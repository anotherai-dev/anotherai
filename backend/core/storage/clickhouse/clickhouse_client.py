import re
from collections.abc import Iterable, Iterator, Sequence
from typing import Any, NamedTuple, cast, final, override
from uuid import UUID

import structlog
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import DatabaseError
from clickhouse_connect.driver.query import QueryResult
from pydantic.main import BaseModel

from core.domain.agent_completion import AgentCompletion
from core.domain.annotation import Annotation
from core.domain.exceptions import InvalidQueryError, ObjectNotFoundError
from core.domain.experiment import Experiment
from core.domain.version import Version
from core.storage.clickhouse._models._ch_annotation import ClickhouseAnnotation
from core.storage.clickhouse._models._ch_completion import ClickhouseCompletion
from core.storage.clickhouse._models._ch_experiment import ClickhouseExperiment
from core.storage.clickhouse._models._ch_field_utils import data_and_columns, zip_columns
from core.storage.clickhouse._utils import clone_client, sanitize_query, sanitize_readonly_privileges
from core.storage.completion_storage import CompletionField, CompletionStorage
from core.utils.iter_utils import safe_map
from core.utils.strings import remove_urls

_log = structlog.get_logger(__name__)

_MAX_MEMORY_USAGE = 3 * 1024 * 1024 * 1024  # 3GB
_MAX_EXECUTION_TIME = 60  # 60 seconds


class ParsedClickhouseError(NamedTuple):
    code: str
    message: str
    error_type: str


@final
class ClickhouseClient(CompletionStorage):
    def __init__(self, client: AsyncClient, tenant_uid: int):
        self._client = client
        self.tenant_uid = tenant_uid

    async def _insert(self, table: str, model: BaseModel, settings: dict[str, Any] | None = None):
        data, columns = data_and_columns(model)

        _ = await self._client.insert(
            table=table,
            column_names=columns,
            data=[data],
            settings=settings,
        )

    @override
    async def store_annotation(self, annotation: Annotation, settings: dict[str, Any] | None = None):
        stored_model = ClickhouseAnnotation.from_domain(self.tenant_uid, annotation)

        await self._insert("annotations", stored_model, settings)

    @override
    async def store_experiment(self, experiment: Experiment, settings: dict[str, Any] | None = None):
        stored_model = ClickhouseExperiment.from_domain(self.tenant_uid, experiment)
        await self._insert("experiments", stored_model, settings)

    @override
    async def add_completion_to_experiment(
        self,
        experiment_id: str,
        completion_id: UUID,
        settings: dict[str, Any] | None = None,
    ):
        # Use ALTER TABLE to update the completion_ids array
        # Since we're using ReplacingMergeTree, we need to update the updated_at as well
        await self._client.command(
            """
            ALTER TABLE experiments UPDATE
                completion_ids = arrayDistinct(arrayConcat(completion_ids, [{completion_id:UUID}]))
            WHERE id = {experiment_id:String}
            """,
            parameters={
                "completion_id": completion_id,
                "experiment_id": experiment_id,
            },
            settings=settings or {},
        )

    @override
    async def store_completion(
        self,
        completion: AgentCompletion,
        insert_settings: dict[str, Any] | None = None,
    ) -> AgentCompletion:
        stored_model = ClickhouseCompletion.from_domain(self.tenant_uid, completion)
        data, columns = data_and_columns(stored_model)

        _ = await self._client.insert(
            table="completions",
            column_names=columns,
            data=[data],
            settings=insert_settings,
        )
        return completion

    def _map_completion(self, result: QueryResult, row: Sequence[Any]):
        zipped = zip_columns(cast(Sequence[str], result.column_names), [row], nested_fields={"annotations", "traces"})
        return ClickhouseCompletion.model_validate(zipped[0]).to_domain()

    @override
    async def completions_by_ids(
        self,
        completions_ids: list[UUID],
        exclude: set[CompletionField] | None = None,
    ) -> list[AgentCompletion]:
        if not completions_ids:
            return []

        uuids = {f"v{i}": uuid for i, uuid in enumerate(completions_ids)}

        raw_exclude: set[str] = (
            {"input_variables", "input_messages", "output_messages", "traces"}
            if exclude is None
            else set(_map_fields(exclude))
        )
        values = [f"({{{k}:UUID}}, UUIDv7ToDateTime({{{k}:UUID}}))" for k in uuids]
        selects = ClickhouseCompletion.select(exclude=raw_exclude)
        query = f"""
            SELECT {", ".join(selects)} FROM completions WHERE (id, created_at) IN ({", ".join(values)})
            """  # noqa: S608
        result = await self._client.query(query, parameters=uuids)

        rows = cast(list[Sequence[Any]], result.result_rows)
        return safe_map(rows, lambda row: self._map_completion(result, row), logger=_log)

    @override
    async def completions_by_id(
        self,
        completion_id: UUID,
        include: set[CompletionField] | None = None,
    ) -> AgentCompletion:
        included = ", ".join(include) if include else "*"

        result = await self._client.query(
            f"""
            SELECT {included} FROM completions WHERE id = {{uuid:UUID}} and created_at = UUIDv7ToDateTime({{uuid:UUID}})
            """,  # noqa: S608
            parameters={"uuid": completion_id},
        )
        if not result.result_rows:
            raise ObjectNotFoundError(object_type="completion")
        return self._map_completion(result, result.result_rows[0])

    async def _readonly_client(self):
        return await clone_client(self._client, self.tenant_uid)

    @override
    async def raw_query(self, query: str) -> list[dict[str, Any]]:
        # We are safe to use a raw query from the client here since the query is executed with a client
        # that is restricted to read only operations and a specific tenant_uid filter
        query = sanitize_query(query)
        readonly_client = await self._readonly_client()
        # We could also set these restrictions at the user level
        query_settings: dict[str, Any] = {
            "readonly": 1,
            "max_memory_usage": _MAX_MEMORY_USAGE,
            "max_execution_time": _MAX_EXECUTION_TIME,
        }

        async def _perform_query():
            try:
                return await readonly_client.query(query, settings=query_settings)
            except DatabaseError as e:
                err = _extract_clickhouse_error(str(e))
                if err.code in {"497"}:
                    # Not enough privileges, we should santitize and retry once
                    raise e
                raise InvalidQueryError(
                    f"{err.error_type}: {err.message}",
                    details={"code": err.code, "error_type": err.error_type},
                ) from None

        try:
            result = await _perform_query()
        except DatabaseError:
            # Can happen after a new table was created, in which case we try sanitizing the privileges again
            await sanitize_readonly_privileges(self._client, self.tenant_uid, user=None)  # using default tenant user
            result = await _perform_query()

        column_names = cast(tuple[str, ...], result.column_names)

        return [dict(zip(column_names, row, strict=False)) for row in result.result_rows]

    @override
    async def get_version_by_id(self, agent_id: str, version_id: str) -> tuple[Version, str]:
        result = await self._client.query(
            """
            SELECT id, version FROM completions WHERE version_id = {version_id:String} and agent_id = {agent_id:String} LIMIT 1
            """,
            parameters={"version_id": version_id, "agent_id": agent_id},
        )
        if not result.result_rows:
            raise ObjectNotFoundError(object_type="version")
        return Version.model_validate_json(result.result_rows[0][1]), str(result.result_rows[0][0])

    @override
    async def cached_completion(
        self,
        version_id: str,
        input_id: str,
        timeout_seconds: float = 0.1,  # 100ms
        max_memory_usage: int = 1024 * 1024 * 200,  # 200MB
    ):
        result = await self._client.query(
            _CACHED_OUTPUT_QUERY,
            parameters={"version_id": version_id, "input_id": input_id},
            settings={
                "max_memory_usage": max_memory_usage,
                "max_execution_time": timeout_seconds,
            },
        )
        if not result.result_rows:
            return None
        return self._map_completion(result, result.result_rows[0])


_CACHED_OUTPUT_QUERY = """
SELECT id, cost_millionth_usd, duration_ds, output_messages FROM completions PREWHERE input_id = {input_id:FixedString(32)} WHERE version_id = {version_id:FixedString(32)} and output_error = '' LIMIT 1
"""


def _map_field(field: CompletionField) -> str:
    # TODO: add field conversion as needed
    return field


def _map_fields(fields: Iterable[CompletionField]) -> Iterator[str]:
    for f in fields:
        yield _map_field(f)


_CK_ERROR_REGEXP = re.compile(
    r"HTTPDriver for .* received Click[hH]ouse error code \d+ +Code: (\d+)\. DB::Exception: (.*) \(([A-Z_0-9]+)\) \(version \d+\.\d+\.\d+\.\d+ \(official build\)\)",
)
_CK_ERROR_CODE_REGEXP = re.compile(r"Code: (\d+)")


def _extract_clickhouse_error(e: str):
    e = e.replace("\n", " ")
    match = _CK_ERROR_REGEXP.match(e)
    if not match:
        _log.error("Failed to extract clickhouse error", error=str(e))
        code_match = _CK_ERROR_CODE_REGEXP.search(e)
        message = remove_urls(e)
        return ParsedClickhouseError(code_match.group(1) if code_match else "0", message, "UNKNOWN")
    code = match.group(1)
    message = match.group(2)
    error_type = match.group(3)

    return ParsedClickhouseError(code, message, error_type)

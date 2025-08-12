from collections.abc import Iterable, Iterator, Sequence
from typing import Any, cast, final, override
from uuid import UUID

import structlog
from clickhouse_connect.driver.asyncclient import AsyncClient
from clickhouse_connect.driver.exceptions import DatabaseError
from clickhouse_connect.driver.query import QueryResult
from pydantic.main import BaseModel

from core.domain.agent_completion import AgentCompletion
from core.domain.annotation import Annotation
from core.domain.exceptions import BadRequestError, ObjectNotFoundError
from core.domain.experiment import Experiment
from core.storage.clickhouse._models._ch_annotation import ClickhouseAnnotation
from core.storage.clickhouse._models._ch_completion import ClickhouseCompletion
from core.storage.clickhouse._models._ch_experiment import ClickhouseExperiment
from core.storage.clickhouse._models._ch_field_utils import data_and_columns, zip_columns
from core.storage.clickhouse._utils import clone_client, sanitize_readonly_privileges
from core.storage.completion_storage import CompletionField, CompletionStorage
from core.utils.iter_utils import safe_map

_log = structlog.get_logger(__name__)

_MAX_MEMORY_USAGE = 1024 * 1024 * 1024  # 1GB
_MAX_EXECUTION_TIME = 60  # 60 seconds


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
        completion_id: str,
        settings: dict[str, Any] | None = None,
    ):
        try:
            completion_uuid = UUID(completion_id)
        except ValueError as e:
            raise BadRequestError("Invalid completion UUID") from e

            # Use ALTER TABLE to update the completion_ids array
        # Since we're using ReplacingMergeTree, we need to update the updated_at as well
        await self._client.command(
            """
            ALTER TABLE experiments UPDATE
                completion_ids = arrayDistinct(arrayConcat(completion_ids, [{completion_id:UUID}]))
            WHERE id = {experiment_id:String}
            """,
            parameters={
                "completion_id": completion_uuid,
                "tenant_uid": self.tenant_uid,
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
        completions_ids: list[str],
        exclude: set[CompletionField] | None = None,
    ) -> list[AgentCompletion]:
        if not completions_ids:
            return []

        try:
            uuids = {f"v{i}": UUID(uuid) for i, uuid in enumerate(completions_ids)}
        except ValueError as e:
            raise BadRequestError("Invalid UUIDs") from e

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
        completion_id: str,
        include: set[CompletionField] | None = None,
    ) -> AgentCompletion:
        try:
            uuid = UUID(completion_id)
        except ValueError as e:
            raise BadRequestError("Invalid UUID") from e

        included = ", ".join(include) if include else "*"

        result = await self._client.query(
            f"""
            SELECT {included} FROM completions WHERE id = {{uuid:UUID}} and created_at = UUIDv7ToDateTime({{uuid:UUID}})
            """,  # noqa: S608
            parameters={"uuid": uuid},
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

        readonly_client = await self._readonly_client()
        # We could also set these restrictions at the user level
        query_settings: dict[str, Any] = {
            "readonly": 1,
            "max_memory_usage": _MAX_MEMORY_USAGE,
            "max_execution_time": _MAX_EXECUTION_TIME,
        }

        # TODO: likely need to wrap the error in a more specific one in case the clickhouse exceptions
        # is not descriptive enough
        try:
            result = await readonly_client.query(query, settings=query_settings)
        except DatabaseError:
            # Can happen after a new table was created, in which case we try sanitizing the privileges again
            await sanitize_readonly_privileges(self._client, self.tenant_uid, user=None)  # using default tenant user
            result = await readonly_client.query(query, settings=query_settings)

        column_names = cast(tuple[str, ...], result.column_names)

        return [dict(zip(column_names, row, strict=False)) for row in result.result_rows]


def _map_field(field: CompletionField) -> str:
    # TODO: add field conversion as needed
    return field


def _map_fields(fields: Iterable[CompletionField]) -> Iterator[str]:
    for f in fields:
        yield _map_field(f)

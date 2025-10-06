from collections.abc import Collection, Iterable
from datetime import datetime
from typing import Any, Protocol, override
from uuid import UUID

import asyncpg
import structlog
from asyncpg.pool import PoolConnectionProxy

from core.domain.agent_output import AgentOutput
from core.domain.cache_usage import CacheUsage
from core.domain.exceptions import DuplicateValueError, ObjectNotFoundError
from core.domain.experiment import Experiment, ExperimentInput, ExperimentOutput, ExperimentVersion
from core.storage.experiment_storage import (
    CompletionIDTuple,
    CompletionOutputTuple,
    ExperimentFields,
    ExperimentOutputFields,
    ExperimentStorage,
)
from core.storage.psql._psql_base_storage import (
    AgentLinkedRow,
    JSONDict,
    JSONList,
    PsqlBaseRow,
    PsqlBaseStorage,
    WithUpdatedAtRow,
    insert_iterator,
    psql_serialize_json,
)
from core.storage.psql._psql_utils import map_value
from core.utils.fields import datetime_zero, uuid_zero
from core.utils.iter_utils import safe_map

log = structlog.get_logger(__name__)


class PsqlExperimentStorage(PsqlBaseStorage, ExperimentStorage):
    @override
    @classmethod
    def table(cls) -> str:
        return "experiments"

    @override
    async def create(self, experiment: Experiment, agent_uid: int | None = None) -> None:
        # Get agent ID from agent_id
        async with self._connect() as connection:
            if not agent_uid:
                agent_uid = await self._agent_uid(connection, experiment.agent_id)

            experiment_row = _ExperimentRow(
                slug=experiment.id,
                agent_uid=agent_uid,
                tenant_uid=self._tenant_uid,
                author_name=experiment.author_name,
                title=experiment.title,
                description=experiment.description,
                result=experiment.result or None,
                run_ids=experiment.run_ids or [],
                metadata=experiment.metadata or {},
            )

            _ = await self._insert(connection, experiment_row)

    @override
    async def set_result(self, experiment_id: str, result: str) -> None:
        async with self._connect() as connection:
            _ = await connection.execute(
                """
                UPDATE experiments
                SET result = $1, updated_at = CURRENT_TIMESTAMP
                WHERE slug = $2
                """,
                result,
                experiment_id,
            )

    @override
    async def add_run_id(self, experiment_id: str, run_id: UUID) -> None:
        async with self._connect() as connection:
            _ = await connection.execute(
                """
                UPDATE experiments
                SET run_ids = array_append(run_ids, $1), updated_at = CURRENT_TIMESTAMP
                WHERE slug = $2 AND NOT ($1 = ANY(run_ids))
                """,
                str(run_id),
                experiment_id,
            )

    @override
    async def delete(self, experiment_id: str) -> None:
        async with self._connect() as connection:
            _ = await connection.execute(
                """
                UPDATE experiments
                SET deleted_at = CURRENT_TIMESTAMP
                WHERE tenant_uid = $1 AND slug = $2
                """,
                self._tenant_uid,
                experiment_id,
            )

    def _where_experiments(self, arg_idx: int, agent_uid: int | None, since: datetime | None) -> tuple[str, list[Any]]:
        where: list[str] = ["e.deleted_at IS NULL"]
        arguments: list[Any] = []

        if since is not None:
            where.append(f"e.created_at > ${len(arguments) + arg_idx}")
            arguments.append(map_value(since))
        if agent_uid is not None:
            where.append(f"e.agent_uid = ${len(arguments) + arg_idx}")
            arguments.append(agent_uid)

        return " AND ".join(where), arguments

    @override
    async def list_experiments(
        self,
        agent_uid: int | None,
        since: datetime | None,
        limit: int,
        offset: int = 0,
    ) -> list[Experiment]:
        where, arguments = self._where_experiments(3, agent_uid, since)

        query = f"""
        SELECT e.*, a.slug as agent_slug
        FROM experiments e
        JOIN agents a ON e.agent_uid = a.uid
        WHERE {where}
        ORDER BY e.created_at DESC
        LIMIT $1
        OFFSET $2
        """  # noqa: S608 # OK here since where is defined above

        async with self._connect() as connection:
            rows = await connection.fetch(
                query,
                limit,
                offset,
                *arguments,
            )
            return safe_map(rows, lambda x: self._validate(_ExperimentRow, x).to_domain(), log)

    @override
    async def count_experiments(self, agent_uid: int | None, since: datetime | None) -> int:
        where, arguments = self._where_experiments(1, agent_uid, since)

        query = f"""
        SELECT COUNT(*)
        FROM experiments e
        WHERE {where} AND e.deleted_at IS NULL
        """  # noqa: S608 # OK here since where is defined above

        async with self._connect() as connection:
            count = await connection.fetchval(query, *arguments)
            return count or 0

    async def _list_experiment_versions(
        self,
        connection: PoolConnectionProxy,
        experiment_uid: int,
        version_ids: Collection[str] | None = None,
        full=False,
    ) -> list[ExperimentVersion]:
        select = "*" if full else "version_id"
        where = ["experiment_uid = $1"]
        args: list[Any] = [experiment_uid]
        if version_ids:
            where.append("(version_id = ANY($2) OR alias = ANY($2))")
            args.append(version_ids)
        rows = await connection.fetch(
            f"SELECT {select} FROM experiment_versions WHERE {' AND '.join(where)} ORDER BY position ASC",  # noqa: S608
            *args,
        )
        return _sort_by_id((self._validate(_ExperimentVersionRow, row).to_domain() for row in rows), version_ids)

    async def _list_experiment_inputs(
        self,
        connection: PoolConnectionProxy,
        experiment_uid: int,
        input_ids: Collection[str] | None = None,
        full=False,
    ) -> list[ExperimentInput]:
        select = "*" if full else "input_id"
        where: list[str] = ["experiment_uid = $1"]
        args: list[Any] = [experiment_uid]
        if input_ids:
            where.append("(input_id = ANY($2) OR alias = ANY($2))")
            args.append(input_ids)
        rows = await connection.fetch(
            f"SELECT {select} FROM experiment_inputs WHERE {' AND '.join(where)} ORDER BY position ASC",  # noqa: S608
            *args,
        )
        return _sort_by_id((self._validate(_ExperimentInputRow, row).to_domain() for row in rows), input_ids)

    @classmethod
    def _include_versions(cls, include: Collection[ExperimentFields]) -> bool | None:
        if "versions" in include:
            return True
        if "versions.id" in include:
            return False
        return None

    @classmethod
    def _include_inputs(cls, include: Collection[ExperimentFields]) -> bool | None:
        if "inputs" in include:
            return True
        if "inputs.id" in include:
            return False
        return None

    @override
    async def get_experiment(
        self,
        experiment_id: str,
        include: Collection[ExperimentFields] | None = None,
        version_ids: Collection[str] | None = None,
        input_ids: Collection[str] | None = None,
    ) -> Experiment:
        # TODO:
        async with self._connect() as connection:
            row = await connection.fetchrow(
                """
                SELECT e.*, a.slug as agent_slug
                FROM experiments e
                JOIN agents a ON e.agent_uid = a.uid
                WHERE e.tenant_uid = $1 AND e.slug = $2 AND e.deleted_at IS NULL
                """,
                self._tenant_uid,
                experiment_id,
            )

            if row is None:
                raise ObjectNotFoundError(f"Experiment not found: {experiment_id}")

            experiment_uid = row["uid"]
            versions: list[ExperimentVersion] | None = None
            inputs: list[ExperimentInput] | None = None
            outputs: list[ExperimentOutput] | None = None
            if include:
                version_included = self._include_versions(include)
                if version_included is not None:
                    versions = await self._list_experiment_versions(
                        connection,
                        experiment_uid,
                        version_ids=version_ids,
                        full=version_included,
                    )
                input_included = self._include_inputs(include)
                if input_included is not None:
                    inputs = await self._list_experiment_inputs(
                        connection,
                        experiment_uid,
                        input_ids=input_ids,
                        full=input_included,
                    )
                if "outputs" in include:
                    outputs = await self._list_experiment_completions(
                        connection,
                        experiment_uid=experiment_uid,
                        version_ids=version_ids,
                        input_ids=input_ids,
                        include={"output"},
                    )

            return self._validate(_ExperimentRow, row).to_domain(versions=versions, inputs=inputs, outputs=outputs)

    async def _experiment_uid(self, connection: PoolConnectionProxy, experiment_id: str) -> int:
        row = await connection.fetchrow(
            "SELECT uid FROM experiments WHERE slug = $1",
            experiment_id,
        )
        if row is None:
            raise ObjectNotFoundError(f"Experiment not found: {experiment_id}")
        return row["uid"]

    async def _map_uids(
        self,
        connection: PoolConnectionProxy,
        experiment_uid: int,
        ids: set[str],
        table: str,
        column: str,
    ):
        rows = await connection.fetch(
            f"SELECT uid, {column}, alias FROM {table} WHERE experiment_uid = $1 AND ({column} = ANY($2) OR alias = ANY($2))",  # noqa: S608
            experiment_uid,
            ids,
        )

        def _it():
            for row in rows:
                yield row[column], row["uid"]
                if row["alias"]:
                    yield row["alias"], row["uid"]

        if len(rows) != len(ids):
            raise ObjectNotFoundError(f"{table} not found: {ids - {row[0] for row in _it()}}")
        return dict(_it())

    async def _version_uids(
        self,
        connection: PoolConnectionProxy,
        experiment_uid: int,
        version_ids: set[str],
    ) -> dict[str, int]:
        return await self._map_uids(connection, experiment_uid, version_ids, "experiment_versions", "version_id")

    async def _input_uids(
        self,
        connection: PoolConnectionProxy,
        experiment_uid: int,
        input_ids: set[str],
    ) -> dict[str, int]:
        return await self._map_uids(connection, experiment_uid, input_ids, "experiment_inputs", "input_id")

    async def _lock_experiment(self, connection: PoolConnectionProxy, experiment_uid: int) -> None:
        await connection.execute(
            "SELECT pg_advisory_xact_lock($1)",
            experiment_uid,
        )

    async def _update_null_aliases(
        self,
        connection: PoolConnectionProxy,
        experiment_uid: int,
        table: str,
        id_column: str,
        alias_to_update: Collection[tuple[str, str]],
    ):
        value_query: list[str] = []
        values: list[str] = []
        for id, alias in alias_to_update:
            value_query.append(f"(${len(values) + 2}, ${len(values) + 3})")
            values.append(id)
            values.append(alias)

        await connection.execute(
            f"""UPDATE {table} AS t
            SET alias = c.new_alias
            FROM (VALUES {", ".join(value_query)}) AS c(id, new_alias)
            WHERE t.{id_column} = c.id AND t.alias IS NULL AND t.experiment_uid = $1""",  # noqa: S608
            experiment_uid,
            *values,
        )

    async def _validate_aliases[T: _AliasAndID](
        self,
        connection: PoolConnectionProxy,
        experiment_uid: int,
        table: str,
        id_column: str,
        values: "Collection[T]",
    ):
        """Check that all requested aliases are either available or attached to the same ID.
        Return a list of IDs that should are already in the DB"""
        requested_aliases = {v.id: v.alias for v in values}
        if not requested_aliases:
            # Nothing to do
            return set()
        # We fetch all the existing IDs for the requested aliases
        existing_aliases = await connection.fetch(
            f"SELECT {id_column}, alias FROM {table} WHERE experiment_uid = $1 AND {id_column} = ANY($2)",  # noqa: S608
            experiment_uid,
            list(requested_aliases.keys()),
        )
        # Checking IDs that will not need to be inserted
        existing_ids: set[str] = set()
        id_mismatch: list[tuple[str, str]] = []
        alias_to_update: list[tuple[str, str]] = []
        for row in existing_aliases:
            # requested_id will be the new ID associated with the alias
            requested_alias = requested_aliases.get(row[0])
            existing_ids.add(row[0])
            if requested_alias and requested_alias != row[1]:
                if row[1] is None:
                    # The existing alias is None so we can update it
                    alias_to_update.append((row[0], requested_alias))
                else:
                    id_mismatch.append((row[0], row[1]))
                continue

        if id_mismatch:
            id_mismatch_str = ", ".join(f"{id}: {alias}" for id, alias in id_mismatch)
            raise DuplicateValueError(f"Some inputs already exist with different aliases: {id_mismatch_str}")

        if alias_to_update:
            await self._update_null_aliases(
                connection,
                experiment_uid,
                "experiment_inputs",
                "input_id",
                alias_to_update,
            )

        return existing_ids

    @override
    async def add_inputs(self, experiment_id: str, inputs: list[ExperimentInput]):
        async with self._connect() as connection:
            experiment_uid = await self._experiment_uid(connection, experiment_id)
            # We lock the entire experiment
            # We could try to lock inputs separately but it's not worth the complexity
            await self._lock_experiment(connection, experiment_uid)

            # First let's check that we won't have duplicate aliases
            # We cannot deal with it with an on conflict clause, because we want to be
            # idempotent for inserts when the alias is attached to the same id
            existing = await self._validate_aliases(connection, experiment_uid, "experiment_inputs", "input_id", inputs)

            # Get the current max position
            max_position = await connection.fetchval(
                "SELECT COALESCE(MAX(position), 0) FROM experiment_inputs WHERE experiment_uid = $1",
                experiment_uid,
            )

            to_insert = (
                _ExperimentInputRow.from_domain(experiment_uid, input, max_position + i + 1)
                for i, input in enumerate(inputs)
                if input.id not in existing
            )

            values = await connection.fetchmany(
                f"""INSERT INTO experiment_inputs ({", ".join(_INPUT_INSERT_FIELDS)})
                VALUES ({", ".join(f"${i + 1}" for i in range(len(_INPUT_INSERT_FIELDS)))})
                RETURNING input_id""",  # noqa: S608 # OK here since fields is defined above
                list(insert_iterator(_INPUT_INSERT_FIELDS, to_insert)),
            )

            return {input[0] for input in values}

    @override
    async def add_versions(self, experiment_id: str, versions: list[ExperimentVersion]) -> set[str]:
        async with self._connect() as connection:
            experiment_uid = await self._experiment_uid(connection, experiment_id)
            to_insert = (_ExperimentVersionRow.from_domain(experiment_uid, version) for version in versions)
            try:
                values = await connection.fetchmany(
                    f"""INSERT INTO experiment_versions ({", ".join(_VERSION_INSERT_FIELDS)})
                    VALUES ({", ".join(f"${i + 1}" for i in range(len(_VERSION_INSERT_FIELDS)))})
                    ON CONFLICT (experiment_uid, version_id) DO NOTHING
                    RETURNING version_id""",  # noqa: S608 # OK here since fields is defined above
                    list(insert_iterator(_VERSION_INSERT_FIELDS, to_insert)),
                )
            except asyncpg.UniqueViolationError as e:
                # Check if it's an alias conflict
                if "experiment_versions_alias_unique" in str(e):
                    # Find which alias caused the conflict
                    conflicting_aliases = [version.alias for version in versions if version.alias]
                    raise DuplicateValueError(
                        f"Duplicate alias found in experiment versions: {conflicting_aliases}",
                    ) from e
                raise DuplicateValueError("Duplicate version found in experiment") from e
            return {version[0] for version in values}

    @override
    async def add_completions(self, experiment_id: str, completions: list[CompletionIDTuple]) -> set[UUID]:
        async with self._connect() as connection:
            experiment_uid = await self._experiment_uid(connection, experiment_id)
            version_uids = await self._version_uids(
                connection,
                experiment_uid,
                {completion.version_id for completion in completions},
            )
            input_uids = await self._input_uids(
                connection,
                experiment_uid,
                {completion.input_id for completion in completions},
            )

            to_insert = (
                _ExperimentOutputRow.from_domain(experiment_uid, input_uids, version_uids, completion)
                for completion in completions
            )
            values = await connection.fetchmany(
                f"""INSERT INTO experiment_outputs ({", ".join(_OUTPUT_INSERT_FIELDS)})
                VALUES ({", ".join(f"${i + 1}" for i in range(len(_OUTPUT_INSERT_FIELDS)))})
                ON CONFLICT (experiment_uid, completion_id) DO NOTHING
                RETURNING completion_id""",  # noqa: S608 # OK here since fields is defined above
                list(insert_iterator(_OUTPUT_INSERT_FIELDS, to_insert)),
            )
            return {completion[0] for completion in values}

    async def _raise_for_completion_not_found(
        self,
        connection: PoolConnectionProxy,
        experiment_uid: int,
        completion_id: UUID,
    ) -> None:
        # Making sure the completion exists
        found = await connection.fetchval(
            "SELECT uid FROM experiment_outputs WHERE experiment_uid = $1 AND completion_id = $2",
            experiment_uid,
            completion_id,
        )
        if not found:
            raise ObjectNotFoundError(f"Completion not found: {completion_id}")

        raise DuplicateValueError(f"Completion already started: {completion_id}")

    @override
    async def start_completion(self, experiment_id: str, completion_id: UUID) -> None:
        async with self._connect() as connection:
            experiment_uid = await self._experiment_uid(connection, experiment_id)
            returned = await connection.fetchval(
                """UPDATE experiment_outputs SET started_at = CURRENT_TIMESTAMP
                WHERE experiment_uid = $1 AND completion_id = $2 AND started_at IS NULL
                RETURNING uid""",
                experiment_uid,
                completion_id,
            )
            if not returned:
                await self._raise_for_completion_not_found(connection, experiment_uid, completion_id)

    @override
    async def fail_completion(self, experiment_id: str, completion_id: UUID) -> None:
        async with self._connect() as connection:
            experiment_uid = await self._experiment_uid(connection, experiment_id)
            returned = await connection.fetchval(
                """UPDATE experiment_outputs SET started_at = NULL
                WHERE experiment_uid = $1 AND completion_id = $2 AND started_at IS NOT NULL AND completed_at IS NULL
                RETURNING uid""",
                experiment_uid,
                completion_id,
            )
            if not returned:
                await self._raise_for_completion_not_found(connection, experiment_uid, completion_id)

    @override
    async def add_completion_output(
        self,
        experiment_id: str,
        completion_id: UUID,
        output: CompletionOutputTuple,
    ) -> None:
        async with self._connect() as connection:
            experiment_uid = await self._experiment_uid(connection, experiment_id)
            _ = await connection.execute(
                "UPDATE experiment_outputs SET completed_at = CURRENT_TIMESTAMP, output_messages = $1, output_error = $2, output_preview = $3, cost_usd = $4, duration_seconds = $5 WHERE experiment_uid = $6 AND completion_id = $7",
                psql_serialize_json(output.output.messages),
                psql_serialize_json(output.output.error),
                output.output.preview,
                output.cost_usd,
                output.duration_seconds,
                experiment_uid,
                completion_id,
            )

    def _sort_experiment_outputs(
        self,
        iter: "Iterable[_ExperimentOutputRow]",
        version_ids: Collection[str] | None = None,
        input_ids: Collection[str] | None = None,
    ) -> list[ExperimentOutput]:
        """Try and respect the requested order of inputs and versions if provided"""
        version_pos = {v: i for i, v in enumerate(version_ids)} if version_ids else {}
        input_pos = {v: i for i, v in enumerate(input_ids)} if input_ids else {}

        def _get_pos(id: str | None, alias: str | None, d: dict[str, int], fallback: int | None) -> int:
            if alias and alias in d:
                return d[alias]
            if id and id in d:
                return d[id]
            return fallback or 0

        def _key(row: _ExperimentOutputRow) -> tuple[int, int]:
            return _get_pos(row.input_id, row.input_alias, input_pos, row.input_position), _get_pos(
                row.version_id,
                row.version_alias,
                version_pos,
                row.version_position,
            )

        return safe_map(sorted(iter, key=_key), lambda x: x.to_domain(), log)

    async def _list_experiment_completions(
        self,
        connection: PoolConnectionProxy,
        experiment_uid: int,
        version_ids: Collection[str] | None = None,
        input_ids: Collection[str] | None = None,
        include: set[ExperimentOutputFields] | None = None,
    ) -> list[ExperimentOutput]:
        selects = _ExperimentOutputRow.select_fields(include)
        args: list[Any] = [experiment_uid]
        where: list[str] = ["experiment_outputs.experiment_uid = $1"]
        if version_ids:
            where.append(f"(ev.version_id = ANY(${len(args) + 1}) OR ev.alias = ANY(${len(args) + 1}))")
            args.append(version_ids)
        if input_ids:
            where.append(f"(ei.input_id = ANY(${len(args) + 1}) OR ei.alias = ANY(${len(args) + 1}))")
            args.append(input_ids)

        # We want to make it easy to compare 2 outputs for the same input and different versions
        # So we want all outputs for a given input to be grouped together
        query = f"""SELECT {", ".join(selects)},
            ei.input_id as input_id, ei.position as input_position, ei.alias as input_alias,
            ev.version_id as version_id, ev.position as version_position, ev.alias as version_alias
            FROM experiment_outputs
            LEFT JOIN experiment_inputs ei ON ei.uid = experiment_outputs.input_uid
            LEFT JOIN experiment_versions ev ON ev.uid = experiment_outputs.version_uid
            WHERE {" AND ".join(where)}
            ORDER BY ei.position ASC, ev.position ASC"""  # noqa: S608 # Ordering will be done in PSQL memory here which is not great
        rows = await connection.fetch(query, *args)
        outputs = (self._validate(_ExperimentOutputRow, x) for x in rows)
        if not input_ids and not version_ids:
            return safe_map(outputs, lambda x: x.to_domain(), log)
        return self._sort_experiment_outputs(outputs, version_ids, input_ids)

    @override
    async def list_experiment_completions(
        self,
        experiment_id: str,
        version_ids: Collection[str] | None = None,
        input_ids: Collection[str] | None = None,
        include: set[ExperimentOutputFields] | None = None,
    ) -> list[ExperimentOutput]:
        async with self._connect() as connection:
            experiment_uid = await self._experiment_uid(connection, experiment_id)
            return await self._list_experiment_completions(
                connection,
                experiment_uid,
                version_ids=version_ids,
                input_ids=input_ids,
                include=include,
            )


class _ExperimentRow(AgentLinkedRow, WithUpdatedAtRow):
    """A representation of an experiment row"""

    slug: str = ""
    author_name: str = ""
    title: str = ""
    description: str = ""
    result: str | None = None
    run_ids: list[str] | None = None
    metadata: JSONDict | None = None
    use_cache: str | None = None

    def _use_cache_to_domain(self) -> CacheUsage | None:
        if self.use_cache is None:
            return None
        try:
            return CacheUsage(self.use_cache)
        except ValueError:
            return None

    def to_domain(
        self,
        versions: list[ExperimentVersion] | None = None,
        inputs: list[ExperimentInput] | None = None,
        outputs: list[ExperimentOutput] | None = None,
    ) -> Experiment:
        return Experiment(
            id=self.slug,
            created_at=self.created_at or datetime_zero(),
            updated_at=self.updated_at or datetime_zero(),
            author_name=self.author_name,
            title=self.title,
            description=self.description,
            result=self.result,
            agent_id=self.agent_slug or "",
            run_ids=self.run_ids or [],
            metadata=self.metadata or None,
            use_cache=self._use_cache_to_domain(),
            versions=versions,
            inputs=inputs,
            outputs=outputs,
        )


_INPUT_INSERT_FIELDS = [
    "experiment_uid",
    "input_id",
    "input_messages",
    "input_variables",
    "input_preview",
    "alias",
    "position",
]


class _ExperimentInputRow(PsqlBaseRow):
    experiment_uid: int | None = None
    input_id: str | None = None
    input_messages: JSONList | None = None
    input_variables: JSONDict | None = None
    input_preview: str | None = None
    alias: str | None = None
    position: int | None = None

    @classmethod
    def from_domain(cls, experiment_uid: int, input: ExperimentInput, position: int):
        # TODO: use a separate type for validation
        dumped = input.model_dump(include={"messages", "variables"})
        return cls(
            experiment_uid=experiment_uid,
            input_id=input.id,
            input_preview=input.preview,
            input_messages=dumped["messages"],
            input_variables=dumped["variables"],
            alias=input.alias,
            position=position,
        )

    def to_domain(self) -> ExperimentInput:
        return ExperimentInput(
            id=self.input_id or "",
            preview=self.input_preview or "",
            messages=self.input_messages,
            variables=self.input_variables,
            alias=self.alias,
        )


_VERSION_INSERT_FIELDS = ["experiment_uid", "version_id", "model", "payload", "alias"]


class _ExperimentVersionRow(PsqlBaseRow):
    alias: str | None = None
    position: int | None = None
    experiment_uid: int | None = None
    version_id: str | None = None
    model: str | None = None
    payload: JSONDict | None = None

    @classmethod
    def from_domain(cls, experiment_uid: int, version: ExperimentVersion):
        return cls(
            experiment_uid=experiment_uid,
            version_id=version.id,
            model=version.model,
            payload=version.model_dump(exclude_none=True),
            alias=version.alias,
        )

    def to_domain(self) -> ExperimentVersion:
        payload = self.payload or {}
        if self.version_id is not None:
            payload["id"] = self.version_id
        if self.model is not None:
            payload["model"] = self.model
        return ExperimentVersion.model_validate(payload)


_OUTPUT_INSERT_FIELDS = [
    "experiment_uid",
    "completion_id",
    "version_uid",
    "input_uid",
    "started_at",
    "completed_at",
    "output_messages",
    "output_error",
    "output_preview",
]


class _ExperimentOutputRow(PsqlBaseRow):
    experiment_uid: int = 0
    version_uid: int = 0
    version_id: str | None = None  # from JOIN queries
    version_alias: str | None = None  # from JOIN queries
    input_uid: int = 0
    input_id: str | None = None  # from JOIN queries
    input_alias: str | None = None  # from JOIN queries
    completion_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    output_messages: JSONList | None = None
    output_error: JSONDict | None = None
    output_preview: str | None = None
    cost_usd: float | None = None
    duration_seconds: float | None = None
    input_position: int | None = None
    version_position: int | None = None

    @classmethod
    def from_domain(
        cls,
        experiment_uid: int,
        input_uids: dict[str, int],
        version_uids: dict[str, int],
        completion: CompletionIDTuple,
    ):
        return cls(
            experiment_uid=experiment_uid,
            version_uid=version_uids[completion.version_id],
            input_uid=input_uids[completion.input_id],
            completion_id=completion.completion_id,
        )

    def to_domain(self) -> ExperimentOutput:
        return ExperimentOutput(
            completion_id=self.completion_id or uuid_zero(),
            version_id=self.version_id or "",
            version_alias=self.version_alias,
            input_id=self.input_id or "",
            input_alias=self.input_alias,
            created_at=self.created_at or datetime_zero(),
            started_at=self.started_at,
            completed_at=self.completed_at,
            cost_usd=self.cost_usd,
            duration_seconds=self.duration_seconds,
            output=AgentOutput.model_validate(
                {
                    "messages": self.output_messages,
                    "error": self.output_error,
                    "preview": self.output_preview or "",
                },
            ),
        )

    @classmethod
    def select_fields(cls, include: set[ExperimentOutputFields] | None = None, prefix: str = "experiment_outputs"):
        base_fields = set(cls.model_fields.keys())
        base_fields.remove("input_id")
        base_fields.remove("version_id")
        base_fields.remove("input_alias")
        base_fields.remove("version_alias")
        base_fields.remove("input_position")
        base_fields.remove("version_position")
        if not include or "output" not in include:
            base_fields.remove("output_messages")
            base_fields.remove("output_error")

        return [f"{prefix}.{f}" for f in base_fields]


class _AliasAndID(Protocol):
    @property
    def alias(self) -> str | None: ...

    @property
    def id(self) -> str: ...


def _sorter(value: Collection[str]):
    by_pos = {v: i for i, v in enumerate(value)}

    def _keymap(v: _AliasAndID) -> int:
        if v.alias and v.alias in by_pos:
            return by_pos[v.alias]
        return by_pos.get(v.id, len(value))

    return _keymap


def _sort_by_id[T: _AliasAndID](it: Iterable[T], ids: Collection[str] | None) -> list[T]:
    if ids is None:
        return list(it)
    return sorted(it, key=_sorter(ids))

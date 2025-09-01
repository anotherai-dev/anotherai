import json
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Annotated, Any

import asyncpg
from asyncpg.pool import PoolConnectionProxy
from pydantic import BaseModel, BeforeValidator, PlainSerializer

from core.domain.exceptions import DuplicateValueError, ObjectNotFoundError


class PsqlBaseStorage:
    def __init__(self, tenant_uid: int, pool: asyncpg.Pool):
        self._tenant_uid: int = tenant_uid
        self._pool: asyncpg.Pool = pool

    def _map_value(self, v: Any) -> Any:
        match v:
            case datetime():
                return v.replace(tzinfo=None) if v.tzinfo else v
            case _:
                return v

    def _map_values(self, *args: Any):
        for arg in args:
            yield self._map_value(arg)

    @asynccontextmanager
    async def _connect(self):
        async with self._pool.acquire() as conn, conn.transaction():
            # Set local variable for RLS
            _ = await conn.execute(f"SET app.tenant_uid = {int(self._tenant_uid)}")
            yield conn

    def _validate[B: BaseModel](self, b: type[B], row: asyncpg.Record):
        return b.model_validate(dict(row))

    @classmethod
    def table(cls) -> str:
        raise NotImplementedError("Subclass must implement table method")

    async def _insert(
        self,
        conn: PoolConnectionProxy,
        row: BaseModel,
        table: str | None = None,
        on_conflict: str | None = None,
    ) -> int:
        dumped = row.model_dump(exclude_none=True, exclude={"tenant_uid", "uid"})
        columns: list[str] = ["tenant_uid"]
        values: list[Any] = [self._tenant_uid]

        for k, v in dumped.items():
            columns.append(k)
            values.append(self._map_value(v))

        columns_str = ", ".join(f'"{c}"' for c in columns)
        values_str = ", ".join(f"${i + 1}" for i in range(len(values)))

        parts = [
            f"INSERT INTO {table or self.table()} ({columns_str}) VALUES ({values_str})",  # noqa: S608
        ]

        if on_conflict:
            parts.append(on_conflict)

        parts.append("RETURNING uid")

        insert = "\n".join(parts)

        try:
            executed = await conn.fetchval(insert, *values)
        except asyncpg.UniqueViolationError as e:
            # TODO: better error message
            raise DuplicateValueError("Duplicate object") from e
        return executed

    async def _agent_uid(self, conn: PoolConnectionProxy, agent_id: str) -> int:
        agent_row = await conn.fetchrow(
            "SELECT uid FROM agents WHERE slug = $1",
            agent_id,
        )

        if agent_row is None:
            raise ObjectNotFoundError(object_type="agent")

        return agent_row["uid"]

    async def _agent_uids(self, conn: PoolConnectionProxy, agent_ids: set[str]) -> dict[str, int]:
        if not agent_ids:
            return {}

        agent_rows = await conn.fetch(
            "SELECT uid, slug FROM agents WHERE slug = ANY($1)",
            agent_ids,
        )
        return {row["slug"]: row["uid"] for row in agent_rows}

    async def _agent_ids(self, conn: PoolConnectionProxy, agent_uids: set[int]) -> dict[int, str]:
        if not agent_uids:
            return {}

        agent_rows = await conn.fetch(
            "SELECT uid, slug FROM agents WHERE uid = ANY($1)",
            agent_uids,
        )

        return {row["uid"]: row["slug"] for row in agent_rows}

    async def _experiment_uids(self, conn: PoolConnectionProxy, experiment_ids: set[str]) -> dict[str, int]:
        if not experiment_ids:
            return {}

        experiment_rows = await conn.fetch(
            "SELECT uid, slug FROM experiments WHERE slug = ANY($1)",
            experiment_ids,
        )

        return {row["slug"]: row["uid"] for row in experiment_rows}

    async def _experiment_ids(self, conn: PoolConnectionProxy, experiment_ids: set[int]) -> dict[int, str]:
        if not experiment_ids:
            return {}

        experiment_rows = await conn.fetch(
            "SELECT uid, slug FROM experiments WHERE uid = ANY($1)",
            experiment_ids,
        )

        return {row["uid"]: row["slug"] for row in experiment_rows}

    @contextmanager
    def _wrap_errors(self) -> Any:
        try:
            yield
        except asyncpg.UniqueViolationError as e:
            raise DuplicateValueError("Duplicate object") from e


class PsqlBaseRow(BaseModel):
    uid: int | None = None
    tenant_uid: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None


class AgentLinkedRow(PsqlBaseRow):
    agent_uid: int | None = None
    agent_slug: str | None = None  # from JOIN queries


def _serialize_json(value: Any):
    return json.dumps(value)


def _deserialize_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    return json.loads(value)


JSONValidator = BeforeValidator(_deserialize_json)
JSONSerializer = PlainSerializer(_serialize_json)


type JSONDict = Annotated[dict[str, Any], JSONValidator, JSONSerializer]
type JSONList = Annotated[list[Any], JSONValidator, JSONSerializer]

from typing import override

from asyncpg import UniqueViolationError

from core.domain.agent import Agent
from core.domain.exceptions import DuplicateValueError, ObjectNotFoundError
from core.storage.agent_storage import AgentStorage
from core.storage.psql._psql_base_storage import PsqlBaseRow, PsqlBaseStorage
from core.utils.fields import datetime_zero, id_uint32


class PsqlAgentsStorage(PsqlBaseStorage, AgentStorage):
    @override
    async def store_agent(self, agent: Agent) -> None:
        if agent.uid == 0:
            agent.uid = id_uint32()

        try:
            async with self._connect() as connection:
                _ = await connection.execute(
                    """
                        INSERT INTO agents (uid, slug, name)
                        VALUES ($1, $2, $3)
                        """,
                    agent.uid,
                    agent.id,
                    agent.name,
                )
        except UniqueViolationError:
            try:
                async with self._connect() as connection:
                    agent.uid = await self._agent_uid(connection, agent.id)
            except ObjectNotFoundError:
                raise DuplicateValueError("Agent already exists") from None

    @override
    async def get_agent(self, agent_id: str) -> Agent:
        async with self._connect() as connection:
            row = await connection.fetchrow(
                "SELECT * FROM agents WHERE slug = $1",
                agent_id,
            )
        if row is None:
            raise ObjectNotFoundError("agent")
        return self._validate(_AgentRow, row).to_domain()

    @override
    async def agent_by_uid(self, agent_uid: int) -> Agent:
        async with self._connect() as connection:
            row = await connection.fetchrow(
                "SELECT * FROM agents WHERE uid = $1",
                agent_uid,
            )
        if row is None:
            raise ObjectNotFoundError("agent")
        return self._validate(_AgentRow, row).to_domain()

    @override
    async def list_agents(self) -> list[Agent]:
        async with self._connect() as connection:
            rows = await connection.fetch("SELECT * FROM agents")
        return [self._validate(_AgentRow, row).to_domain() for row in rows]


class _AgentRow(PsqlBaseRow):
    slug: str = ""
    name: str = ""

    def to_domain(self) -> Agent:
        return Agent(uid=self.uid or 0, id=self.slug, name=self.name, created_at=self.created_at or datetime_zero())

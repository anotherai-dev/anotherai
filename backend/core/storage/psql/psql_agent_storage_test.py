import asyncpg
import pytest

from core.domain.agent import Agent
from core.domain.exceptions import ObjectNotFoundError
from core.storage.psql.psql_agent_storage import PsqlAgentsStorage


class TestStoreAgent:
    async def test_store_agent(self, agent_storage: PsqlAgentsStorage, psql_pool: asyncpg.Pool):
        agent = Agent(uid=0, id="test", name="Test Agent")
        await agent_storage.store_agent(agent)
        assert agent.uid != 0

        retrieved = await agent_storage.get_agent(agent.id)
        assert retrieved.uid == agent.uid

        # Check that I cannot get it from another tenant
        other_storage = PsqlAgentsStorage(tenant_uid=2, pool=psql_pool)
        with pytest.raises(ObjectNotFoundError):
            _ = await other_storage.get_agent(agent.id)

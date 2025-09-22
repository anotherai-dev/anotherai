# pyright: reportPrivateUsage=false


from typing import Any

import asyncpg
import pytest
from asyncpg.pool import PoolConnectionProxy

from core.domain.agent import Agent
from core.domain.exceptions import ObjectNotFoundError
from core.storage.psql._psql_base_storage import PsqlBaseStorage, _deserialize_json, psql_serialize_json
from core.storage.psql.psql_agent_storage import PsqlAgentsStorage
from core.storage.psql.psql_experiment_storage import PsqlExperimentStorage
from tests.fake_models import fake_experiment


@pytest.fixture
def base_storage(inserted_tenant: int, purged_psql: asyncpg.Pool):
    return PsqlBaseStorage(
        tenant_uid=inserted_tenant,
        pool=purged_psql,
    )


@pytest.fixture
async def inserted_agents(agent_storage: PsqlAgentsStorage, purged_psql_tenant_conn: asyncpg.Pool):
    await agent_storage.store_agent(Agent(uid=0, id="agent1", name="Test Agent"))
    await agent_storage.store_agent(Agent(uid=0, id="agent2", name="Test Agent"))

    rows = await purged_psql_tenant_conn.fetch("SELECT uid, slug FROM agents")
    return {row["slug"]: row["uid"] for row in rows}


@pytest.fixture
async def inserted_experiments(
    inserted_agents: dict[int, str],
    experiment_storage: PsqlExperimentStorage,
    purged_psql_tenant_conn: PoolConnectionProxy,
):
    exp1 = fake_experiment(agent_id="agent1", id="exp1")
    await experiment_storage.create(exp1)

    exp2 = fake_experiment(agent_id="agent1", id="exp2")
    await experiment_storage.create(exp2)

    rows = await purged_psql_tenant_conn.fetch("SELECT uid, slug FROM experiments")
    return {row["slug"]: row["uid"] for row in rows}


class TestAgentUid:
    async def test_agent_uid_existing_agent(
        self,
        inserted_agents: dict[str, int],
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        agent_uid = await base_storage._agent_uid(purged_psql_tenant_conn, "agent1")
        assert agent_uid == inserted_agents["agent1"]

    async def test_agent_uid_nonexistent_agent(
        self,
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        with pytest.raises(ObjectNotFoundError):
            await base_storage._agent_uid(purged_psql_tenant_conn, "nonexistent")


class TestAgentUids:
    async def test_agent_uid_existing_agent(
        self,
        inserted_agents: dict[str, int],
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        agent_uid_map = await base_storage._agent_uids(purged_psql_tenant_conn, {"agent1", "agent2"})
        assert agent_uid_map == {"agent1": inserted_agents["agent1"], "agent2": inserted_agents["agent2"]}


class TestAgentIds:
    async def test_agent_ids_with_valid_uids(
        self,
        inserted_agents: dict[str, int],
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        agent_uids = set(inserted_agents.values())
        agent_ids = await base_storage._agent_ids(purged_psql_tenant_conn, agent_uids)
        assert agent_ids == {v: k for k, v in inserted_agents.items()}

    async def test_agent_ids_empty_set(
        self,
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        agent_ids = await base_storage._agent_ids(purged_psql_tenant_conn, set())
        assert agent_ids == {}

    async def test_agent_ids_nonexistent_uids(
        self,
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        nonexistent_uids = {999, 1000}
        agent_ids = await base_storage._agent_ids(purged_psql_tenant_conn, nonexistent_uids)
        assert agent_ids == {}


class TestExperimentUids:
    async def test_experiment_uids_with_valid_ids(
        self,
        inserted_experiments: dict[str, int],
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        experiment_ids = set(inserted_experiments.keys())
        experiment_uids = await base_storage._experiment_uids(purged_psql_tenant_conn, experiment_ids)
        assert experiment_uids == inserted_experiments

    async def test_experiment_uids_empty_set(
        self,
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        experiment_uids = await base_storage._experiment_uids(purged_psql_tenant_conn, set())
        assert experiment_uids == {}

    async def test_experiment_uids_nonexistent_ids(
        self,
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        nonexistent_ids = {"nonexistent1", "nonexistent2"}
        experiment_uids = await base_storage._experiment_uids(purged_psql_tenant_conn, nonexistent_ids)
        assert experiment_uids == {}


class TestExperimentIds:
    async def test_experiment_ids_with_valid_uids(
        self,
        inserted_experiments: dict[str, int],
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        experiment_uids = set(inserted_experiments.values())
        experiment_ids = await base_storage._experiment_ids(purged_psql_tenant_conn, experiment_uids)
        assert experiment_ids == {v: k for k, v in inserted_experiments.items()}

    async def test_experiment_ids_empty_set(
        self,
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        experiment_ids = await base_storage._experiment_ids(purged_psql_tenant_conn, set())
        assert experiment_ids == {}

    async def test_experiment_ids_nonexistent_uids(
        self,
        base_storage: PsqlBaseStorage,
        purged_psql_tenant_conn: PoolConnectionProxy,
    ):
        nonexistent_uids = {999, 1000}
        experiment_ids = await base_storage._experiment_ids(purged_psql_tenant_conn, nonexistent_uids)
        assert experiment_ids == {}


@pytest.mark.parametrize(("value", "expected"), [(None, None), ({"a": 1}, '{"a":1}'), ([1, 2, 3], "[1,2,3]")])
def test_psql_serialize_json(value: Any, expected: str | None):
    serialized = psql_serialize_json(value)
    assert serialized == expected
    assert _deserialize_json(serialized) == value

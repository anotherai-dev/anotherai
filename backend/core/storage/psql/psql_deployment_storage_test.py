# pyright: reportPrivateUsage=false

import uuid
from datetime import UTC, datetime

import asyncpg
import pytest

from core.domain.agent import Agent
from core.domain.deployment import Deployment
from core.domain.exceptions import ObjectNotFoundError
from core.storage.psql.psql_agent_storage import PsqlAgentsStorage
from core.storage.psql.psql_deployment_storage import PsqlDeploymentStorage, _DeploymentRow
from tests.fake_models import fake_deployment, fake_version


@pytest.fixture
async def test_agent(agent_storage: PsqlAgentsStorage):
    agent = Agent(uid=0, id=f"test-agent-{uuid.uuid4().hex[:8]}", name="Test Agent")
    await agent_storage.store_agent(agent)
    return agent


@pytest.fixture
def sample_deployment(test_agent: Agent):
    return fake_deployment(id=f"test-deployment-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)


class TestDeploymentRowFromDomain:
    def test_exhaustive(self):
        dep = fake_deployment()
        converted = _DeploymentRow.from_domain(1, dep)
        expected_fields = set(_DeploymentRow.model_fields)
        expected_fields -= {"tenant_uid", "uid", "deleted_at", "agent_slug"}

        assert converted.model_fields_set == expected_fields


class TestCreateDeployment:
    async def test_create_deployment(
        self,
        deployment_storage: PsqlDeploymentStorage,
        sample_deployment: Deployment,
    ):
        await deployment_storage.create_deployment(sample_deployment)

        # Verify the deployment was created
        retrieved = await deployment_storage.get_deployment(sample_deployment.id)
        assert retrieved.id == sample_deployment.id
        assert retrieved.agent_id == sample_deployment.agent_id
        assert retrieved.version.model == sample_deployment.version.model
        assert retrieved.created_by == sample_deployment.created_by
        assert retrieved.metadata == sample_deployment.metadata

    async def test_create_deployment_with_nonexistent_agent(
        self,
        deployment_storage: PsqlDeploymentStorage,
    ):
        deployment = Deployment(
            id="test-deployment",
            agent_id="nonexistent-agent",
            version=fake_version(),
            created_by="Test User",
            metadata={},
        )

        with pytest.raises(ObjectNotFoundError):
            await deployment_storage.create_deployment(deployment)

    async def test_create_deployment_different_tenant(
        self,
        psql_pool: asyncpg.Pool,
        sample_deployment: Deployment,
        deployment_storage: PsqlDeploymentStorage,
    ):
        # Create deployment in tenant 1
        await deployment_storage.create_deployment(sample_deployment)

        # Try to get it from tenant 2
        storage_tenant2 = PsqlDeploymentStorage(tenant_uid=2, pool=psql_pool)
        with pytest.raises(ObjectNotFoundError):
            _ = await storage_tenant2.get_deployment(sample_deployment.id)


class TestUpdateDeployment:
    async def test_update_deployment_version(
        self,
        deployment_storage: PsqlDeploymentStorage,
        sample_deployment: Deployment,
    ):
        await deployment_storage.create_deployment(sample_deployment)

        # Update version
        new_version = fake_version(model="gpt-4", temperature=0.8)
        updated = await deployment_storage.update_deployment(sample_deployment.id, new_version, None)

        assert updated.version.model == "gpt-4"
        assert updated.version.temperature == 0.8
        assert updated.id == sample_deployment.id

    async def test_update_deployment_metadata(
        self,
        deployment_storage: PsqlDeploymentStorage,
        sample_deployment: Deployment,
    ):
        await deployment_storage.create_deployment(sample_deployment)

        # Update metadata
        new_metadata = {"environment": "production", "region": "us-east-1"}
        updated = await deployment_storage.update_deployment(sample_deployment.id, None, new_metadata)

        assert updated.metadata == new_metadata
        assert updated.id == sample_deployment.id

    async def test_update_deployment_both_version_and_metadata(
        self,
        deployment_storage: PsqlDeploymentStorage,
        sample_deployment: Deployment,
    ):
        await deployment_storage.create_deployment(sample_deployment)

        # Update both version and metadata
        new_version = fake_version(model="claude-3-sonnet", max_output_tokens=4000)
        new_metadata = {"updated": True}
        updated = await deployment_storage.update_deployment(sample_deployment.id, new_version, new_metadata)

        assert updated.version.model == "claude-3-sonnet"
        assert updated.version.max_output_tokens == 4000
        assert updated.metadata == new_metadata

    async def test_update_nonexistent_deployment(
        self,
        deployment_storage: PsqlDeploymentStorage,
    ):
        with pytest.raises(ObjectNotFoundError):
            await deployment_storage.update_deployment("nonexistent-deployment", fake_version(), {"test": True})

    async def test_update_archived_deployment(
        self,
        deployment_storage: PsqlDeploymentStorage,
        sample_deployment: Deployment,
    ):
        await deployment_storage.create_deployment(sample_deployment)
        await deployment_storage.archive_deployment(sample_deployment.id)

        with pytest.raises(ObjectNotFoundError):
            await deployment_storage.update_deployment(sample_deployment.id, fake_version(), {"test": True})


class TestArchiveDeployment:
    async def test_archive_deployment(
        self,
        deployment_storage: PsqlDeploymentStorage,
        sample_deployment: Deployment,
    ):
        await deployment_storage.create_deployment(sample_deployment)

        # Archive the deployment
        await deployment_storage.archive_deployment(sample_deployment.id)

        # Verify it's archived - should be retrievable but marked as archived
        retrieved = await deployment_storage.get_deployment(sample_deployment.id)
        assert retrieved.archived_at is not None

    async def test_archive_nonexistent_deployment(
        self,
        deployment_storage: PsqlDeploymentStorage,
    ):
        with pytest.raises(ObjectNotFoundError):
            await deployment_storage.archive_deployment("nonexistent-deployment")

    async def test_archive_already_archived_deployment(
        self,
        deployment_storage: PsqlDeploymentStorage,
        sample_deployment: Deployment,
    ):
        await deployment_storage.create_deployment(sample_deployment)
        await deployment_storage.archive_deployment(sample_deployment.id)

        # Archiving again should raise ObjectNotFoundError
        with pytest.raises(ObjectNotFoundError):
            await deployment_storage.archive_deployment(sample_deployment.id)


class TestCountDeployments:
    async def test_count_all_deployments(
        self,
        deployment_storage: PsqlDeploymentStorage,
        test_agent: Agent,
    ):
        # Create multiple deployments
        for i in range(3):
            deployment = fake_deployment(id=f"deployment-{i}-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)
            await deployment_storage.create_deployment(deployment)

        count = await deployment_storage.count_deployments(None, False)
        assert count >= 3

    async def test_count_deployments_by_agent(
        self,
        deployment_storage: PsqlDeploymentStorage,
        agent_storage: PsqlAgentsStorage,
    ):
        # Create two agents
        agent1 = Agent(uid=0, id=f"agent-1-{uuid.uuid4().hex[:8]}", name="Agent 1")
        agent2 = Agent(uid=0, id=f"agent-2-{uuid.uuid4().hex[:8]}", name="Agent 2")
        await agent_storage.store_agent(agent1)
        await agent_storage.store_agent(agent2)

        # Create deployments for each agent
        await deployment_storage.create_deployment(
            fake_deployment(id=f"dep-1-{uuid.uuid4().hex[:8]}", agent_id=agent1.id),
        )
        await deployment_storage.create_deployment(
            fake_deployment(id=f"dep-2-{uuid.uuid4().hex[:8]}", agent_id=agent2.id),
        )
        await deployment_storage.create_deployment(
            fake_deployment(id=f"dep-3-{uuid.uuid4().hex[:8]}", agent_id=agent1.id),
        )

        # Count deployments for agent1
        count = await deployment_storage.count_deployments(agent1.id, False)
        assert count == 2

        # Count deployments for agent2
        count = await deployment_storage.count_deployments(agent2.id, False)
        assert count == 1

    async def test_count_deployments_include_archived(
        self,
        deployment_storage: PsqlDeploymentStorage,
        test_agent: Agent,
    ):
        # Create deployments
        active_deployment = fake_deployment(id=f"active-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)
        archived_deployment = fake_deployment(id=f"archived-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)

        await deployment_storage.create_deployment(active_deployment)
        await deployment_storage.create_deployment(archived_deployment)

        # Archive one deployment
        await deployment_storage.archive_deployment(archived_deployment.id)

        # Count excluding archived
        count_active = await deployment_storage.count_deployments(test_agent.id, False)

        # Count including archived
        count_all = await deployment_storage.count_deployments(test_agent.id, True)

        assert count_all == count_active + 1


class TestListDeployments:
    async def test_list_all_deployments(
        self,
        deployment_storage: PsqlDeploymentStorage,
        test_agent: Agent,
    ):
        # Create multiple deployments
        deployments: list[Deployment] = []
        for i in range(3):
            deployment = fake_deployment(id=f"deployment-{i}-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)
            deployments.append(deployment)
            await deployment_storage.create_deployment(deployment)

        # List all deployments
        retrieved = [deployment async for deployment in deployment_storage.list_deployments(None, None, False, 10)]

        # Should have at least our 3 deployments
        assert len(retrieved) >= 3

        # Check that our deployments are in the list
        retrieved_ids = [dep.id for dep in retrieved]
        for deployment in deployments:
            assert deployment.id in retrieved_ids

    async def test_list_deployments_by_agent(
        self,
        deployment_storage: PsqlDeploymentStorage,
        agent_storage: PsqlAgentsStorage,
    ):
        # Create two agents
        agent1 = Agent(uid=0, id="agent-1", name="Agent 1")
        agent2 = Agent(uid=0, id="agent-2", name="Agent 2")
        await agent_storage.store_agent(agent1)
        await agent_storage.store_agent(agent2)

        # Create deployments for each agent
        dep1 = fake_deployment(id="dep-1", agent_id=agent1.id)
        dep2 = fake_deployment(id="dep-2", agent_id=agent2.id)

        await deployment_storage.create_deployment(dep1)
        await deployment_storage.create_deployment(dep2)

        # List deployments for agent1 only
        retrieved = [deployment async for deployment in deployment_storage.list_deployments(agent1.id, None, False, 10)]

        # Should only have agent1's deployment
        assert len(retrieved) == 1
        assert retrieved[0].id == dep1.id
        assert retrieved[0].agent_id == agent1.id

    async def test_list_deployments_exclude_archived(
        self,
        deployment_storage: PsqlDeploymentStorage,
        test_agent: Agent,
    ):
        # Create deployments
        active_deployment = fake_deployment(id=f"active-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)
        archived_deployment = fake_deployment(id=f"archived-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)

        await deployment_storage.create_deployment(active_deployment)
        await deployment_storage.create_deployment(archived_deployment)

        # Archive one deployment
        await deployment_storage.archive_deployment(archived_deployment.id)

        # List deployments excluding archived
        retrieved = [
            deployment async for deployment in deployment_storage.list_deployments(test_agent.id, None, False, 10)
        ]

        # Should only have the active deployment
        retrieved_ids = [dep.id for dep in retrieved]
        assert active_deployment.id in retrieved_ids
        assert archived_deployment.id not in retrieved_ids

    async def test_list_deployments_include_archived(
        self,
        deployment_storage: PsqlDeploymentStorage,
        test_agent: Agent,
    ):
        # Create deployments
        active_deployment = fake_deployment(id=f"active-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)
        archived_deployment = fake_deployment(id=f"archived-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)

        await deployment_storage.create_deployment(active_deployment)
        await deployment_storage.create_deployment(archived_deployment)

        # Archive one deployment
        await deployment_storage.archive_deployment(archived_deployment.id)

        # List deployments including archived
        retrieved = [
            deployment async for deployment in deployment_storage.list_deployments(test_agent.id, None, True, 10)
        ]

        # Should have both deployments
        retrieved_ids = [dep.id for dep in retrieved]
        assert active_deployment.id in retrieved_ids
        assert archived_deployment.id in retrieved_ids
        assert len(retrieved) == 2

    async def test_list_deployments_with_created_before(
        self,
        deployment_storage: PsqlDeploymentStorage,
        test_agent: Agent,
    ):
        # Create deployment with specific created_at time
        past_time = datetime(2020, 1, 1, tzinfo=UTC)
        recent_time = datetime.now(UTC)

        old_deployment = fake_deployment(id=f"old-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id, created_at=past_time)
        new_deployment = fake_deployment(
            id=f"new-{uuid.uuid4().hex[:8]}",
            agent_id=test_agent.id,
            created_at=recent_time,
        )

        await deployment_storage.create_deployment(old_deployment)
        await deployment_storage.create_deployment(new_deployment)

        # List deployments created before a cutoff time
        cutoff_time = datetime(2021, 1, 1, tzinfo=UTC)
        retrieved = [
            deployment
            async for deployment in deployment_storage.list_deployments(test_agent.id, cutoff_time, False, 10)
        ]

        # Should only have the old deployment
        retrieved_ids = [dep.id for dep in retrieved]
        assert old_deployment.id in retrieved_ids
        assert new_deployment.id not in retrieved_ids

    async def test_list_deployments_with_limit(
        self,
        deployment_storage: PsqlDeploymentStorage,
        test_agent: Agent,
    ):
        # Create multiple deployments
        for i in range(5):
            deployment = fake_deployment(id=f"deployment-{i}-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)
            await deployment_storage.create_deployment(deployment)

        # List with limit
        retrieved = [
            deployment async for deployment in deployment_storage.list_deployments(test_agent.id, None, False, 2)
        ]

        # Should respect the limit
        assert len(retrieved) == 2

    async def test_list_deployments_different_tenant(
        self,
        psql_pool: asyncpg.Pool,
        test_agent: Agent,
        deployment_storage: PsqlDeploymentStorage,
    ):
        # Create deployment in tenant 1
        deployment = fake_deployment(id=f"deployment-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)
        await deployment_storage.create_deployment(deployment)

        # List from tenant 2
        storage_tenant2 = PsqlDeploymentStorage(tenant_uid=2, pool=psql_pool)
        retrieved = [dep async for dep in storage_tenant2.list_deployments(None, None, False, 10)]

        # Should not find the deployment from tenant 1
        retrieved_ids = [dep.id for dep in retrieved]
        assert deployment.id not in retrieved_ids


class TestGetDeployment:
    async def test_get_deployment(
        self,
        deployment_storage: PsqlDeploymentStorage,
        sample_deployment: Deployment,
    ):
        await deployment_storage.create_deployment(sample_deployment)

        retrieved = await deployment_storage.get_deployment(sample_deployment.id)
        assert retrieved.id == sample_deployment.id
        assert retrieved.agent_id == sample_deployment.agent_id
        assert retrieved.version.model == sample_deployment.version.model
        assert retrieved.created_by == sample_deployment.created_by
        assert retrieved.metadata == sample_deployment.metadata

    async def test_get_nonexistent_deployment(
        self,
        deployment_storage: PsqlDeploymentStorage,
    ):
        with pytest.raises(ObjectNotFoundError):
            _ = await deployment_storage.get_deployment("nonexistent-deployment")

    async def test_get_archived_deployment(
        self,
        deployment_storage: PsqlDeploymentStorage,
        sample_deployment: Deployment,
    ):
        await deployment_storage.create_deployment(sample_deployment)
        await deployment_storage.archive_deployment(sample_deployment.id)

        # Should still be able to get archived deployment
        retrieved = await deployment_storage.get_deployment(sample_deployment.id)
        assert retrieved.id == sample_deployment.id
        assert retrieved.archived_at is not None

    async def test_get_deployment_different_tenant(
        self,
        psql_pool: asyncpg.Pool,
        sample_deployment: Deployment,
        deployment_storage: PsqlDeploymentStorage,
    ):
        # Create deployment in tenant 1
        await deployment_storage.create_deployment(sample_deployment)

        # Try to get it from tenant 2
        storage_tenant2 = PsqlDeploymentStorage(tenant_uid=2, pool=psql_pool)
        with pytest.raises(ObjectNotFoundError):
            _ = await storage_tenant2.get_deployment(sample_deployment.id)

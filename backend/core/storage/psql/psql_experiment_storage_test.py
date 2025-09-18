import uuid
from datetime import UTC, datetime

import asyncpg
import pytest

from core.domain.agent import Agent
from core.domain.agent_input import AgentInput
from core.domain.exceptions import DuplicateValueError, ObjectNotFoundError
from core.domain.experiment import Experiment
from core.domain.message import Message
from core.domain.version import Version
from core.storage.experiment_storage import CompletionIDTuple
from core.storage.psql.psql_agent_storage import PsqlAgentsStorage
from core.storage.psql.psql_experiment_storage import PsqlExperimentStorage
from tests.fake_models import fake_experiment


@pytest.fixture
async def test_agent(agent_storage: PsqlAgentsStorage):
    agent = Agent(uid=0, id=f"test-agent-{uuid.uuid4().hex[:8]}", name="Test Agent")
    await agent_storage.store_agent(agent)
    return agent


@pytest.fixture
def sample_experiment(test_agent: Agent):
    return fake_experiment(id=f"test-experiment-{uuid.uuid4().hex[:8]}", agent_id=test_agent.id)


@pytest.fixture
async def inserted_experiment(
    test_agent: Agent,
    sample_experiment: Experiment,
    experiment_storage: PsqlExperimentStorage,
):
    await experiment_storage.create(sample_experiment)
    return sample_experiment


class TestCreate:
    async def test_create_experiment(
        self,
        experiment_storage: PsqlExperimentStorage,
        sample_experiment: Experiment,
    ):
        await experiment_storage.create(sample_experiment)

        # Verify the experiment was created
        retrieved = await experiment_storage.get_experiment(sample_experiment.id)
        assert retrieved.id == sample_experiment.id
        assert retrieved.title == sample_experiment.title
        assert retrieved.description == sample_experiment.description
        assert retrieved.author_name == sample_experiment.author_name
        assert retrieved.agent_id == sample_experiment.agent_id
        assert retrieved.metadata == sample_experiment.metadata

    async def test_create_experiment_with_nonexistent_agent(
        self,
        experiment_storage: PsqlExperimentStorage,
    ):
        experiment = Experiment(
            id="test-experiment",
            author_name="Test Author",
            title="Test Experiment",
            description="A test experiment",
            result=None,
            agent_id="nonexistent-agent",
            run_ids=[],
            metadata={},
        )

        with pytest.raises(ObjectNotFoundError):
            await experiment_storage.create(experiment)

    async def test_create_experiment_different_tenant(
        self,
        psql_pool: asyncpg.Pool,
        sample_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        # Create experiment in tenant 1
        await experiment_storage.create(sample_experiment)

        # Try to get it from tenant 2
        storage_tenant2 = PsqlExperimentStorage(tenant_uid=2, pool=psql_pool)
        with pytest.raises(ObjectNotFoundError):
            _ = await storage_tenant2.get_experiment(sample_experiment.id)


class TestSetResult:
    async def test_set_result(
        self,
        experiment_storage: PsqlExperimentStorage,
        sample_experiment: Experiment,
    ):
        await experiment_storage.create(sample_experiment)

        result = "Test completed successfully"
        await experiment_storage.set_result(sample_experiment.id, result)

        retrieved = await experiment_storage.get_experiment(sample_experiment.id)
        assert retrieved.result == result

    async def test_set_result_nonexistent_experiment(
        self,
        experiment_storage: PsqlExperimentStorage,
    ):
        # This should not raise an error - it's a valid operation that just doesn't match any rows
        await experiment_storage.set_result("nonexistent-experiment", "some result")


class TestAddRunId:
    async def test_add_run_id(
        self,
        experiment_storage: PsqlExperimentStorage,
        sample_experiment: Experiment,
    ):
        await experiment_storage.create(sample_experiment)

        run_id = "run-123"
        await experiment_storage.add_run_id(sample_experiment.id, run_id)

        retrieved = await experiment_storage.get_experiment(sample_experiment.id)
        assert retrieved.run_ids == [run_id]

        # Add it again to make sure it's not added again
        await experiment_storage.add_run_id(sample_experiment.id, run_id)
        retrieved = await experiment_storage.get_experiment(sample_experiment.id)
        assert retrieved.run_ids == [run_id]

    async def test_add_multiple_run_ids(
        self,
        experiment_storage: PsqlExperimentStorage,
        sample_experiment: Experiment,
    ):
        await experiment_storage.create(sample_experiment)

        run_ids = ["run-1", "run-2", "run-3"]
        for run_id in run_ids:
            await experiment_storage.add_run_id(sample_experiment.id, run_id)

        retrieved = await experiment_storage.get_experiment(sample_experiment.id)
        for run_id in run_ids:
            assert run_id in retrieved.run_ids

    async def test_add_run_id_nonexistent_experiment(
        self,
        experiment_storage: PsqlExperimentStorage,
    ):
        # This should not raise an error - it's a valid operation that just doesn't match any rows
        await experiment_storage.add_run_id("nonexistent-experiment", "run-123")


class TestDelete:
    async def test_delete_experiment(
        self,
        experiment_storage: PsqlExperimentStorage,
        sample_experiment: Experiment,
    ):
        await experiment_storage.create(sample_experiment)

        # Verify it exists
        retrieved = await experiment_storage.get_experiment(sample_experiment.id)
        assert retrieved is not None

        # Delete it
        await experiment_storage.delete(sample_experiment.id)

        # Verify it's gone
        with pytest.raises(ObjectNotFoundError):
            _ = await experiment_storage.get_experiment(sample_experiment.id)

    async def test_delete_nonexistent_experiment(
        self,
        experiment_storage: PsqlExperimentStorage,
    ):
        # This should not raise an error - it's a valid operation that just doesn't match any rows
        await experiment_storage.delete("nonexistent-experiment")


class TestListExperiments:
    async def test_list_experiments(
        self,
        experiment_storage: PsqlExperimentStorage,
        test_agent: Agent,
    ):
        # Create multiple experiments
        experiments: list[Experiment] = []
        for i in range(3):
            experiment = Experiment(
                id=f"test-experiment-{i}-{uuid.uuid4().hex[:8]}",
                author_name="Test Author",
                title=f"Test Experiment {i}",
                description=f"A test experiment {i}",
                result=None,
                agent_id=test_agent.id,
                run_ids=[],
                metadata={"index": i},
            )
            experiments.append(experiment)
            await experiment_storage.create(experiment)

        # List all experiments
        since = datetime(1960, 1, 1, tzinfo=UTC)
        retrieved = await experiment_storage.list_experiments(None, since, 10)

        # Should have at least our 3 experiments
        assert len(retrieved) >= 3

        # Check that our experiments are in the list
        retrieved_ids = [exp.id for exp in retrieved]
        for experiment in experiments:
            assert experiment.id in retrieved_ids

    async def test_list_experiments_by_agent(
        self,
        experiment_storage: PsqlExperimentStorage,
        agent_storage: PsqlAgentsStorage,
    ):
        # Create two agents
        agent1 = Agent(uid=0, id=f"agent-1-{uuid.uuid4().hex[:8]}", name="Agent 1")
        agent2 = Agent(uid=0, id=f"agent-2-{uuid.uuid4().hex[:8]}", name="Agent 2")
        await agent_storage.store_agent(agent1)
        await agent_storage.store_agent(agent2)

        # Create experiments for each agent
        exp1 = Experiment(
            id=f"exp-1-{uuid.uuid4().hex[:8]}",
            author_name="Author",
            title="Experiment 1",
            description="Description 1",
            result=None,
            agent_id=agent1.id,
            run_ids=[],
            metadata={},
        )
        exp2 = Experiment(
            id=f"exp-2-{uuid.uuid4().hex[:8]}",
            author_name="Author",
            title="Experiment 2",
            description="Description 2",
            result=None,
            agent_id=agent2.id,
            run_ids=[],
            metadata={},
        )

        await experiment_storage.create(exp1)
        await experiment_storage.create(exp2)

        # List experiments for agent1 only
        since = datetime(1960, 1, 1, tzinfo=UTC)
        retrieved = await experiment_storage.list_experiments(agent1.uid, since, 10)

        # Should only have agent1's experiment
        assert len(retrieved) == 1
        assert retrieved[0].id == exp1.id
        assert retrieved[0].agent_id == agent1.id

    async def test_list_experiments_with_limit(
        self,
        experiment_storage: PsqlExperimentStorage,
        test_agent: Agent,
    ):
        # Create multiple experiments
        for i in range(5):
            experiment = Experiment(
                id=f"test-experiment-{i}-{uuid.uuid4().hex[:8]}",
                author_name="Test Author",
                title=f"Test Experiment {i}",
                description=f"A test experiment {i}",
                result=None,
                agent_id=test_agent.id,
                run_ids=[],
                metadata={"index": i},
            )
            await experiment_storage.create(experiment)

        # List with limit
        since = datetime(1960, 1, 1, tzinfo=UTC)
        retrieved = await experiment_storage.list_experiments(None, since, 2)

        # Should respect the limit
        assert len(retrieved) == 2

    async def test_list_experiments_different_tenant(
        self,
        psql_pool: asyncpg.Pool,
        test_agent: Agent,
        experiment_storage: PsqlExperimentStorage,
    ):
        # Create experiment in tenant 1
        experiment = Experiment(
            id=f"test-experiment-{uuid.uuid4().hex[:8]}",
            author_name="Test Author",
            title="Test Experiment",
            description="A test experiment",
            result=None,
            agent_id=test_agent.id,
            run_ids=[],
            metadata={},
        )
        await experiment_storage.create(experiment)

        # List from tenant 2
        storage_tenant2 = PsqlExperimentStorage(tenant_uid=2, pool=psql_pool)  # type: ignore
        since = datetime(1960, 1, 1, tzinfo=UTC)
        retrieved = await storage_tenant2.list_experiments(None, since, 10)

        # Should not find the experiment from tenant 1
        retrieved_ids = [exp.id for exp in retrieved]
        assert experiment.id not in retrieved_ids


class TestGetExperiment:
    async def test_get_experiment(
        self,
        experiment_storage: PsqlExperimentStorage,
        sample_experiment: Experiment,
    ):
        await experiment_storage.create(sample_experiment)

        retrieved = await experiment_storage.get_experiment(sample_experiment.id)
        assert retrieved.id == sample_experiment.id
        assert retrieved.title == sample_experiment.title
        assert retrieved.description == sample_experiment.description
        assert retrieved.author_name == sample_experiment.author_name
        assert retrieved.agent_id == sample_experiment.agent_id
        assert retrieved.metadata == sample_experiment.metadata

    async def test_get_nonexistent_experiment(
        self,
        experiment_storage: PsqlExperimentStorage,
    ):
        with pytest.raises(ObjectNotFoundError):
            _ = await experiment_storage.get_experiment("nonexistent-experiment")

    async def test_get_deleted_experiment(
        self,
        experiment_storage: PsqlExperimentStorage,
        sample_experiment: Experiment,
    ):
        await experiment_storage.create(sample_experiment)
        await experiment_storage.delete(sample_experiment.id)

        with pytest.raises(ObjectNotFoundError):
            _ = await experiment_storage.get_experiment(sample_experiment.id)


class TestAddInputs:
    async def test_add_single_input(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        input = AgentInput(messages=[Message.with_text("Hello")], variables={"a": "b"})
        inserted = await experiment_storage.add_inputs(inserted_experiment.id, [input])
        assert inserted == {"96566260da4cac46ded8c8d969adaa74"}

        # If I try again, nothing should happen
        inserted = await experiment_storage.add_inputs(inserted_experiment.id, [input])
        assert inserted == set()

    async def test_add_multiple_inputs(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        input1 = AgentInput(messages=[Message.with_text("Hello")], variables={"a": "b"})
        input2 = AgentInput(messages=[Message.with_text("World")], variables={"x": 1})

        inserted = await experiment_storage.add_inputs(inserted_experiment.id, [input1, input2])
        assert inserted == {input1.id, input2.id}

        # Re-adding should insert nothing
        inserted_again = await experiment_storage.add_inputs(inserted_experiment.id, [input1, input2])
        assert inserted_again == set()

    async def test_add_inputs_nonexistent_experiment(
        self,
        experiment_storage: PsqlExperimentStorage,
    ):
        input = AgentInput(messages=[Message.with_text("Hello")], variables={"a": "b"})
        with pytest.raises(ObjectNotFoundError):
            await experiment_storage.add_inputs("nonexistent-exp", [input])


class TestAddVersions:
    async def test_add_single_version(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        version = Version(model="gpt-4o")
        inserted = await experiment_storage.add_versions(inserted_experiment.id, [version])
        assert inserted == {version.id}

        # Re-adding should insert nothing
        inserted_again = await experiment_storage.add_versions(inserted_experiment.id, [version])
        assert inserted_again == set()


class TestAddCompletions:
    async def test_add_single_completion(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        # Prepare prerequisites: one input and one version
        agent_input = AgentInput(messages=[Message.with_text("Hello")], variables={"x": 1})
        version = Version(model="gpt-4o")
        await experiment_storage.add_inputs(inserted_experiment.id, [agent_input])
        await experiment_storage.add_versions(inserted_experiment.id, [version])

        completion_id = uuid.uuid4()
        inserted = await experiment_storage.add_completions(
            inserted_experiment.id,
            [CompletionIDTuple(completion_id=completion_id, version_id=version.id, input_id=agent_input.id)],
        )
        assert inserted == {completion_id}

        # Re-adding same completion should insert nothing
        inserted_again = await experiment_storage.add_completions(
            inserted_experiment.id,
            [CompletionIDTuple(completion_id=completion_id, version_id=version.id, input_id=agent_input.id)],
        )
        assert inserted_again == set()

    async def test_add_completion_unknown_version_or_input(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        # No inputs/versions inserted; should raise when adding completion
        completion_id = uuid.uuid4()
        with pytest.raises(ObjectNotFoundError):
            await experiment_storage.add_completions(
                inserted_experiment.id,
                [
                    CompletionIDTuple(
                        completion_id=completion_id,
                        version_id="unknown-version",
                        input_id="unknown-input",
                    ),
                ],
            )


class TestStartCompletion:
    async def test_start_then_double_start_raises(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        # Prepare input, version, and completion
        agent_input = AgentInput(messages=[Message.with_text("Hi")], variables=None)
        version = Version(model="gpt-4o")
        await experiment_storage.add_inputs(inserted_experiment.id, [agent_input])
        await experiment_storage.add_versions(inserted_experiment.id, [version])

        completion_id = uuid.uuid4()
        await experiment_storage.add_completions(
            inserted_experiment.id,
            [CompletionIDTuple(completion_id=completion_id, version_id=version.id, input_id=agent_input.id)],
        )

        # First start should succeed
        await experiment_storage.start_completion(inserted_experiment.id, completion_id)

        # Second start should raise DuplicateValueError
        with pytest.raises(DuplicateValueError):
            await experiment_storage.start_completion(inserted_experiment.id, completion_id)

    async def test_start_nonexistent_completion_raises(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        with pytest.raises(ObjectNotFoundError):
            await experiment_storage.start_completion(inserted_experiment.id, uuid.uuid4())


class TestFailCompletion:
    async def test_fail_flow(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        # Prepare input, version, and completion
        agent_input = AgentInput(messages=[Message.with_text("Hi")], variables=None)
        version = Version(model="gpt-4o")
        await experiment_storage.add_inputs(inserted_experiment.id, [agent_input])
        await experiment_storage.add_versions(inserted_experiment.id, [version])

        completion_id = uuid.uuid4()
        await experiment_storage.add_completions(
            inserted_experiment.id,
            [CompletionIDTuple(completion_id=completion_id, version_id=version.id, input_id=agent_input.id)],
        )

        # Failing before start should raise DuplicateValueError (exists but not started)
        with pytest.raises(DuplicateValueError):
            await experiment_storage.fail_completion(inserted_experiment.id, completion_id)

        # Start then fail should succeed, and allow starting again
        await experiment_storage.start_completion(inserted_experiment.id, completion_id)
        await experiment_storage.fail_completion(inserted_experiment.id, completion_id)
        await experiment_storage.start_completion(inserted_experiment.id, completion_id)

    async def test_fail_nonexistent_completion_raises(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        with pytest.raises(ObjectNotFoundError):
            await experiment_storage.fail_completion(inserted_experiment.id, uuid.uuid4())

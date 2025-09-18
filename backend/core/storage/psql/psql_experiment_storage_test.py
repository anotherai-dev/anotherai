# pyright: reportPrivateUsage=false
import asyncio
import uuid
from datetime import UTC, datetime

import asyncpg
import pytest

from core.domain.agent import Agent
from core.domain.agent_input import AgentInput
from core.domain.agent_output import AgentOutput
from core.domain.error import Error
from core.domain.exceptions import DuplicateValueError, ObjectNotFoundError
from core.domain.experiment import Experiment
from core.domain.message import Message
from core.domain.version import Version
from core.storage.experiment_storage import CompletionIDTuple, CompletionOutputTuple
from core.storage.psql.psql_agent_storage import PsqlAgentsStorage
from core.storage.psql.psql_experiment_storage import PsqlExperimentStorage
from core.utils.uuid import uuid7
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

    async def test_get_experiment_include_versions(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        v1 = Version(model="gpt-4o")
        v2 = Version(model="gpt-4o-mini")
        inserted = await experiment_storage.add_versions(inserted_experiment.id, [v1, v2])
        assert inserted == {v1.id, v2.id}

        # Request only version ids
        exp_ids_only = await experiment_storage.get_experiment(
            inserted_experiment.id,
            include={"versions.id"},
        )
        assert exp_ids_only.versions is not None
        ids_only = sorted([v.id for v in exp_ids_only.versions])
        assert ids_only == sorted([v1.id, v2.id])
        # Minimal versions should still have id but no model
        assert all(v.id for v in exp_ids_only.versions)
        assert all(v.model is None for v in exp_ids_only.versions)

        # Request full versions
        exp_full = await experiment_storage.get_experiment(
            inserted_experiment.id,
            include={"versions"},
        )
        assert exp_full.versions is not None
        full_ids = sorted([v.id for v in exp_full.versions])
        assert full_ids == sorted([v1.id, v2.id])
        # Ensure model field is present
        models = sorted([m for m in (v.model for v in exp_full.versions) if m is not None])
        assert models == sorted(["gpt-4o", "gpt-4o-mini"])

    async def test_get_experiment_include_inputs(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        i1 = AgentInput(messages=[Message.with_text("I1")], variables=None, preview="I1")
        i2 = AgentInput(messages=None, variables={"x": 1}, preview="I2")
        inserted = await experiment_storage.add_inputs(inserted_experiment.id, [i1, i2])
        assert inserted == {i1.id, i2.id}

        # Request only input ids
        exp_ids_only = await experiment_storage.get_experiment(
            inserted_experiment.id,
            include={"inputs.id"},
        )
        assert exp_ids_only.inputs is not None
        ids_only = sorted([i.id for i in exp_ids_only.inputs])
        assert ids_only == sorted([i1.id, i2.id])
        assert all(i.messages is None and i.variables is None for i in exp_ids_only.inputs)

        # Request full inputs
        exp_full = await experiment_storage.get_experiment(
            inserted_experiment.id,
            include={"inputs"},
        )
        assert exp_full.inputs is not None
        full_ids = sorted([i.id for i in exp_full.inputs])
        assert full_ids == sorted([i1.id, i2.id])
        previews = sorted([i.preview for i in exp_full.inputs])
        assert previews == ["I1", "I2"]

    async def test_get_experiment_include_outputs(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        # Prepare inputs, versions and one output
        agent_input = AgentInput(messages=[Message.with_text("Question")], variables=None, preview="Q")
        version = Version(model="gpt-4o")
        await experiment_storage.add_inputs(inserted_experiment.id, [agent_input])
        await experiment_storage.add_versions(inserted_experiment.id, [version])
        completion_id = uuid7()
        await experiment_storage.add_completions(
            inserted_experiment.id,
            [CompletionIDTuple(completion_id=completion_id, version_id=version.id, input_id=agent_input.id)],
        )
        await experiment_storage.start_completion(inserted_experiment.id, completion_id)
        await experiment_storage.add_completion_output(
            inserted_experiment.id,
            completion_id,
            CompletionOutputTuple(
                output=AgentOutput(messages=[Message.with_text("Answer")], preview="Answer"),
                cost_usd=1.0,
                duration_seconds=2.0,
            ),
        )

        # Request outputs
        exp = await experiment_storage.get_experiment(inserted_experiment.id, include={"outputs"})
        assert exp.outputs is not None
        assert len(exp.outputs) == 1
        out = exp.outputs[0]
        assert out.completion_id == completion_id
        # get_experiment includes outputs with include={"output"} so messages should be present
        assert out.output is not None
        assert out.output.preview == "Answer"
        assert out.output.messages is not None
        assert out.output.messages[0].content[0].text == "Answer"


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


@pytest.fixture
async def inserted_input(inserted_experiment: Experiment, experiment_storage: PsqlExperimentStorage):
    agent_input = AgentInput(messages=[Message.with_text("Hi")], variables={"x": 1})
    await experiment_storage.add_inputs(inserted_experiment.id, [agent_input])
    return agent_input


@pytest.fixture
async def inserted_version(inserted_experiment: Experiment, experiment_storage: PsqlExperimentStorage):
    version = Version(model="gpt-4o")
    await experiment_storage.add_versions(inserted_experiment.id, [version])
    return version


class TestAddCompletion:
    async def test_add_completion(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
        inserted_input: AgentInput,
        inserted_version: Version,
    ):
        completion_id = uuid7()
        values = await experiment_storage.add_completions(
            inserted_experiment.id,
            [
                CompletionIDTuple(
                    completion_id=completion_id,
                    version_id=inserted_version.id,
                    input_id=inserted_input.id,
                ),
            ],
        )
        assert values == {completion_id}

        # Try again, it should do nothing
        values = await experiment_storage.add_completions(
            inserted_experiment.id,
            [
                CompletionIDTuple(
                    completion_id=completion_id,
                    version_id=inserted_version.id,
                    input_id=inserted_input.id,
                ),
            ],
        )
        assert values == set()


@pytest.fixture
async def inserted_completion(
    inserted_experiment: Experiment,
    experiment_storage: PsqlExperimentStorage,
    inserted_input: AgentInput,
    inserted_version: Version,
):
    completion_id = uuid7()
    await experiment_storage.add_completions(
        inserted_experiment.id,
        [CompletionIDTuple(completion_id=completion_id, version_id=inserted_version.id, input_id=inserted_input.id)],
    )
    return completion_id


class TestListExperimentCompletions:
    async def test_list_experiment_completions(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
        inserted_completion: uuid.UUID,
    ):
        completions = await experiment_storage.list_experiment_completions(inserted_experiment.id)
        assert len(completions) == 1
        assert completions[0].completion_id == inserted_completion

    async def test_list_experiment_completions_include(
        self,
        inserted_experiment: Experiment,
        experiment_storage: PsqlExperimentStorage,
    ):
        # Create an input and a version, then a completion with an output
        agent_input = AgentInput(messages=[Message.with_text("Hi")], variables=None)
        version = Version(model="gpt-4o")
        await experiment_storage.add_inputs(inserted_experiment.id, [agent_input])
        await experiment_storage.add_versions(inserted_experiment.id, [version])

        completion_id = uuid7()
        await experiment_storage.add_completions(
            inserted_experiment.id,
            [
                CompletionIDTuple(
                    completion_id=completion_id,
                    version_id=version.id,
                    input_id=agent_input.id,
                ),
            ],
        )
        await experiment_storage.start_completion(inserted_experiment.id, completion_id)
        await experiment_storage.add_completion_output(
            inserted_experiment.id,
            completion_id,
            CompletionOutputTuple(
                output=AgentOutput(messages=[Message.with_text("Answer")], preview="Answer"),
                cost_usd=1.0,
                duration_seconds=2.0,
            ),
        )

        # Without include, output messages and error should not be loaded, preview remains
        outputs_no_include = await experiment_storage.list_experiment_completions(inserted_experiment.id)
        assert len(outputs_no_include) == 1
        out = outputs_no_include[0]
        assert out.completion_id == completion_id
        assert out.output is not None
        assert out.output.preview == "Answer"
        assert out.output.messages is None
        assert out.output.error is None

        # With include={"output"}, messages should be present
        outputs_with_include = await experiment_storage.list_experiment_completions(
            inserted_experiment.id,
            include={"output"},
        )
        assert len(outputs_with_include) == 1
        out_inc = outputs_with_include[0]
        assert out_inc.output is not None
        assert out_inc.output.messages is not None
        assert out_inc.output.messages[0].content[0].text == "Answer"


async def test_output_flow(inserted_experiment: Experiment, experiment_storage: PsqlExperimentStorage):
    # First add 2 inputs
    input1 = AgentInput(messages=[Message.with_text("I1")], variables=None, preview="I1")
    input2 = AgentInput(messages=None, variables={"x": 1}, preview="I2")
    inserted_inputs = await experiment_storage.add_inputs(inserted_experiment.id, [input1, input2])
    assert inserted_inputs == {input1.id, input2.id}
    # Then add 2 versions
    version1 = Version(model="gpt-4o")
    version2 = Version(model="gpt-4o-mini")
    inserted_versions = await experiment_storage.add_versions(inserted_experiment.id, [version1, version2])
    assert inserted_versions == {version1.id, version2.id}

    # Then add 4 completions
    completions = [
        CompletionIDTuple(completion_id=uuid7(), version_id=vid, input_id=iid)
        for vid in [version1.id, version2.id]
        for iid in [input1.id, input2.id]
    ]
    inserted_completions = await experiment_storage.add_completions(inserted_experiment.id, completions)
    assert inserted_completions == {cid.completion_id for cid in completions}
    completion_id_list = [cid.completion_id for cid in completions]

    # Create tasks for each completion
    async def _completion_success(cid: uuid.UUID):
        await experiment_storage.start_completion(inserted_experiment.id, cid)
        await experiment_storage.add_completion_output(
            inserted_experiment.id,
            cid,
            CompletionOutputTuple(
                output=AgentOutput(messages=[Message.with_text("Answer")], preview="Answer"),
                cost_usd=1.23,
                duration_seconds=4.56,
            ),
        )

    async def _completion_failure(cid: uuid.UUID):
        await experiment_storage.start_completion(inserted_experiment.id, cid)
        await experiment_storage.add_completion_output(
            inserted_experiment.id,
            cid,
            CompletionOutputTuple(
                output=AgentOutput(error=Error(message="Error"), preview="Answer"),
                cost_usd=1.23,
                duration_seconds=4.56,
            ),
        )

    async def _other_error(cid: uuid.UUID):
        await experiment_storage.start_completion(inserted_experiment.id, cid)
        await experiment_storage.fail_completion(inserted_experiment.id, cid)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(_completion_success(completion_id_list[0]))
        tg.create_task(_completion_failure(completion_id_list[1]))
        tg.create_task(_other_error(completion_id_list[2]))
        # Last one will still be going

    outputs = await experiment_storage.list_experiment_completions(inserted_experiment.id)
    assert len(outputs) == 4
    assert {o.completion_id for o in outputs} == inserted_completions

# pyright: reportPrivateUsage=false

from typing import Any
from unittest.mock import Mock, patch
from uuid import UUID

import pytest

from core.domain.agent_input import AgentInput
from core.domain.exceptions import BadRequestError
from core.storage.experiment_storage import CompletionIDTuple
from protocol.api._api_models import ExperimentInput, Message, VersionRequest
from protocol.api._services.playground_service import (
    PlaygroundService,
    _validate_version,
    _version_request_with_override,
)
from tests.fake_models import fake_deployment, fake_experiment, fake_experiment_version, fake_input


@pytest.fixture
def mock_completion_runner():
    from core.services.completion_runner import CompletionRunner

    return Mock(spec=CompletionRunner)


@pytest.fixture
def playground_service(
    mock_completion_runner: Mock,
    mock_agent_storage: Mock,
    mock_experiment_storage: Mock,
    mock_completion_storage: Mock,
    mock_deployment_storage: Mock,
    mock_event_router: Mock,
):
    def _add_inputs(experiment_id: str, inputs: list[AgentInput]):
        return {i.id for i in inputs}

    mock_experiment_storage.add_inputs.side_effect = _add_inputs

    def _add_completions(experiment_id: str, completions: list[CompletionIDTuple]):
        return {c.completion_id for c in completions}

    mock_experiment_storage.add_completions.side_effect = _add_completions

    return PlaygroundService(
        completion_runner=mock_completion_runner,
        agent_storage=mock_agent_storage,
        experiment_storage=mock_experiment_storage,
        completion_storage=mock_completion_storage,
        deployment_storage=mock_deployment_storage,
        event_router=mock_event_router,
    )


@pytest.fixture
def patched_start_completions(playground_service: PlaygroundService):
    with patch.object(playground_service, "_start_experiment_completions") as mock:
        yield mock


class TestValidateVersion:
    @pytest.mark.parametrize(
        "model_id",
        [
            # Use a few known-good ids and aliases (see core/domain/models/models.py)
            "gpt-4o-2024-05-13",
            "gpt-4o-mini-latest",
            "gpt-4.1-mini-latest",
        ],
    )
    def test_accepts_valid_models(self, model_id: str):
        v = VersionRequest(model=model_id, prompt=[Message(content="You are a helpful assistant", role="system")])
        out = _validate_version(v)
        assert out.model  # normalized to canonical id or kept as is

    @pytest.mark.parametrize(
        "model_id",
        [
            "non-existent-model",
            "",
        ],
    )
    def test_rejects_invalid_models(self, model_id: str):
        v = VersionRequest(model=model_id)
        with pytest.raises(BadRequestError, match="Invalid model"):
            _validate_version(v)

    def test_rejects_versions_with_no_prompt(self):
        v = VersionRequest(model="gpt-4o-mini-latest")
        with pytest.raises(BadRequestError, match="Versions must have an explicit prompt parameter"):
            _validate_version(v)


class TestVersionById:
    async def test_deployment(
        self,
        playground_service: PlaygroundService,
        mock_deployment_storage: Mock,
        mock_completion_storage: Mock,
    ):
        """Version does not conform to hash so we guess it's a deployment"""
        d = fake_deployment()
        mock_deployment_storage.get_deployment.return_value = d

        v = await playground_service._get_version_by_id("test-agent", "anotherai/deployment/test-deployment")

        assert v.model == d.version.model

        mock_completion_storage.get_version_by_id.assert_not_called()
        mock_deployment_storage.get_deployment.assert_called_once_with("test-deployment")

    async def test_version_id(
        self,
        playground_service: PlaygroundService,
        mock_completion_storage: Mock,
        mock_deployment_storage: Mock,
    ):
        v = fake_experiment_version()
        mock_completion_storage.get_version_by_id.return_value = v, UUID(int=0)
        found = await playground_service._get_version_by_id("test-agent", v.id)
        assert found.model == v.model
        mock_completion_storage.get_version_by_id.assert_called_once_with("test-agent", v.id)
        mock_deployment_storage.get_deployment.assert_not_called()

    async def test_serialized_version(
        self,
        playground_service: PlaygroundService,
        mock_completion_storage: Mock,
        mock_deployment_storage: Mock,
    ):
        found = await playground_service._get_version_by_id("test-agent", '{"model": "gpt-4o-mini-latest"}')

        assert found.model == "gpt-4o-mini-latest"
        mock_completion_storage.get_version_by_id.assert_not_called()
        mock_deployment_storage.get_deployment.assert_not_called()


class TestVersionWithOverride:
    def test_valid_override_updates_fields(self):
        base = VersionRequest(model="gpt-4o-mini-latest", temperature=0.1, top_p=None)
        override = {"temperature": 0.5, "top_p": 0.9}
        out = _version_request_with_override(base, override)
        assert out.temperature == 0.5
        assert out.top_p == 0.9
        # model is preserved
        assert out.model

    @pytest.mark.parametrize(
        "override",
        [
            pytest.param({"tools": {"not": "a list"}}, id="wrong type for tools"),  # wrong type for tools
            pytest.param({"max_output_tokens": "abc"}, id="wrong type for int"),  # wrong type for int
            pytest.param({"temperature": "hot"}, id="wrong type for float"),  # wrong type for float
            pytest.param({"not_a_field": "value"}, id="wrong field"),  # wrong field
        ],
    )
    def test_invalid_override_raises(self, override: dict[str, Any]):
        base = VersionRequest(model="gpt-4o-mini-latest")
        with pytest.raises(BadRequestError, match="Invalid version with override"):
            _version_request_with_override(base, override)


class TestAddInputsToExperiment:
    async def test_compute_preview(self, playground_service: PlaygroundService, mock_experiment_storage: Mock):
        mock_experiment_storage.get_experiment.return_value = fake_experiment()

        inputs = [
            ExperimentInput(
                variables={
                    # A very long transcript
                    "transcript": "Good morning everyone. I'm calling from our headquarters in London to discuss the quarterly results. We had excellent performance in our Tokyo office this quarter, with sales up 15%. Our team in Berlin also exceeded expectations. Next month, I'll be traveling to Sydney to meet with our Australian partners, and then heading to Toronto for the North American summit.",
                },
            ),
        ]

        added = await playground_service.add_inputs_to_experiment(
            "test-experiment",
            inputs,
            None,
        )
        assert added == ["anotherai/input/3d79eb2916c751bdc814311f6e473f2b"]
        added_inputs: list[AgentInput] = mock_experiment_storage.add_inputs.call_args[0][1]
        assert len(added_inputs) == 1
        assert added_inputs[0].variables == inputs[0].variables
        assert added_inputs[0].id == "3d79eb2916c751bdc814311f6e473f2b"
        assert added_inputs[0].preview
        assert len(added_inputs[0].preview) <= 255

    async def test_start_experiment_completions(
        self,
        playground_service: PlaygroundService,
        mock_experiment_storage: Mock,
        patched_start_completions: Mock,
    ):
        version = fake_experiment_version()
        mock_experiment_storage.get_experiment.return_value = fake_experiment(
            versions=[version],
        )
        await playground_service.add_inputs_to_experiment(
            "test-experiment",
            [ExperimentInput(variables={"name": "John"})],
            None,
        )
        assert patched_start_completions.call_count == 1
        version_ids = set(patched_start_completions.call_args.kwargs["version_ids"])
        input_ids = set(patched_start_completions.call_args.kwargs["input_ids"])
        assert version_ids == {version.id}
        assert input_ids == {"88aebe2d32e9c7a0e8e3790db4ceddc1"}

    async def test_only_starting_completions_for_inserted_ids(
        self,
        playground_service: PlaygroundService,
        mock_experiment_storage: Mock,
        patched_start_completions: Mock,
    ):
        mock_experiment_storage.get_experiment.return_value = fake_experiment(
            versions=[fake_experiment_version()],
        )
        mock_experiment_storage.add_inputs.reset_mock()

        def _add_inputs(experiment_id: str, inputs: list[AgentInput]):
            assert len(inputs) == 2, "sanity"
            return {inputs[0].id}

        mock_experiment_storage.add_inputs.side_effect = _add_inputs

        res = await playground_service.add_inputs_to_experiment(
            "test-experiment",
            # Second input ID is 43396217dcb18701763a4d45e4de11b2
            [ExperimentInput(variables={"name": "John"}), ExperimentInput(variables={"name": "Jane"})],
            None,
        )
        assert patched_start_completions.call_count == 1
        # Only first input ID is included
        assert set(patched_start_completions.call_args.kwargs["input_ids"]) == {"88aebe2d32e9c7a0e8e3790db4ceddc1"}

        # Order is maintained and all ids are returned
        assert res == [
            "anotherai/input/88aebe2d32e9c7a0e8e3790db4ceddc1",
            "anotherai/input/43396217dcb18701763a4d45e4de11b2",
        ]


class TestStartExperimentCompletion:
    async def test_insert_count(
        self,
        playground_service: PlaygroundService,
        mock_experiment_storage: Mock,
        mock_event_router: Mock,
    ):
        versions = [
            fake_experiment_version(model="gpt-4o-mini-latest"),
            fake_experiment_version(model="gpt-4.1-mini-latest"),
        ]
        inputs = [fake_input(variables={"name": "John"}), fake_input(variables={"name": "Jane"})]

        assert len({v.id for v in versions}) == 2, "sanity"
        assert len({i.id for i in inputs}) == 2, "sanity"

        await playground_service._start_experiment_completions(
            "test-experiment",
            version_ids=(v.id for v in versions),
            input_ids=(i.id for i in inputs),
        )
        assert mock_experiment_storage.add_completions.call_count == 1
        completions = mock_experiment_storage.add_completions.call_args[0][1]
        assert len(completions) == 4

        # Check that the event router is called 4 times as well
        assert mock_event_router.call_count == 4

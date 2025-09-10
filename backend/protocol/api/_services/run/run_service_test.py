# pyright: reportPrivateUsage=false

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.domain.deployment import Deployment
from core.domain.exceptions import BadRequestError, JSONSchemaValidationError, ObjectNotFoundError
from core.domain.message import Message
from core.domain.models.model_data_mapping import get_model_id
from core.domain.models.models import Model
from core.domain.tenant_data import TenantData
from core.domain.version import Version
from core.services.completion_runner import CompletionRunner
from core.storage.deployment_storage import DeploymentStorage
from protocol.api._run_models import (
    OpenAIProxyChatCompletionRequest,
    OpenAIProxyMessage,
    OpenAIProxyResponseFormat,
)
from protocol.api._services.run.run_service import RunService, _EnvironmentRef, _extract_references, _ModelRef
from tests.utils import mock_aiter


def _proxy_request(**kwargs: Any):
    base = OpenAIProxyChatCompletionRequest(
        model="gpt-4o",
        messages=[
            OpenAIProxyMessage(
                role="user",
                content="Hello, how are you?",
            ),
        ],
    )
    return base.model_copy(update=kwargs)


class TestExtractReferences:
    @pytest.mark.parametrize(
        ("updates", "deployment_id"),
        [
            pytest.param(
                {"model": "anotherai/deployments/123"},
                "123",
                id="in model deployment plural",
            ),
            pytest.param(
                {"model": "anotherai/deployment/123"},
                "123",
                id="in model deployment single",
            ),
            pytest.param(
                {"model": "deployment/123"},
                "123",
                id="in model deployment single without anotherai prefix",
            ),
            pytest.param(
                {"deployment_id": "123"},
                "123",
                id="in body",
            ),
            pytest.param(
                {"deployment_id": "anotherai/deployment/123"},
                "123",
                id="in body deployment single with anotherai prefix",
            ),
        ],
    )
    def test_deployments(self, updates: dict[str, Any], deployment_id: str):
        request = _proxy_request(**updates)
        extracted = _extract_references(request)
        assert isinstance(extracted, _EnvironmentRef)
        assert extracted.deployment_id == deployment_id

    @pytest.mark.parametrize(
        ("updates", "expected_agent_id"),
        [
            pytest.param(
                {"model": "gpt-4o"},
                None,
                id="model_only",
            ),
            pytest.param(
                {"model": "agent-123/gpt-4o"},
                "agent-123",
                id="agent_in_model_path",
            ),
            pytest.param(
                {"model": "gpt-4o", "agent_id": "body-agent"},
                "body-agent",
                id="agent_in_body",
            ),
            pytest.param(
                {"model": "agent-in-path/gpt-4o", "metadata": {"agent_id": "meta-agent"}},
                "meta-agent",
                id="metadata_overrides_when_body_missing",
            ),
            pytest.param(
                {
                    "model": "agent-in-path/gpt-4o",
                    "agent_id": "body-agent",
                    "metadata": {"agent_id": "meta-agent"},
                },
                "body-agent",
                id="body_wins_over_metadata",
            ),
        ],
    )
    def test_model_references(self, updates: dict[str, Any], expected_agent_id: str | None):
        request = _proxy_request(**updates)
        extracted = _extract_references(request)
        assert isinstance(extracted, _ModelRef)
        assert extracted.model == get_model_id("gpt-4o")
        assert extracted.agent_id == expected_agent_id

    def test_invalid_environment_error(self):
        request = _proxy_request(model="agent/#schema/dev")
        with pytest.raises(BadRequestError) as excinfo:
            _extract_references(request)
        assert "does not refer to a valid model or deployment" in str(excinfo.value)


@pytest.fixture
def mock_tenant():
    return TenantData(uid=1, org_id="test-org")


@pytest.fixture
def mock_completion_runner():
    return Mock(spec=CompletionRunner)


@pytest.fixture
def mock_deployments_storage():
    return Mock(spec=DeploymentStorage)


@pytest.fixture
def run_service(mock_tenant: TenantData, mock_completion_runner: Mock, mock_deployments_storage: Mock):
    return RunService(
        tenant=mock_tenant,
        completion_runner=mock_completion_runner,
        deployments_storage=mock_deployments_storage,
    )


def _sample_messages():
    return [
        Message.with_text("You are a helpful assistant.", "system"),
        Message.with_text("Hello, how are you?", "user"),
    ]


class TestPrepareForDeployment:
    async def test_deployment_not_found(self, run_service: RunService, mock_deployments_storage: Mock):
        """Test that ObjectNotFoundError from storage raises BadRequestError"""
        mock_deployments_storage.get_deployment.side_effect = ObjectNotFoundError("deployment")

        with pytest.raises(BadRequestError) as excinfo:
            await run_service._prepare_for_deployment(
                deployment_id="nonexistent",
                messages=[],
                variables=None,
                response_format=None,
            )
        assert "Deployment nonexistent does not exist" in str(excinfo.value)

    async def test_invalid_input_variables(self, run_service: RunService, mock_deployments_storage: Mock):
        """Test that JSONSchemaValidationError from validate_input raises BadRequestError"""
        # Create mock deployment with version that will fail validation
        mock_version = Mock(spec=Version)
        mock_version.id = "test-version-id"
        mock_version.validate_input.side_effect = JSONSchemaValidationError("Invalid input")
        mock_version.output_schema = None

        mock_deployment = Deployment(
            id="test-deployment",
            agent_id="test-agent",
            version=mock_version,
            created_by="test-user",
            metadata=None,
        )

        mock_deployments_storage.get_deployment.return_value = mock_deployment

        with pytest.raises(BadRequestError) as excinfo:
            await run_service._prepare_for_deployment(
                deployment_id="test-deployment",
                messages=[],
                variables={"invalid": "data"},
                response_format=None,
            )
        assert "Deployment expected a different input" in str(excinfo.value)

    async def test_incompatible_output_schema(self, run_service: RunService, mock_deployments_storage: Mock):
        """Test that incompatible response format raises BadRequestError"""
        # Create mock deployment with incompatible output schema
        deployment_schema = Version.OutputSchema(
            json_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )
        mock_version = Mock(spec=Version)
        mock_version.id = "test-version-id"
        mock_version.output_schema = deployment_schema
        mock_version.validate_input.return_value = None

        mock_deployment = Deployment(
            id="test-deployment",
            agent_id="test-agent",
            version=mock_version,
            created_by="test-user",
            metadata=None,
        )

        mock_deployments_storage.get_deployment.return_value = mock_deployment

        # Mock the compatibility check to raise an error
        with patch(
            "protocol.api._services.run.run_service._check_output_schema_compatibility",
            side_effect=BadRequestError("Incompatible schema"),
        ):
            response_format = OpenAIProxyResponseFormat(type="json_object")

            with pytest.raises(BadRequestError) as excinfo:
                await run_service._prepare_for_deployment(
                    deployment_id="test-deployment",
                    messages=[],
                    variables=None,
                    response_format=response_format,
                )
            assert "Incompatible schema" in str(excinfo.value)

    async def test_successful_preparation(self, run_service: RunService, mock_deployments_storage: Mock):
        """Test successful deployment preparation"""
        mock_version = Mock(spec=Version)
        mock_version.id = "test-version-id"
        mock_version.output_schema = None
        mock_version.validate_input.return_value = None

        mock_deployment = Deployment(
            id="test-deployment",
            agent_id="test-agent",
            version=mock_version,
            created_by="test-user",
            metadata=None,
        )

        mock_deployments_storage.get_deployment.return_value = mock_deployment

        result = await run_service._prepare_for_deployment(
            deployment_id="test-deployment",
            messages=[],
            variables={"key": "value"},
            response_format=None,
        )

        assert result.agent_id == "test-agent"
        assert result.version == mock_version
        assert result.agent_input.messages == []
        assert result.agent_input.variables == {"key": "value"}
        assert result.metadata["anotherai/deployment_id"] == "test-deployment"


class TestPrepareForModel:
    async def test_variables_provided_no_template(self, run_service: RunService):
        """Test that variables provided without templated messages raises BadRequestError"""
        # Create messages without templates
        messages = [
            Message.with_text("Hello, how are you?", "user"),
        ]

        model_ref = _ModelRef(model=Model.GPT_4O_LATEST, agent_id="test-agent")

        # This should trigger the BadRequestError when variables are provided but no template is found
        with pytest.raises(BadRequestError) as excinfo:
            await run_service._prepare_for_model(
                agent_ref=model_ref,
                messages=messages,
                variables={"key": "value"},
                response_format=None,
            )
        assert "Input variables are provided but the messages do not contain a valid template" in str(
            excinfo.value,
        )

    async def test_extract_output_schema_validation_error(self, run_service: RunService):
        """Test that invalid output schema raises validation error"""
        messages = [Message.with_text("Hello", "user")]
        model_ref = _ModelRef(model=Model.GPT_4O_LATEST, agent_id="test-agent")

        # Mock _extract_output_schema to raise a validation error
        with patch(
            "protocol.api._services.run.run_service._extract_output_schema",
            side_effect=BadRequestError("Invalid response format schema"),
        ):
            with pytest.raises(BadRequestError) as excinfo:
                await run_service._prepare_for_model(
                    agent_ref=model_ref,
                    messages=messages,
                    variables=None,
                    response_format=OpenAIProxyResponseFormat(type="json_object"),
                )
            assert "Invalid response format schema" in str(excinfo.value)

    async def test_successful_preparation_no_variables(self, run_service: RunService):
        """Test successful model preparation without variables"""
        messages = [
            Message.with_text("You are a helpful assistant.", "system"),
            Message.with_text("Hello, how are you?", "user"),
        ]

        model_ref = _ModelRef(model=Model.GPT_4O_LATEST, agent_id="test-agent")

        result = await run_service._prepare_for_model(
            agent_ref=model_ref,
            messages=messages,
            variables=None,
            response_format=None,
        )

        assert result.agent_id == "test-agent"
        assert result.version.model == Model.GPT_4O_LATEST
        assert result.version.output_schema is None
        assert result.version.input_variables_schema is None
        assert result.version.prompt is None
        assert result.agent_input.messages == messages
        assert result.agent_input.variables is None
        assert result.metadata == {}

    async def test_successful_preparation_with_variables(self, run_service: RunService):
        """Test successful model preparation with variables and templates"""
        messages = [
            Message.with_text("You are a {{ role }} assistant.", "system"),
            Message.with_text("Hello, how are you?", "user"),
        ]

        model_ref = _ModelRef(model=Model.GPT_4O_LATEST, agent_id="test-agent")

        # Mock the schema generation functions

        result = await run_service._prepare_for_model(
            agent_ref=model_ref,
            messages=messages,
            variables={"role": "helpful"},
            response_format=None,
        )

        assert result.agent_id == "test-agent"
        assert result.version.model == Model.GPT_4O_LATEST
        assert result.version.input_variables_schema == {"type": "object", "properties": {"role": {"type": "string"}}}
        assert result.version.prompt == [messages[0]]  # First message should be in prompt
        assert result.agent_input.messages == messages[1:]  # Rest should be in messages
        assert result.agent_input.variables == {"role": "helpful"}

    async def test_default_agent_id_when_none(self, run_service: RunService):
        """Test that default agent_id is used when model_ref.agent_id is None"""
        messages = [Message.with_text("Hello", "user")]
        model_ref = _ModelRef(model=Model.GPT_4O_LATEST, agent_id=None)

        result = await run_service._prepare_for_model(
            agent_ref=model_ref,
            messages=messages,
            variables=None,
            response_format=None,
        )

        assert result.agent_id == "default"


class TestMissingModelError:
    async def test_missing_model_none(self, mock_deployments_storage: Mock):
        """Test that missing model (None) returns appropriate error"""

        result = await RunService.missing_model_error(
            model=None,
            list_deployment_ids=mock_deployments_storage.list_deployment_ids,
        )
        assert isinstance(result, BadRequestError)
        expected_message = "Missing model. To list all models programmatically: Use the list_models tool"
        assert str(result) == expected_message

    async def test_missing_model_empty_string(self, mock_deployments_storage: Mock):
        """Test that missing model (empty string) returns appropriate error"""

        result = await RunService.missing_model_error(
            model="",
            list_deployment_ids=mock_deployments_storage.list_deployment_ids,
        )
        assert isinstance(result, BadRequestError)
        expected_message = "Missing model. To list all models programmatically: Use the list_models tool"
        assert str(result) == expected_message

    @patch("protocol.api._services.run.run_service.suggest_model")
    async def test_invalid_model_no_deployments_no_suggestion(
        self,
        mock_suggest_model: AsyncMock,
        mock_deployments_storage: Mock,
    ):
        """Test invalid model with no deployments and no suggestion"""
        mock_suggest_model.return_value = None
        mock_deployments_storage.list_deployment_ids.return_value = mock_aiter("deployment-1", "deployment-2")

        result = await RunService.missing_model_error(
            model="invalid-model",
            list_deployment_ids=mock_deployments_storage.list_deployment_ids,
        )
        assert isinstance(result, BadRequestError)
        expected_message = """invalid-model does not refer to a valid model or deployment ['deployment-1', 'deployment-2']. The accepted formats are:
- <model>: a valid model name or alias
- <agent_id>/<model>: passing an agent_id as a prefix
- anotherai/deployment/<deployment_id>: passing a deployment id

To list all models programmatically: Use the list_models tool
To list all deployments programmatically: Use the list_deployments tool"""
        assert str(result) == expected_message
        mock_suggest_model.assert_called_once_with("invalid-model", ["deployment-1", "deployment-2"])

    @patch("protocol.api._services.run.run_service.suggest_model")
    async def test_invalid_model_with_deployments_no_suggestion(
        self,
        mock_suggest_model: AsyncMock,
        mock_deployments_storage: Mock,
    ):
        """Test invalid model with deployments available but no suggestion"""
        mock_suggest_model.return_value = None

        mock_deployments_storage.list_deployment_ids.return_value = mock_aiter("deployment-1", "deployment-2")

        result = await RunService.missing_model_error(
            model="invalid-model",
            list_deployment_ids=mock_deployments_storage.list_deployment_ids,
        )
        assert isinstance(result, BadRequestError)
        expected_message = """invalid-model does not refer to a valid model or deployment ['deployment-1', 'deployment-2']. The accepted formats are:
- <model>: a valid model name or alias
- <agent_id>/<model>: passing an agent_id as a prefix
- anotherai/deployment/<deployment_id>: passing a deployment id

To list all models programmatically: Use the list_models tool
To list all deployments programmatically: Use the list_deployments tool"""
        assert str(result) == expected_message
        mock_suggest_model.assert_called_once_with("invalid-model", ["deployment-1", "deployment-2"])

    @patch("protocol.api._services.run.run_service.suggest_model")
    async def test_invalid_model_with_suggestion(self, mock_suggest_model: AsyncMock, mock_deployments_storage: Mock):
        """Test invalid model with suggestion provided"""
        mock_suggest_model.return_value = "gpt-4o"

        mock_deployments_storage.list_deployment_ids.return_value = mock_aiter()

        result = await RunService.missing_model_error(
            model="gpt4o",
            list_deployment_ids=mock_deployments_storage.list_deployment_ids,
        )
        assert isinstance(result, BadRequestError)
        expected_message = """gpt4o does not refer to a valid model . The accepted formats are:
- <model>: a valid model name or alias
- <agent_id>/<model>: passing an agent_id as a prefix

Did you mean gpt-4o?
To list all models programmatically: Use the list_models tool"""
        assert str(result) == expected_message
        mock_suggest_model.assert_called_once_with("gpt4o", [])

    @patch("protocol.api._services.run.run_service.suggest_model")
    async def test_invalid_model_with_deployments_and_suggestion(
        self,
        mock_suggest_model: AsyncMock,
        mock_deployments_storage: Mock,
    ):
        """Test invalid model with both deployments and suggestion"""
        mock_suggest_model.return_value = "claude-3-sonnet"
        mock_deployments_storage.list_deployment_ids.return_value = mock_aiter("my-agent:prod", "my-agent:dev")

        result = await RunService.missing_model_error(
            model="claude-sonnet",
            list_deployment_ids=mock_deployments_storage.list_deployment_ids,
        )
        assert isinstance(result, BadRequestError)
        expected_message = """claude-sonnet does not refer to a valid model or deployment ['my-agent:prod', 'my-agent:dev']. The accepted formats are:
- <model>: a valid model name or alias
- <agent_id>/<model>: passing an agent_id as a prefix
- anotherai/deployment/<deployment_id>: passing a deployment id
Did you mean claude-3-sonnet?

To list all models programmatically: Use the list_models tool
To list all deployments programmatically: Use the list_deployments tool"""
        assert str(result) == expected_message
        mock_suggest_model.assert_called_once_with("claude-sonnet", ["my-agent:prod", "my-agent:dev"])

    async def test_no_deployment_list_function(self):
        """Test when list_deployment_ids is None"""
        result = await RunService.missing_model_error(
            model="invalid-model",
            list_deployment_ids=None,
        )
        assert isinstance(result, BadRequestError)
        expected_message = """invalid-model does not refer to a valid model . The accepted formats are:
- <model>: a valid model name or alias
- <agent_id>/<model>: passing an agent_id as a prefix

To list all models programmatically: Use the list_models tool"""
        assert str(result) == expected_message

from unittest.mock import Mock

import pytest

from core.domain.exceptions import BadRequestError, ObjectNotFoundError
from core.domain.version import Version
from core.storage.completion_storage import CompletionStorage
from core.storage.deployment_storage import DeploymentStorage
from protocol.api._api_models import Deployment
from protocol.api._services.deployment_service import DeploymentService
from tests.fake_models import fake_deployment, fake_version


@pytest.fixture
def mock_deployments_storage() -> DeploymentStorage:
    return Mock(spec=DeploymentStorage)


@pytest.fixture
def mock_completions_storage() -> CompletionStorage:
    return Mock(spec=CompletionStorage)


@pytest.fixture
def deployment_service(
    mock_deployments_storage: DeploymentStorage,
    mock_completions_storage: CompletionStorage,
) -> DeploymentService:
    return DeploymentService(mock_deployments_storage, mock_completions_storage)


class TestUpsertDeployment:
    async def test_create_new_deployment_when_not_exists(
        self,
        deployment_service: DeploymentService,
        mock_completions_storage: Mock,
        mock_deployments_storage: Mock,
    ):
        """Test creating a new deployment when deployment_id doesn't exist."""
        # Arrange
        agent_id = "agent-123"
        version_id = "version-456"
        deployment_id = "deployment-789"
        author_name = "test-author"
        completion_id = "completion-abc"

        test_version = fake_version()
        mock_completions_storage.get_version_by_id.return_value = (test_version, completion_id)
        mock_deployments_storage.get_deployment.side_effect = ObjectNotFoundError("Deployment")

        # Act
        result = await deployment_service.upsert_deployment(agent_id, version_id, deployment_id, author_name)

        # Assert
        mock_completions_storage.get_version_by_id.assert_called_once_with(agent_id, version_id)
        mock_deployments_storage.get_deployment.assert_called_once_with(deployment_id)
        mock_deployments_storage.create_deployment.assert_called_once()

        # Check the created deployment
        created_deployment = mock_deployments_storage.create_deployment.call_args[0][0]
        assert created_deployment.id == deployment_id
        assert created_deployment.agent_id == agent_id
        assert created_deployment.version == test_version
        assert created_deployment.created_by == author_name
        assert created_deployment.metadata == {}

        # Result should be a converted deployment
        assert isinstance(result, Deployment)
        assert result.id == deployment_id

    async def test_return_confirmation_url_when_deployment_exists_and_compatible(
        self,
        deployment_service: DeploymentService,
        mock_completions_storage: Mock,
        mock_deployments_storage: Mock,
    ):
        """Test returning confirmation URL when deployment exists and schemas are compatible."""
        # Arrange
        agent_id = "agent-123"
        version_id = "version-456"
        deployment_id = "deployment-789"
        author_name = "test-author"
        completion_id = "completion-abc"

        # Create compatible versions (same schemas)
        input_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        output_schema = {"type": "object", "properties": {"result": {"type": "string"}}}
        output_schema_obj = Version.OutputSchema(json_schema=output_schema)

        existing_version = fake_version(
            input_variables_schema=input_schema,
            output_schema=output_schema_obj,
        )
        new_version = fake_version(
            input_variables_schema=input_schema,
            output_schema=output_schema_obj,
        )

        existing_deployment = fake_deployment(
            id=deployment_id,
            agent_id=agent_id,
            version=existing_version,
        )

        mock_completions_storage.get_version_by_id.return_value = (new_version, completion_id)
        mock_deployments_storage.get_deployment.return_value = existing_deployment

        # Act
        result = await deployment_service.upsert_deployment(agent_id, version_id, deployment_id, author_name)

        # Assert
        mock_completions_storage.get_version_by_id.assert_called_once_with(agent_id, version_id)
        mock_deployments_storage.get_deployment.assert_called_once_with(deployment_id)
        mock_deployments_storage.create_deployment.assert_not_called()

        # Result should be a confirmation URL
        assert isinstance(result, str)
        assert "http://localhost:3000/deploy" in result
        assert f"deployment_id={deployment_id}" in result
        assert f"completion_id={completion_id}" in result

    async def test_input_schema_incompatibility_new_version_has_none_existing_has_schema(
        self,
        deployment_service: DeploymentService,
        mock_completions_storage: Mock,
        mock_deployments_storage: Mock,
    ):
        """Test failure when new version has no input schema but existing deployment does."""
        # Arrange
        agent_id = "agent-123"
        version_id = "version-456"
        deployment_id = "deployment-789"
        author_name = "test-author"
        completion_id = "completion-abc"

        existing_version = fake_version(
            input_variables_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )
        new_version = fake_version(input_variables_schema=None)

        existing_deployment = fake_deployment(version=existing_version)

        mock_completions_storage.get_version_by_id.return_value = (new_version, completion_id)
        mock_deployments_storage.get_deployment.return_value = existing_deployment

        # Act & Assert
        with pytest.raises(BadRequestError) as exc_info:
            await deployment_service.upsert_deployment(agent_id, version_id, deployment_id, author_name)

        assert "no input variables" in str(exc_info.value)
        assert "existing deployment does" in str(exc_info.value)

    async def test_input_schema_incompatibility_new_version_has_schema_existing_has_none(
        self,
        deployment_service: DeploymentService,
        mock_completions_storage: Mock,
        mock_deployments_storage: Mock,
    ):
        """Test failure when new version has input schema but existing deployment doesn't."""
        # Arrange
        agent_id = "agent-123"
        version_id = "version-456"
        deployment_id = "deployment-789"
        author_name = "test-author"
        completion_id = "completion-abc"

        existing_version = fake_version(input_variables_schema=None)
        new_version = fake_version(
            input_variables_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )

        existing_deployment = fake_deployment(version=existing_version)

        mock_completions_storage.get_version_by_id.return_value = (new_version, completion_id)
        mock_deployments_storage.get_deployment.return_value = existing_deployment

        # Act & Assert
        with pytest.raises(BadRequestError) as exc_info:
            await deployment_service.upsert_deployment(agent_id, version_id, deployment_id, author_name)

        assert "expects input variables" in str(exc_info.value)
        assert "existing deployment does not" in str(exc_info.value)

    async def test_output_schema_incompatibility_new_version_has_none_existing_has_schema(
        self,
        deployment_service: DeploymentService,
        mock_completions_storage: Mock,
        mock_deployments_storage: Mock,
    ):
        """Test failure when new version has no output schema but existing deployment does."""
        # Arrange
        agent_id = "agent-123"
        version_id = "version-456"
        deployment_id = "deployment-789"
        author_name = "test-author"
        completion_id = "completion-abc"

        output_schema_obj = Version.OutputSchema(
            json_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        )

        existing_version = fake_version(
            output_schema=output_schema_obj,
        )
        new_version = fake_version(output_schema=None)

        existing_deployment = fake_deployment(version=existing_version)

        mock_completions_storage.get_version_by_id.return_value = (new_version, completion_id)
        mock_deployments_storage.get_deployment.return_value = existing_deployment

        # Act & Assert
        with pytest.raises(BadRequestError) as exc_info:
            await deployment_service.upsert_deployment(agent_id, version_id, deployment_id, author_name)

        assert "no output schema" in str(exc_info.value)
        assert "existing deployment does" in str(exc_info.value)

    async def test_output_schema_incompatibility_new_version_has_schema_existing_has_none(
        self,
        deployment_service: DeploymentService,
        mock_completions_storage: Mock,
        mock_deployments_storage: Mock,
    ):
        """Test failure when new version has output schema but existing deployment doesn't."""
        # Arrange
        agent_id = "agent-123"
        version_id = "version-456"
        deployment_id = "deployment-789"
        author_name = "test-author"
        completion_id = "completion-abc"

        output_schema_obj = Version.OutputSchema(
            json_schema={"type": "object", "properties": {"result": {"type": "string"}}},
        )

        existing_version = fake_version(output_schema=None)
        new_version = fake_version(
            output_schema=output_schema_obj,
        )

        existing_deployment = fake_deployment(version=existing_version)

        mock_completions_storage.get_version_by_id.return_value = (new_version, completion_id)
        mock_deployments_storage.get_deployment.return_value = existing_deployment

        # Act & Assert
        with pytest.raises(BadRequestError) as exc_info:
            await deployment_service.upsert_deployment(agent_id, version_id, deployment_id, author_name)

        assert "has an output schema" in str(exc_info.value)
        assert "existing deployment does not" in str(exc_info.value)

    async def test_input_schema_structural_incompatibility(
        self,
        deployment_service: DeploymentService,
        mock_completions_storage: Mock,
        mock_deployments_storage: Mock,
    ):
        """Test failure when input schemas have different structures."""
        # Arrange
        agent_id = "agent-123"
        version_id = "version-456"
        deployment_id = "deployment-789"
        author_name = "test-author"
        completion_id = "completion-abc"

        # Different object properties - incompatible schemas
        existing_schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        new_schema = {"type": "object", "properties": {"id": {"type": "number"}}}

        existing_version = fake_version(input_variables_schema=existing_schema)
        new_version = fake_version(input_variables_schema=new_schema)

        existing_deployment = fake_deployment(version=existing_version)

        mock_completions_storage.get_version_by_id.return_value = (new_version, completion_id)
        mock_deployments_storage.get_deployment.return_value = existing_deployment

        # Act & Assert
        with pytest.raises(BadRequestError) as exc_info:
            await deployment_service.upsert_deployment(agent_id, version_id, deployment_id, author_name)

        assert "not compatible" in str(exc_info.value)

    async def test_output_schema_structural_incompatibility(
        self,
        deployment_service: DeploymentService,
        mock_completions_storage: Mock,
        mock_deployments_storage: Mock,
    ):
        """Test failure when output schemas have different structures."""
        # Arrange
        agent_id = "agent-123"
        version_id = "version-456"
        deployment_id = "deployment-789"
        author_name = "test-author"
        completion_id = "completion-abc"

        # Different types - incompatible schemas
        existing_schema = {"type": "string"}
        new_schema = {"type": "number"}

        existing_output_schema = Version.OutputSchema(json_schema=existing_schema)
        new_output_schema = Version.OutputSchema(json_schema=new_schema)

        existing_version = fake_version(output_schema=existing_output_schema)
        new_version = fake_version(output_schema=new_output_schema)

        existing_deployment = fake_deployment(version=existing_version)

        mock_completions_storage.get_version_by_id.return_value = (new_version, completion_id)
        mock_deployments_storage.get_deployment.return_value = existing_deployment

        # Act & Assert
        with pytest.raises(BadRequestError) as exc_info:
            await deployment_service.upsert_deployment(agent_id, version_id, deployment_id, author_name)

        assert "not compatible" in str(exc_info.value)

    async def test_both_schemas_compatible_null_values(
        self,
        deployment_service: DeploymentService,
        mock_completions_storage: Mock,
        mock_deployments_storage: Mock,
    ):
        """Test success when both deployments have no schemas (null values)."""
        # Arrange
        agent_id = "agent-123"
        version_id = "version-456"
        deployment_id = "deployment-789"
        author_name = "test-author"
        completion_id = "completion-abc"

        # Both versions have no schemas - should be compatible
        existing_version = fake_version(
            input_variables_schema=None,
            output_schema=None,
        )
        new_version = fake_version(
            input_variables_schema=None,
            output_schema=None,
        )

        existing_deployment = fake_deployment(version=existing_version)

        mock_completions_storage.get_version_by_id.return_value = (new_version, completion_id)
        mock_deployments_storage.get_deployment.return_value = existing_deployment

        # Act
        result = await deployment_service.upsert_deployment(agent_id, version_id, deployment_id, author_name)

        # Assert
        mock_completions_storage.get_version_by_id.assert_called_once_with(agent_id, version_id)
        mock_deployments_storage.get_deployment.assert_called_once_with(deployment_id)
        mock_deployments_storage.create_deployment.assert_not_called()

        # Result should be a confirmation URL
        assert isinstance(result, str)
        assert "http://localhost:3000/deploy" in result
        assert f"deployment_id={deployment_id}" in result
        assert f"completion_id={completion_id}" in result

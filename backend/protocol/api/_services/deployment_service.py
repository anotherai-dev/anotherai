from datetime import UTC, datetime

from structlog import get_logger

from core.consts import ANOTHERAI_APP_URL
from core.domain.deployment import Deployment as DomainDeployment
from core.domain.exceptions import BadRequestError, ObjectNotFoundError
from core.domain.version import Version
from core.storage.completion_storage import CompletionStorage
from core.storage.deployment_storage import DeploymentStorage
from core.utils.schemas import IncompatibleSchemaError, JsonSchema
from protocol.api._api_models import Deployment, DeploymentCreate, DeploymentUpdate, Page
from protocol.api._services.conversions import (
    deployment_from_domain,
    page_token_from_datetime,
    page_token_to_datetime,
    version_to_domain,
)

_log = get_logger(__name__)


class DeploymentService:
    def __init__(self, deployments_storage: DeploymentStorage, completions_storage: CompletionStorage):
        self._deployments_storage = deployments_storage
        self._completions_storage = completions_storage

    async def get_deployment(self, deployment_id: str):
        deployment = await self._deployments_storage.get_deployment(deployment_id)
        return deployment_from_domain(deployment)

    async def list_deployments(
        self,
        agent_id: str | None,
        page_token: str | None,
        include_archived: bool,
        limit: int,
    ):
        created_before = page_token_to_datetime(page_token)

        # TODO: run both in //
        deployments = [
            deployment_from_domain(d)
            async for d in self._deployments_storage.list_deployments(agent_id, created_before, include_archived, limit)
        ]

        try:
            total = await self._deployments_storage.count_deployments(agent_id, include_archived)
        except Exception as e:  # noqa: BLE001
            _log.warning("Failed to count deployments", exc_info=e)
            total = 0

        return Page(
            items=deployments,
            total=total,
            next_page_token=page_token_from_datetime(deployments[-1].created_at) if deployments else None,
        )

    async def create_deployment(self, deployment: DeploymentCreate) -> Deployment:
        inserted = DomainDeployment(
            id=deployment.id,
            agent_id=deployment.agent_id,
            version=version_to_domain(deployment.version),
            created_by=deployment.created_by,
            created_at=datetime.now(UTC),
            metadata=deployment.metadata,
        )
        await self._deployments_storage.create_deployment(inserted)
        return deployment_from_domain(inserted)

    async def update_deployment(self, deployment_id: str, deployment: DeploymentUpdate) -> Deployment:
        if deployment.version:
            # We are ok with race conditions here (fetch then update)
            # Deployment compat should be transitive and we are just trying to check the new version is compatible
            existing = await self._deployments_storage.get_deployment(deployment_id)
            _check_input_schema_compatibility(existing, version_to_domain(deployment.version))
            _check_output_schema_compatibility(existing, version_to_domain(deployment.version))

        updated = await self._deployments_storage.update_deployment(
            deployment_id,
            version_to_domain(deployment.version) if deployment.version else None,
            deployment.metadata,
        )
        return deployment_from_domain(updated)

    async def upsert_deployment(
        self,
        agent_id: str,
        version_id: str,
        deployment_id: str,
        author_name: str,
    ) -> Deployment | str:
        # First we fetch the version from the completions
        version, completion_id = await self._completions_storage.get_version_by_id(agent_id, version_id)
        # We are going to fetch and update
        # We could have race conditions here, but that would be a massive edge case so we should just throw
        # if someone else deploys a version with the same id in between the fetch and the update

        # First check if a deployment exist
        try:
            deployment = await self._deployments_storage.get_deployment(deployment_id)
        except ObjectNotFoundError:
            # Deployment does not exist so we can just create it
            inserted = DomainDeployment(
                id=deployment_id,
                agent_id=agent_id,
                version=version,
                created_by=author_name,
                created_at=datetime.now(UTC),
                metadata={},
            )
            await self._deployments_storage.create_deployment(inserted)
            return deployment_from_domain(inserted)

        # A deployment already exists
        # We won't update anything here since it would be too dangerous to update a deployment via MCP
        # Instead we check compatibility and either raise and return a confirm URL

        _check_input_schema_compatibility(deployment, version)
        _check_output_schema_compatibility(deployment, version)

        return f"An existing deployment already exists for this ID. Go to {ANOTHERAI_APP_URL}/deploy?deployment_id={deployment_id}&completion_id={completion_id}"

    async def archive_deployment(self, deployment_id: str):
        return await self._deployments_storage.archive_deployment(deployment_id)


def _check_output_schema_compatibility(deployment: DomainDeployment, version: Version):
    if version.output_schema is None:
        if deployment.version.output_schema is not None:
            raise BadRequestError(
                "The version you are trying to deploy has no output schema but the existing deployment does. "
                "Please create a new deployment.",
            )
        return
    if deployment.version.output_schema is None:
        raise BadRequestError(
            "The version you are trying to deploy has an output schema but the existing deployment does not. "
            "Please create a new deployment.",
        )

    try:
        JsonSchema(deployment.version.output_schema.json_schema).check_compatible(
            JsonSchema(version.output_schema.json_schema),
        )
    except IncompatibleSchemaError as e:
        raise BadRequestError(
            "The version you are trying to deploy has an output schema that is not compatible with the existing "
            f"deployment. Please create a new deployment.\n{e}",
        ) from None
    return


def _check_input_schema_compatibility(deployment: DomainDeployment, version: Version):
    if version.input_variables_schema is None:
        if deployment.version.input_variables_schema is not None:
            raise BadRequestError(
                "The version you are trying to deploy expects no input variables but the existing deployment does. "
                "Please create a new deployment.",
            )
        return
    if deployment.version.input_variables_schema is None:
        raise BadRequestError(
            "The version you are trying to deploy expects input variables but the existing deployment does not. "
            "Please create a new deployment.",
        )

    try:
        JsonSchema(deployment.version.input_variables_schema).check_compatible(
            JsonSchema(version.input_variables_schema),
        )
    except IncompatibleSchemaError as e:
        raise BadRequestError(
            "The version you are trying to deploy uses input variables that are not compatible with the ones used by "
            f"the existing deployment. Please create a new deployment.\n{e}",
        ) from None
    return

from structlog import get_logger

from core.storage.deployment_storage import DeploymentStorage
from protocol.api._api_models import Deployment, DeploymentCreate, DeploymentUpdate, Page
from protocol.api._services.conversions import deployment_from_domain, page_token_from_datetime, page_token_to_datetime

_log = get_logger(__name__)


class DeploymentService:
    def __init__(self, deployments_storage: DeploymentStorage):
        self.deployments_storage = deployments_storage

    async def get_deployment(self, deployment_id: str):
        deployment = await self.deployments_storage.get_deployment(deployment_id)
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
            async for d in self.deployments_storage.list_deployments(agent_id, created_before, include_archived, limit)
        ]

        try:
            total = await self.deployments_storage.count_deployments(agent_id, include_archived)
        except Exception as e:  # noqa: BLE001
            _log.warning("Failed to count deployments: %s", e)
            total = 0

        return Page(
            items=deployments,
            total=total,
            next_page_token=page_token_from_datetime(deployments[-1].created_at) if deployments else None,
        )

    async def create_deployment(self, deployment: DeploymentCreate) -> Deployment:
        raise NotImplementedError

    async def update_deployment(self, deployment_id: str, deployment: DeploymentUpdate) -> Deployment:
        raise NotImplementedError

    async def upsert_deployment(
        self,
        agent_id: str,
        version_id: str,
        deployment_id: str,
        author_name: str,
    ) -> Deployment | str:
        raise NotImplementedError

    async def archive_deployment(self, deployment_id: str) -> None:
        raise NotImplementedError

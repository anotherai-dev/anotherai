from collections.abc import AsyncIterable
from datetime import datetime
from typing import Any, Protocol

from core.domain.deployment import Deployment
from core.domain.version import Version


class DeploymentStorage(Protocol):
    async def create_deployment(self, deployment: Deployment): ...

    async def update_deployment(
        self,
        deployment_id: str,
        version: Version | None,
        metadata: dict[str, Any] | None,
    ) -> Deployment: ...

    async def archive_deployment(self, deployment_id: str): ...

    async def count_deployments(self, agent_id: str | None, include_archived: bool) -> int: ...

    def list_deployments(
        self,
        agent_id: str | None,
        created_before: datetime | None,
        include_archived: bool,
        limit: int,
    ) -> AsyncIterable[Deployment]: ...

    async def get_deployment(self, deployment_id: str) -> Deployment: ...

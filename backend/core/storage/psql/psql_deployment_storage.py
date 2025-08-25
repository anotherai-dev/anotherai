import json
from collections.abc import AsyncIterable
from datetime import datetime
from typing import Any, override

from asyncpg.pool import PoolConnectionProxy
from structlog import get_logger

from core.domain.deployment import Deployment
from core.domain.exceptions import ObjectNotFoundError
from core.domain.version import Version
from core.storage.deployment_storage import DeploymentStorage
from core.storage.psql._psql_base_storage import AgentLinkedRow, JSONDict, PsqlBaseStorage
from core.storage.psql._psql_utils import map_value, set_values
from core.utils.fields import datetime_zero

_log = get_logger(__name__)


class PsqlDeploymentStorage(PsqlBaseStorage, DeploymentStorage):
    @override
    @classmethod
    def table(cls) -> str:
        return "deployments"

    @override
    async def create_deployment(self, deployment: Deployment):
        async with self._connect() as connection:
            agent_uid = await self._agent_uid(connection, deployment.agent_id)
            row = _DeploymentRow.from_domain(agent_uid, deployment)
            await self._insert(connection, row, table=self.table())

    async def update_deployment(
        self,
        deployment_id: str,
        version: Version | None,
        metadata: dict[str, Any] | None,
    ) -> Deployment:
        values: list[tuple[str, Any]] = []
        if version:
            values.append(("version", version.model_dump_json(exclude_none=True)))
        if metadata:
            values.append(("metadata", json.dumps(metadata)))
        sets, set_args = set_values(values, start=2)
        async with self._connect() as connection:
            id = await connection.fetchrow(
                f"""
                UPDATE deployments
                SET {sets}
                WHERE slug = $1 AND deleted_at IS NULL
                RETURNING *
                """,  # noqa: S608 # we trust set_values function
                deployment_id,
                *set_args,
            )
            if not id:
                raise ObjectNotFoundError(f"Deployment {deployment_id} not found")
            return self._validate(_DeploymentRow, id).to_domain()

    async def archive_deployment(self, deployment_id: str):
        async with self._connect() as connection:
            id = await connection.fetchrow(
                """
                UPDATE deployments
                SET deleted_at = CURRENT_TIMESTAMP
                WHERE slug = $1 AND deleted_at IS NULL
                RETURNING uid
                """,
                deployment_id,
            )
            if not id:
                raise ObjectNotFoundError(f"Deployment {deployment_id} not found")

    def _where_deployments(
        self,
        conn: PoolConnectionProxy,
        arg_idx: int,
        agent_uid: int | None,
        include_archived: bool,
        created_before: datetime | None,
    ) -> tuple[str, list[Any]]:
        where: list[str] = []
        arguments: list[Any] = []
        if agent_uid is not None:
            where.append(f"agent_uid = ${len(arguments) + arg_idx}")
            arguments.append(agent_uid)
        if include_archived is False:
            where.append("deleted_at IS NULL")
        if created_before is not None:
            where.append(f"created_at < ${len(arguments) + arg_idx}")
            arguments.append(map_value(created_before))
        return " AND ".join(where), arguments

    async def count_deployments(self, agent_id: str | None, include_archived: bool) -> int:
        async with self._connect() as connection:
            agent_uid = await self._agent_uid(connection, agent_id) if agent_id else None
            where, arguments = self._where_deployments(connection, 1, agent_uid, include_archived, None)
            count = await connection.fetchval(
                f"""
                SELECT COUNT(*) FROM deployments WHERE {where}
                """,  # noqa: S608 # OK here since where is defined above
                *arguments,
            )
            return count or 0

    async def list_deployments(
        self,
        agent_id: str | None,
        created_before: datetime | None,
        include_archived: bool,
        limit: int,
    ) -> AsyncIterable[Deployment]:
        async with self._connect() as connection:
            agent_uid = await self._agent_uid(connection, agent_id) if agent_id else None
            where, arguments = self._where_deployments(connection, 1, agent_uid, include_archived, created_before)
            rows = await connection.fetch(
                f"""
                SELECT * FROM deployments WHERE {where}
                """,  # noqa: S608 # OK here since where is defined above
                *arguments,
            )
            for row in rows:
                yield self._validate(_DeploymentRow, row).to_domain()

    async def get_deployment(self, deployment_id: str) -> Deployment:
        async with self._connect() as connection:
            row = await connection.fetchrow(
                """
                SELECT * FROM deployments WHERE slug = $1
                """,
                deployment_id,
            )
            if not row:
                raise ObjectNotFoundError(f"Deployment {deployment_id} not found")
            return self._validate(_DeploymentRow, row).to_domain()


class _DeploymentRow(AgentLinkedRow):
    slug: str = ""
    author_name: str = ""
    version_id: str = ""
    version: JSONDict | None = None
    updated_at: datetime | None = None
    metadata: JSONDict | None = None

    def to_domain(self) -> Deployment:
        return Deployment(
            id=self.slug,
            agent_id=self.agent_slug or "",
            version=Version.model_validate(self.version) if self.version else Version(),
            created_by=self.author_name,
            created_at=self.created_at or datetime_zero(),
            updated_at=self.updated_at,
            metadata=self.metadata or None,
            archived_at=self.deleted_at,
        )

    @classmethod
    def from_domain(cls, agent_uid: int, deployment: Deployment):
        return cls(
            slug=deployment.id,
            agent_uid=agent_uid,
            agent_slug=deployment.agent_id,
            version_id=deployment.version.id,
            version=deployment.version.model_dump(exclude_none=True),
            author_name=deployment.created_by,
            created_at=deployment.created_at,
            updated_at=deployment.updated_at,
            metadata=deployment.metadata,
        )

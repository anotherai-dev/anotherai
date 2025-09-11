import os
from collections.abc import Callable
from typing import final, override

import asyncpg
from clickhouse_connect.driver import create_async_client  # pyright: ignore[reportUnknownVariableType]
from clickhouse_connect.driver.asyncclient import AsyncClient

from core.storage.agent_storage import AgentStorage
from core.storage.annotation_storage import AnnotationStorage
from core.storage.clickhouse.clickhouse_client import ClickhouseClient
from core.storage.clickhouse.migrations.migrate import migrate as migrate_clickhouse
from core.storage.completion_storage import CompletionStorage
from core.storage.deployment_storage import DeploymentStorage
from core.storage.experiment_storage import ExperimentStorage
from core.storage.file_storage import FileStorage
from core.storage.psql.migrations.migrate import migrate
from core.storage.psql.psql_agent_storage import PsqlAgentsStorage
from core.storage.psql.psql_annotation_storage import PsqlAnnotationStorage
from core.storage.psql.psql_deployment_storage import PsqlDeploymentStorage
from core.storage.psql.psql_experiment_storage import PsqlExperimentStorage
from core.storage.psql.psql_tenant_storage import PsqlTenantStorage
from core.storage.psql.psql_user_storage import PsqlUserStorage
from core.storage.psql.psql_view_storage import PsqlViewStorage
from core.storage.storage_builder import StorageBuilder
from core.storage.tenant_storage import TenantStorage
from core.storage.user_storage import UserStorage
from core.storage.view_storage import ViewStorage


@final
class DefaultStorageBuilder(StorageBuilder):
    def __init__(
        self,
        clickhouse_client: AsyncClient,
        psql_pool: asyncpg.Pool,
        file_storage_builder: Callable[[int], FileStorage],
    ):
        self._clickhouse_client = clickhouse_client
        self._psql_pool = psql_pool
        self._file_storage_builder = file_storage_builder

    @override
    def completions(self, tenant_uid: int) -> CompletionStorage:
        return ClickhouseClient(self._clickhouse_client, tenant_uid)

    @override
    def agents(self, tenant_uid: int) -> AgentStorage:
        return PsqlAgentsStorage(tenant_uid, self._psql_pool)

    @override
    def experiments(self, tenant_uid: int) -> ExperimentStorage:
        return PsqlExperimentStorage(tenant_uid, self._psql_pool)

    @override
    def files(self, tenant_uid: int) -> FileStorage:
        return self._file_storage_builder(tenant_uid)

    @override
    def annotations(self, tenant_uid: int) -> AnnotationStorage:
        return PsqlAnnotationStorage(tenant_uid, self._psql_pool)

    @override
    def views(self, tenant_uid: int) -> ViewStorage:
        return PsqlViewStorage(tenant_uid, self._psql_pool)

    @override
    def tenants(self, tenant_uid: int) -> TenantStorage:
        return PsqlTenantStorage(tenant_uid=tenant_uid, pool=self._psql_pool)

    @override
    def deployments(self, tenant_uid: int) -> DeploymentStorage:
        return PsqlDeploymentStorage(tenant_uid, self._psql_pool)

    @override
    def users(self, tenant_uid: int) -> UserStorage:
        return PsqlUserStorage(tenant_uid, self._psql_pool)

    @classmethod
    async def create(cls):
        psql_pool = await asyncpg.create_pool(dsn=os.environ["PSQL_DSN"])
        clickhouse_client = await create_async_client(dsn=os.environ["CLICKHOUSE_DSN"])

        return cls(
            clickhouse_client=clickhouse_client,
            psql_pool=psql_pool,
            file_storage_builder=_default_file_storage_builder(),
        )

    async def close(self):
        await self._psql_pool.close()
        await self._clickhouse_client.close()

    @override
    async def migrate(self):
        async with self._psql_pool.acquire() as conn:
            await migrate(conn)

        await migrate_clickhouse(self._clickhouse_client)


def _default_file_storage_builder() -> Callable[[int], FileStorage]:
    if azure_blob_dsn := os.environ.get("AZURE_BLOB_DSN"):
        from core.storage.azure.azure_blob_file_storage import AzureBlobFileStorage

        azure_container_name = os.environ.get("AZURE_BLOB_CONTAINER", "completions")
        return lambda tenant_uid: AzureBlobFileStorage(
            connection_string=azure_blob_dsn,
            container_name=azure_container_name,
            tenant_uid=tenant_uid,
        )

    dsn = os.environ.get("FILE_STORAGE_DSN")
    if not dsn:
        # TODO: noop ?
        raise ValueError("FILE_STORAGE_DSN is not set")

    if not dsn.startswith("s3://"):
        raise ValueError("Only S3 file storage is supported")

    from core.storage.s3.s3_file_storage import S3FileStorage

    return lambda tenant_uid: S3FileStorage(
        connection_string=dsn,
        tenant_uid=tenant_uid,
    )

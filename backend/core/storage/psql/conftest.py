import asyncpg
import pytest


@pytest.fixture
async def inserted_tenant(purged_psql: asyncpg.Pool) -> int:
    async with purged_psql.acquire() as conn:
        uid = await conn.fetchval("INSERT INTO tenants (slug) VALUES ('test') RETURNING uid")

    return uid


@pytest.fixture
async def purged_psql_tenant_conn(purged_psql: asyncpg.Pool, inserted_tenant: int):
    async with purged_psql.acquire() as conn:
        _ = await conn.execute(f"SET app.tenant_uid = {inserted_tenant}")
        yield conn


@pytest.fixture
def experiment_storage(inserted_tenant: int, purged_psql: asyncpg.Pool):
    from core.storage.psql.psql_experiment_storage import PsqlExperimentStorage

    return PsqlExperimentStorage(tenant_uid=inserted_tenant, pool=purged_psql)


@pytest.fixture
def agent_storage(inserted_tenant: int, purged_psql: asyncpg.Pool):
    from core.storage.psql.psql_agent_storage import PsqlAgentsStorage

    return PsqlAgentsStorage(tenant_uid=inserted_tenant, pool=purged_psql)


@pytest.fixture
def annotation_storage(inserted_tenant: int, purged_psql: asyncpg.Pool):
    from core.storage.psql.psql_annotation_storage import PsqlAnnotationStorage

    return PsqlAnnotationStorage(tenant_uid=inserted_tenant, pool=purged_psql)

import uuid

import asyncpg
import pytest

from core.domain.exceptions import ObjectNotFoundError
from core.storage.psql.psql_user_storage import PsqlUserStorage


@pytest.fixture
def user_storage(purged_psql: asyncpg.Pool) -> PsqlUserStorage:
    return PsqlUserStorage(tenant_uid=1, pool=purged_psql)


async def _insert_tenant(pool: asyncpg.Pool, owner_id: str | None = None, org_id: str | None = None) -> int:
    async with pool.acquire() as conn:
        org_uid = await conn.fetchval(
            "INSERT INTO tenants (slug, owner_id, org_id) VALUES ($1, $2, $3) RETURNING uid",
            uuid.uuid4().hex,
            owner_id,
            org_id,
        )
        assert org_uid
        return org_uid


class TestPsqlUserStorageSetLastUsedOrganization:
    async def _get_last_used_organization_uid(self, purged_psql: asyncpg.Pool, user_id: str) -> int:
        async with purged_psql.acquire() as conn:
            row = await conn.fetchrow("SELECT last_used_organization_uid FROM users WHERE user_id = $1", user_id)
            assert row
            return row["last_used_organization_uid"]

    async def test_insert_no_org(self, user_storage: PsqlUserStorage, purged_psql: asyncpg.Pool):
        org_uid = await _insert_tenant(purged_psql, owner_id="test-user")

        await user_storage.set_last_used_organization("test-user", None)
        assert await self._get_last_used_organization_uid(purged_psql, "test-user") == org_uid

    async def test_insert_org(self, user_storage: PsqlUserStorage, purged_psql: asyncpg.Pool):
        org_uid = await _insert_tenant(purged_psql, org_id="test-org")

        await user_storage.set_last_used_organization("test-user", "test-org")

        assert await self._get_last_used_organization_uid(purged_psql, "test-user") == org_uid

    async def test_update_org(self, user_storage: PsqlUserStorage, purged_psql: asyncpg.Pool):
        await _insert_tenant(purged_psql, org_id="org-a")
        org_uid_b = await _insert_tenant(purged_psql, org_id="org-b")

        await user_storage.set_last_used_organization("test-user", "org-a")
        await user_storage.set_last_used_organization("test-user", "org-b")

        assert await self._get_last_used_organization_uid(purged_psql, "test-user") == org_uid_b

    async def test_clear_org(self, user_storage: PsqlUserStorage, purged_psql: asyncpg.Pool):
        await _insert_tenant(purged_psql, org_id="org-clear")
        owner_uid = await _insert_tenant(purged_psql, owner_id="user-clear")

        await user_storage.set_last_used_organization("user-clear", "org-clear")
        await user_storage.set_last_used_organization("user-clear", None)

        assert await self._get_last_used_organization_uid(purged_psql, "user-clear") == owner_uid

    async def test_invalid_org_raises(self, user_storage: PsqlUserStorage):
        with pytest.raises(ObjectNotFoundError, match="tenant not found"):
            await user_storage.set_last_used_organization("user-invalid", "does-not-exist")


class TestPsqlUserStorageLastUsedOrganization:
    async def test_returns_personal_tenant(self, user_storage: PsqlUserStorage, purged_psql: asyncpg.Pool):
        # Insert personal tenant owned by the user
        inserted_uid = await _insert_tenant(purged_psql, owner_id="user-personal")

        # Set last used to personal (None means personal tenant by owner_id)
        await user_storage.set_last_used_organization("user-personal", None)

        # Fetch and validate
        tenant = await user_storage.last_used_organization("user-personal")
        assert tenant.uid == inserted_uid
        assert tenant.owner_id == "user-personal"
        assert tenant.org_id is None

    async def test_returns_org_tenant(self, user_storage: PsqlUserStorage, purged_psql: asyncpg.Pool):
        # Insert organization tenant
        inserted_uid = await _insert_tenant(purged_psql, org_id="org-xyz")

        # Set last used to that org
        await user_storage.set_last_used_organization("user-org", "org-xyz")

        # Fetch and validate
        tenant = await user_storage.last_used_organization("user-org")
        assert tenant.uid == inserted_uid
        assert tenant.org_id == "org-xyz"

    async def test_returns_latest_after_update(self, user_storage: PsqlUserStorage, purged_psql: asyncpg.Pool):
        # Insert two org tenants
        await _insert_tenant(purged_psql, org_id="org-a")
        org_b_uid = await _insert_tenant(purged_psql, org_id="org-b")

        # Set to org-a then update to org-b
        await user_storage.set_last_used_organization("user-update", "org-a")
        await user_storage.set_last_used_organization("user-update", "org-b")

        # Should return org-b
        tenant = await user_storage.last_used_organization("user-update")
        assert tenant.uid == org_b_uid
        assert tenant.org_id == "org-b"

    async def test_user_not_found(self, user_storage: PsqlUserStorage):
        with pytest.raises(ObjectNotFoundError, match="user not found"):
            await user_storage.last_used_organization("unknown-user")

# pyright: reportPrivateUsage=false
import asyncio
from datetime import UTC, datetime

import asyncpg
import pytest

from core.domain.api_key import APIKey, CompleteAPIKey
from core.domain.exceptions import DuplicateValueError, InternalError, ObjectNotFoundError
from core.domain.tenant_data import TenantData
from core.storage.psql.psql_tenant_storage import PsqlTenantStorage
from core.utils.hash import secure_hash


@pytest.fixture
def tenant_storage(purged_psql: asyncpg.Pool) -> PsqlTenantStorage:
    return PsqlTenantStorage(tenant_uid=1, pool=purged_psql)


async def _insert_tenant(
    pool: asyncpg.Pool,
    slug: str,
    owner_id: str | None = None,
    org_id: str | None = None,
    current_credits_usd: float = 0.0,
) -> TenantData:
    """Helper to insert a tenant directly into database."""
    async with pool.acquire() as conn:
        uid = await conn.fetchval(
            "INSERT INTO tenants (slug, owner_id, org_id, current_credits_usd) VALUES ($1, $2, $3, $4) RETURNING uid",
            slug,
            owner_id,
            org_id,
            current_credits_usd,
        )
    return TenantData(uid=uid, slug=slug, owner_id=owner_id, org_id=org_id, current_credits_usd=current_credits_usd)


@pytest.fixture
async def inserted_tenant(tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> TenantData:
    data = await _insert_tenant(purged_psql, "test-tenant", "owner123")
    tenant_storage._tenant_uid = data.uid
    return data


async def _insert_api_key(
    pool: asyncpg.Pool,
    tenant_uid: int,
    slug: str = "test-key-id",
    name: str = "Test Key",
    partial_key: str = "aai-test****",
    hashed_key: str | None = None,
    created_by: str = "test-user",
    last_used_at: datetime | None = None,
):
    """Helper to insert an API key directly into database."""
    if hashed_key is None:
        # Generate unique hashed key to avoid constraint violations
        import uuid

        hashed_key = f"hashed_test_key_{uuid.uuid4().hex[:8]}"

    async with pool.acquire() as conn:
        _ = await conn.fetchrow(
            """
            INSERT INTO api_keys (
                slug, tenant_uid, name, partial_key, hashed_key, created_by, last_used_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *
        """,
            slug,
            tenant_uid,
            name,
            partial_key,
            hashed_key,
            created_by,
            last_used_at,
        )


class TestTenantByOrgID:
    async def test_success(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        inserted_tenant = await _insert_tenant(purged_psql, "org-tenant", "owner123", "org456")
        tenant = await tenant_storage.tenant_by_org_id("org456")
        assert tenant.uid == inserted_tenant.uid
        assert tenant.slug == inserted_tenant.slug
        assert tenant.owner_id == inserted_tenant.owner_id
        assert tenant.org_id == "org456"

    async def test_not_found(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        with pytest.raises(ObjectNotFoundError, match="Tenant with org_id = \\$1 not found"):
            await tenant_storage.tenant_by_org_id("nonexistent-org")


class TestTenantByOwnerID:
    async def test_success(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        # Insert tenant with owner_id but no org_id (personal tenant)
        inserted_tenant = await _insert_tenant(purged_psql, "personal-tenant", "owner123")
        tenant = await tenant_storage.tenant_by_owner_id("owner123")
        assert tenant.uid == inserted_tenant.uid
        assert tenant.slug == inserted_tenant.slug
        assert tenant.owner_id == "owner123"
        assert tenant.org_id is None

    async def test_ignores_org_tenant(
        self,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        # Insert tenant with both owner_id and org_id (should be ignored)
        await _insert_tenant(purged_psql, "org-tenant", "owner123", "org456")
        # Insert personal tenant with same owner_id but no org_id
        inserted_personal = await _insert_tenant(purged_psql, "personal-tenant", "owner123")

        tenant = await tenant_storage.tenant_by_owner_id("owner123")
        assert tenant.uid == inserted_personal.uid
        assert tenant.org_id is None

    async def test_not_found(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        with pytest.raises(ObjectNotFoundError, match="Tenant with owner_id = \\$1 AND org_id is null not found"):
            await tenant_storage.tenant_by_owner_id("nonexistent-owner")


class TestTenantByAPIKey:
    async def test_success(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        # Insert tenant
        inserted_tenant = await _insert_tenant(purged_psql, "test-tenant", "owner123")

        # Insert API key
        api_key = "test-api-key"
        hashed_key = secure_hash(api_key)
        await _insert_api_key(purged_psql, inserted_tenant.uid, hashed_key=hashed_key)

        # Test retrieval
        tenant = await tenant_storage.tenant_by_api_key(api_key)
        assert tenant.uid == inserted_tenant.uid
        assert tenant.slug == inserted_tenant.slug
        assert tenant.owner_id == inserted_tenant.owner_id

    async def test_not_found_no_api_key(
        self,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        with pytest.raises(ObjectNotFoundError, match="Tenant with API key nonexistent-key not found"):
            await tenant_storage.tenant_by_api_key("nonexistent-key")

    async def test_not_found_wrong_key(
        self,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        # Insert tenant and API key
        inserted_tenant = await _insert_tenant(purged_psql, "test-tenant", "owner123")
        await _insert_api_key(purged_psql, inserted_tenant.uid, hashed_key=secure_hash("correct-key"))

        # Try with wrong key
        with pytest.raises(ObjectNotFoundError, match="Tenant with API key wrong-key not found"):
            await tenant_storage.tenant_by_api_key("wrong-key")


class TestCreateTenant:
    async def test_success(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        tenant_data = TenantData(slug="new-tenant", owner_id="owner123")
        created_tenant = await tenant_storage.create_tenant(tenant_data)

        assert created_tenant.uid > 0
        assert created_tenant.slug == "new-tenant"
        assert created_tenant.owner_id == "owner123"
        assert created_tenant.org_id is None

    async def test_success_with_org_id(
        self,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        tenant_data = TenantData(slug="org-tenant", owner_id="owner123", org_id="org456")
        created_tenant = await tenant_storage.create_tenant(tenant_data)

        assert created_tenant.uid > 0
        assert created_tenant.slug == "org-tenant"
        assert created_tenant.owner_id == "owner123"
        assert created_tenant.org_id == "org456"

    async def test_duplicate(self, tenant_storage: PsqlTenantStorage):
        tenant_data = TenantData(slug="org-tenant", owner_id="owner123", org_id="org456")
        gathered = await asyncio.gather(
            tenant_storage.create_tenant(tenant_data),
            tenant_storage.create_tenant(tenant_data),
            tenant_storage.create_tenant(tenant_data),
            return_exceptions=True,
        )

        not_exceptions = [result for result in gathered if not isinstance(result, Exception)]
        exceptions = [result for result in gathered if isinstance(result, Exception)]
        assert len(not_exceptions) == 1
        assert len(exceptions) == 2
        assert isinstance(exceptions[0], DuplicateValueError)
        assert isinstance(exceptions[1], DuplicateValueError)


class TestCreateTenantForOwnerID:
    async def test_success(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        created_tenant = await tenant_storage.create_tenant_for_owner_id("owner123")

        assert created_tenant.uid > 0
        assert created_tenant.slug == "owner123"  # Slugified owner_id
        assert created_tenant.owner_id == "owner123"
        assert created_tenant.org_id is None

    async def test_duplicate(self, tenant_storage: PsqlTenantStorage):
        gathered = await asyncio.gather(
            tenant_storage.create_tenant_for_owner_id("owner123"),
            tenant_storage.create_tenant_for_owner_id("owner123"),
            return_exceptions=True,
        )

        first = gathered[0]
        assert isinstance(first, TenantData)
        assert first.slug == "owner123"
        assert first.owner_id == "owner123"
        assert first.org_id is None
        assert all(res == first for res in gathered[1:])


class TestCreateTenantForOrgID:
    async def test_create_new_tenant(
        self,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        """Test creating new tenant when no existing personal tenant."""
        created_tenant = await tenant_storage.create_tenant_for_org_id("org456", "custom-slug", "owner123")

        assert created_tenant.uid > 0
        assert created_tenant.slug == "custom-slug"
        assert created_tenant.owner_id == "owner123"
        assert created_tenant.org_id == "org456"

    async def test_migrate_existing_personal_tenant(
        self,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        """Test migrating existing personal tenant to organization."""
        # First create a personal tenant
        personal_tenant = await _insert_tenant(purged_psql, "personal-slug", "owner123")

        # Now migrate to organization
        migrated_tenant = await tenant_storage.create_tenant_for_org_id("org456", "new-slug", "owner123")

        # Should be same uid but updated fields
        assert migrated_tenant.uid == personal_tenant.uid
        assert migrated_tenant.slug == "new-slug"  # Should use the provided org_slug
        assert migrated_tenant.owner_id == "owner123"
        assert migrated_tenant.org_id == "org456"

    async def test_migrate_duplicate(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool):
        personal_tenant = await _insert_tenant(purged_psql, "personal-slug", "owner123")

        # migrating tenant twice
        gathered = await asyncio.gather(
            tenant_storage.create_tenant_for_org_id("org456", "new-slug", "owner123"),
            tenant_storage.create_tenant_for_org_id("org456", "new-slug", "owner123"),
            return_exceptions=True,
        )
        first = gathered[0]
        assert isinstance(first, TenantData)
        assert first.uid == personal_tenant.uid
        assert first.slug == "new-slug"
        assert first.owner_id == "owner123"
        assert first.org_id == "org456"
        assert all(res == first for res in gathered[1:])

    async def test_default_slug_generation(
        self,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        """Test that slug is generated from org_id when not provided."""
        created_tenant = await tenant_storage.create_tenant_for_org_id("My-Org-123", None, "owner123")

        assert created_tenant.slug == "my-org-123"  # Slugified org_id
        assert created_tenant.org_id == "My-Org-123"

    async def test_duplicate(self, tenant_storage: PsqlTenantStorage):
        gathered = await asyncio.gather(
            tenant_storage.create_tenant_for_org_id("org456", None, "owner123"),
            tenant_storage.create_tenant_for_org_id("org456", None, "owner123"),
            return_exceptions=True,
        )

        first = gathered[0]
        assert isinstance(first, TenantData)
        assert first.slug == "org456"
        assert first.owner_id == "owner123"
        assert first.org_id == "org456"
        assert all(res == first for res in gathered[1:])


class TestUpdateTenantSlug:
    async def test_success(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        # Insert tenant
        inserted_tenant = await _insert_tenant(purged_psql, "old-slug", "owner123")

        # Update slug
        tenant_data = TenantData(uid=inserted_tenant.uid, slug="new-slug", owner_id="owner123")
        updated_tenant = await tenant_storage.update_tenant_slug(tenant_data)

        assert updated_tenant.uid == inserted_tenant.uid
        assert updated_tenant.slug == "new-slug"
        assert updated_tenant.owner_id == "owner123"

    async def test_not_found(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        tenant_data = TenantData(uid=999, slug="new-slug", owner_id="owner123")

        with pytest.raises(ObjectNotFoundError, match="Tenant with uid 999 not found"):
            await tenant_storage.update_tenant_slug(tenant_data)


class TestCreateAPIKey:
    async def test_success(self, inserted_tenant: TenantData, tenant_storage: PsqlTenantStorage) -> None:
        api_key = await tenant_storage.create_api_key("Test Key", "creator123")

        assert isinstance(api_key, CompleteAPIKey)
        assert api_key.name == "Test Key"
        assert api_key.created_by == "creator123"
        assert api_key.api_key.startswith("aai-")
        assert api_key.partial_key.endswith("****")
        assert len(api_key.partial_key) == 13  # "aai-" + 5 chars + "****"
        assert api_key.id  # Should have an ID

    async def test_no_tenant_uid(
        self,
        inserted_tenant: TenantData,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        tenant_storage._tenant_uid = -1
        with pytest.raises(InternalError, match="Tenant UID is required to create an API key"):
            await tenant_storage.create_api_key("Test Key", "creator123")


class TestDeleteAPIKey:
    async def test_success(
        self,
        inserted_tenant: TenantData,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        # Insert API key
        key_id = "test-key-id"
        await _insert_api_key(purged_psql, inserted_tenant.uid, slug=key_id)

        # Delete key - should not raise
        await tenant_storage.delete_api_key(key_id)

        # Verify deleted
        async with purged_psql.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM api_keys WHERE slug = $1", key_id)
            assert row is None

    async def test_nonexistent_key(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        # Should not raise even if key doesn't exist
        await tenant_storage.delete_api_key("nonexistent-key")


class TestUpdateAPIKeyLastUsedAt:
    async def test_success(
        self,
        inserted_tenant: TenantData,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        # Insert API key
        key_id = "test-key-id"
        await _insert_api_key(purged_psql, inserted_tenant.uid, slug=key_id)

        # Update last used
        now = datetime.now(tz=UTC)
        await tenant_storage.update_api_key_last_used_at(key_id, now)

        # Verify updated
        async with purged_psql.acquire() as conn:
            row = await conn.fetchrow("SELECT last_used_at FROM api_keys WHERE slug = $1", key_id)
            assert row is not None
            assert row["last_used_at"] is not None

    async def test_nonexistent_key(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        # Should not raise even if key doesn't exist
        now = datetime.now(tz=UTC)
        await tenant_storage.update_api_key_last_used_at("nonexistent-key", now)


class TestListAPIKeys:
    async def test_empty_list(self, inserted_tenant: TenantData, tenant_storage: PsqlTenantStorage) -> None:
        # No API keys inserted

        keys = await tenant_storage.list_api_keys()
        assert keys == []

    async def test_single_key(
        self,
        inserted_tenant: TenantData,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        # Insert API key
        await _insert_api_key(purged_psql, inserted_tenant.uid, name="Test Key", created_by="creator123")

        keys = await tenant_storage.list_api_keys()
        assert len(keys) == 1

        key = keys[0]
        assert isinstance(key, APIKey)
        assert key.name == "Test Key"
        assert key.created_by == "creator123"
        assert key.partial_key == "aai-test****"

    async def test_multiple_keys(
        self,
        inserted_tenant: TenantData,
        tenant_storage: PsqlTenantStorage,
        purged_psql: asyncpg.Pool,
    ) -> None:
        # Insert multiple API keys
        await _insert_api_key(purged_psql, inserted_tenant.uid, slug="key1", name="Key 1")
        await _insert_api_key(purged_psql, inserted_tenant.uid, slug="key2", name="Key 2")

        keys = await tenant_storage.list_api_keys()
        assert len(keys) == 2

        key_names = {key.name for key in keys}
        assert key_names == {"Key 1", "Key 2"}

    async def test_filters_by_tenant(self, purged_psql: asyncpg.Pool) -> None:
        # Insert two tenants
        tenant1 = await _insert_tenant(purged_psql, "tenant1", "owner1")
        tenant2 = await _insert_tenant(purged_psql, "tenant2", "owner2")

        # Insert keys for both tenants
        await _insert_api_key(purged_psql, tenant1.uid, slug="key1", name="Tenant 1 Key")
        await _insert_api_key(purged_psql, tenant2.uid, slug="key2", name="Tenant 2 Key")

        # Create storage for tenant1 specifically
        tenant1_storage = PsqlTenantStorage(tenant_uid=tenant1.uid, pool=purged_psql)
        keys = await tenant1_storage.list_api_keys()
        assert len(keys) == 1
        assert keys[0].name == "Tenant 1 Key"


class TestDecrementCredits:
    async def test_success(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        # Insert tenant with initial credits
        tenant_data = await _insert_tenant(purged_psql, "test-tenant", "owner123", current_credits_usd=100.0)
        tenant_storage._tenant_uid = tenant_data.uid

        result = await tenant_storage.decrement_credits(25.0)

        # Verify returned data

        assert result.uid == tenant_data.uid
        assert result.current_credits_usd == 75.0
        assert result.slug == tenant_data.slug
        assert result.owner_id == tenant_data.owner_id

        # Verify database was updated
        async with purged_psql.acquire() as conn:
            row = await conn.fetchrow("SELECT current_credits_usd FROM tenants WHERE uid = $1", tenant_data.uid)
            assert row is not None
            assert row["current_credits_usd"] == 75.0

    async def test_decrement_to_zero(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        # Insert tenant with exact amount to decrement
        initial_credits = 50.0
        tenant_data = await _insert_tenant(purged_psql, "test-tenant", "owner123", current_credits_usd=initial_credits)
        tenant_storage._tenant_uid = tenant_data.uid

        # Decrement all credits
        result = await tenant_storage.decrement_credits(initial_credits)

        # Should result in zero credits
        assert result.current_credits_usd == 0.0

        # Verify in database
        async with purged_psql.acquire() as conn:
            row = await conn.fetchrow("SELECT current_credits_usd FROM tenants WHERE uid = $1", tenant_data.uid)
            assert row is not None
            assert row["current_credits_usd"] == 0.0

    async def test_decrement_zero(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        # Insert tenant with credits
        initial_credits = 50.0
        tenant_data = await _insert_tenant(purged_psql, "test-tenant", "owner123", current_credits_usd=initial_credits)
        tenant_storage._tenant_uid = tenant_data.uid

        # Decrement zero credits
        result = await tenant_storage.decrement_credits(0.0)

        # Credits should remain unchanged
        assert result.current_credits_usd == initial_credits

        # Verify in database
        async with purged_psql.acquire() as conn:
            row = await conn.fetchrow("SELECT current_credits_usd FROM tenants WHERE uid = $1", tenant_data.uid)
            assert row is not None
            assert row["current_credits_usd"] == initial_credits

    async def test_tenant_not_found(self, tenant_storage: PsqlTenantStorage, purged_psql: asyncpg.Pool) -> None:
        # Set tenant_storage to use non-existent tenant UID
        tenant_storage._tenant_uid = 99999

        # Should raise ObjectNotFoundError
        with pytest.raises(ObjectNotFoundError, match="Tenant with uid 99999 not found"):
            await tenant_storage.decrement_credits(10.0)

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, override

import asyncpg
from asyncpg import UniqueViolationError
from pydantic import BaseModel, Field

from core.domain.api_key import APIKey, CompleteAPIKey
from core.domain.exceptions import DuplicateValueError, InternalError, ObjectNotFoundError
from core.domain.tenant_data import TenantData
from core.storage.psql._psql_base_storage import JSONList, PsqlBaseStorage
from core.storage.tenant_storage import AutomaticPayment, TenantStorage
from core.utils.fields import datetime_zero
from core.utils.hash import secure_hash
from core.utils.strings import slugify

# Note: the api_keys and tenants tables are not protected by RLS
# That's because some operations on these tables need to be done without
# specifying a tenant_uid
# So the tenant_uid needs to be manually specified when needed


class PsqlTenantStorage(PsqlBaseStorage, TenantStorage):
    @override
    @classmethod
    def table(cls) -> str:
        return "tenants"

    @classmethod
    def validate_row(cls, row: asyncpg.Record) -> TenantData:
        return cls._validate(_TenantRow, row).to_domain()

    async def _tenant_where(self, where: str, *args: Any) -> TenantData:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                f"""
                SELECT * FROM tenants
                WHERE {where}
                """,  # noqa: S608, where is defined below
                *args,
            )
            if not row:
                raise ObjectNotFoundError(f"Tenant with {where} not found")
            return self.validate_row(row)

    @override
    async def tenant_by_uid(self, tenant_uid: int) -> TenantData:
        return await self._tenant_where("uid = $1", tenant_uid)

    @override
    async def tenant_by_org_id(self, org_id: str) -> TenantData:
        return await self._tenant_where("org_id = $1", org_id)

    @override
    async def tenant_by_owner_id(self, owner_id: str) -> TenantData:
        return await self._tenant_where("owner_id = $1 AND org_id is null", owner_id)

    @override
    async def tenant_by_api_key(self, api_key: str) -> TenantData:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT tenants.* FROM tenants LEFT JOIN api_keys ON tenants.uid = api_keys.tenant_uid
                WHERE api_keys.hashed_key = $1
                """,
                secure_hash(api_key),
            )
            if not row:
                raise ObjectNotFoundError(f"Tenant with API key {api_key} not found")
            return self._validate(_TenantRow, row).to_domain()

    @override
    async def create_tenant(self, tenant: TenantData) -> TenantData:
        async with self._pool.acquire() as connection:
            with self._wrap_errors():
                row = await connection.fetchrow(
                    """
                    INSERT INTO tenants (slug, owner_id, org_id) VALUES ($1, $2, $3) RETURNING *
                    """,
                    tenant.slug,
                    tenant.owner_id,
                    tenant.org_id,
                )
            if not row:
                raise InternalError("Failed to create tenant")
            return self._validate(_TenantRow, row).to_domain()

    @override
    async def create_tenant_for_owner_id(self, owner_id: str) -> TenantData:
        tenant = TenantData(owner_id=owner_id, slug=slugify(owner_id))
        try:
            return await self.create_tenant(tenant)
        except DuplicateValueError:
            return await self.tenant_by_owner_id(owner_id)

    @override
    async def create_tenant_for_org_id(self, org_id: str, org_slug: str | None, owner_id: str) -> TenantData:
        # First we try to update a row that has no org_id but has an owner_id
        # basically migrating the owner id tenant to an organization
        if not org_slug:
            org_slug = slugify(org_id)
        async with self._pool.acquire() as connection:
            try:
                row = await connection.fetchrow(
                    """
                    UPDATE tenants SET org_id = $1, slug = $2 WHERE owner_id = $3 AND org_id is null RETURNING *
                    """,
                    org_id,
                    org_slug,
                    owner_id,
                )
            except UniqueViolationError:
                return await self.tenant_by_owner_id(org_id)
            if row:
                # Tenant data was found so we can just return
                return self._validate(_TenantRow, row).to_domain()

            # Otherwise we just create a new tenant
            tenant = TenantData(owner_id=owner_id, org_id=org_id, slug=org_slug)
            try:
                return await self.create_tenant(tenant)
            except DuplicateValueError:
                return await self.tenant_by_org_id(org_id)

    @override
    async def update_tenant_slug(self, slug: str) -> TenantData:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                UPDATE tenants SET slug = $1 WHERE uid = $2 RETURNING *
                """,
                slug,
                self._tenant_uid,
            )
            if not row:
                raise self._tenant_not_found_error()
            return self._validate(_TenantRow, row).to_domain()

    @override
    async def create_api_key(self, name: str, created_by: str) -> CompleteAPIKey:
        if self._tenant_uid <= 0:
            raise InternalError("Tenant UID is required to create an API key")

        api_key = f"aai-{secrets.token_urlsafe(32)}"
        hashed_key = secure_hash(api_key)
        partial_key = f"{api_key[:9]}****"

        insert_row = _APIKeyRow(
            slug=str(uuid.uuid4()),
            tenant_uid=self._tenant_uid,
            name=name,
            created_by=created_by,
            partial_key=partial_key,
            hashed_key=hashed_key,
        )

        async with self._pool.acquire() as connection:
            row = await self._insert(connection, insert_row, "api_keys")
            if not row:
                raise InternalError("Failed to create API key")

        return CompleteAPIKey(
            id=insert_row.slug,
            name=insert_row.name,
            partial_key=insert_row.partial_key,
            created_at=datetime.now(tz=UTC),
            last_used_at=insert_row.last_used_at,
            created_by=insert_row.created_by,
            api_key=api_key,
        )

    @override
    async def delete_api_key(self, api_key_id: str) -> None:
        async with self._pool.acquire() as connection:
            await connection.execute(
                """
                DELETE FROM api_keys WHERE slug = $1 AND tenant_uid = $2
                """,
                api_key_id,
                self._tenant_uid,
            )

    @override
    async def update_api_key_last_used_at(self, api_key_id: str, last_used_at: datetime) -> None:
        async with self._pool.acquire() as connection:
            await connection.execute(
                """
                UPDATE api_keys SET last_used_at = $1 WHERE slug = $2 AND tenant_uid = $3
                """,
                self._map_value(last_used_at),
                api_key_id,
                self._tenant_uid,
            )

    @override
    async def list_api_keys(self) -> list[APIKey]:
        async with self._pool.acquire() as connection:
            rows = await connection.fetch(
                """
                SELECT * FROM api_keys WHERE tenant_uid = $1
                """,
                self._tenant_uid,
            )
            return [self._validate(_APIKeyRow, row).to_domain() for row in rows]

    @override
    async def current_tenant(self) -> TenantData:
        return await self.tenant_by_uid(self._tenant_uid)

    @override
    async def decrement_credits(self, credits: float):
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                UPDATE tenants SET current_credits_usd = current_credits_usd - $1 WHERE uid = $2 RETURNING *
                """,
                credits,
                self._tenant_uid,
            )
            if not row:
                raise ObjectNotFoundError(f"Tenant with uid {self._tenant_uid} not found")
            return self._validate(_TenantRow, row).to_domain()

    @override
    async def set_customer_id(self, customer_id: str) -> TenantData:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                UPDATE tenants SET stripe_customer_id = $1 WHERE uid = $2 RETURNING *
                """,
                customer_id,
                self._tenant_uid,
            )
            if not row:
                raise ObjectNotFoundError(f"Tenant with uid {self._tenant_uid} not found")
            return self._validate(_TenantRow, row).to_domain()

    @override
    async def clear_payment_failure(self):
        async with self._pool.acquire() as connection:
            uid = await connection.fetchval(
                """
                UPDATE tenants SET
                    payment_failure_date = NULL,
                    payment_failure_code = NULL,
                    payment_failure_reason = NULL
                WHERE uid = $1
                RETURNING uid
                """,
                self._tenant_uid,
            )
            if not uid:
                raise self._tenant_not_found_error()

    def _tenant_not_found_error(self) -> ObjectNotFoundError:
        return ObjectNotFoundError(object_type="tenant", msg=f"Tenant with uid {self._tenant_uid} not found")

    @override
    async def update_automatic_payment(self, automatic_payment: AutomaticPayment | None) -> None:
        async with self._pool.acquire() as connection:
            if automatic_payment is None:
                uid = await connection.fetchval(
                    """
                    UPDATE tenants SET
                        automatic_payment_enabled = FALSE,
                        automatic_payment_threshold = NULL,
                        automatic_payment_balance_to_maintain = NULL
                    WHERE uid = $1
                    RETURNING uid
                    """,
                    self._tenant_uid,
                )
            else:
                uid = await connection.fetchval(
                    """
                    UPDATE tenants SET
                        automatic_payment_enabled = TRUE,
                        automatic_payment_threshold = $1,
                        automatic_payment_balance_to_maintain = $2
                    WHERE uid = $3
                    RETURNING uid
                    """,
                    automatic_payment.threshold,
                    automatic_payment.balance_to_maintain,
                    self._tenant_uid,
                )
            if not uid:
                raise self._tenant_not_found_error()

    @override
    async def add_credits(self, credits: float) -> TenantData:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                UPDATE tenants SET current_credits_usd = current_credits_usd + $1 WHERE uid = $2 RETURNING *
                """,
                credits,
                self._tenant_uid,
            )
            if not row:
                raise self._tenant_not_found_error()
            return self._validate(_TenantRow, row).to_domain()

    @override
    async def unlock_payment_for_success(self, amount: float) -> None:
        async with self._pool.acquire() as connection:
            uid = await connection.fetchval(
                """
                UPDATE tenants SET
                    locked_for_payment = FALSE,
                    current_credits_usd = current_credits_usd + $1
                WHERE uid = $2
                RETURNING uid
                """,
                amount,
                self._tenant_uid,
            )
            if not uid:
                raise self._tenant_not_found_error()

    @override
    async def unlock_payment_for_failure(
        self,
        now: datetime,
        code: Literal["internal", "payment_failed"],
        failure_reason: str,
    ):
        async with self._pool.acquire() as connection:
            uid = await connection.fetchval(
                """
                UPDATE tenants SET
                    locked_for_payment = FALSE,
                    payment_failure_date = $1,
                    payment_failure_code = $2,
                    payment_failure_reason = $3
                WHERE uid = $4
                RETURNING uid
                """,
                self._map_value(now),
                code,
                failure_reason,
                self._tenant_uid,
            )
            if not uid:
                raise self._tenant_not_found_error()

    @override
    async def check_unlocked_payment_failure(self) -> TenantData.PaymentFailure | None:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                """
                SELECT locked_for_payment, payment_failure_date, payment_failure_code, payment_failure_reason
                FROM tenants
                WHERE uid = $1
                """,
                self._tenant_uid,
            )
            if not row:
                raise self._tenant_not_found_error()

            # If locked, raise error
            if row["locked_for_payment"]:
                raise InternalError("Organization is locked for payment")

            # If no failure, return None
            if not row["payment_failure_date"]:
                return None

            # Return payment failure
            return TenantData.PaymentFailure(
                failure_date=row["payment_failure_date"],
                failure_code=row["payment_failure_code"],
                failure_reason=row["payment_failure_reason"],
            )


class _TenantRow(BaseModel):
    uid: int = 0
    slug: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    owner_id: str | None = None
    org_id: str | None = None

    # Custom provider configs
    providers: JSONList = Field(default_factory=list)
    # Payment
    stripe_customer_id: str | None = None
    current_credits_usd: float = 0.0
    locked_for_payment: bool = False
    automatic_payment_enabled: bool = False
    automatic_payment_threshold: float | None = None
    automatic_payment_balance_to_maintain: float | None = None
    payment_failure_date: datetime | None = None
    payment_failure_code: str | None = None
    payment_failure_reason: str | None = None
    low_credits_email_sent_by_threshold: JSONList | None = None

    def to_domain(self) -> TenantData:
        # TODO: other fields
        return TenantData(
            uid=self.uid,
            slug=self.slug,
            org_id=self.org_id,
            owner_id=self.owner_id,
            current_credits_usd=self.current_credits_usd,
        )


class _APIKeyRow(BaseModel):
    uid: int = 0
    slug: str = ""
    tenant_uid: int = 0
    created_at: datetime | None = None
    name: str = ""
    created_by: str = ""
    partial_key: str = ""
    hashed_key: str = ""
    last_used_at: datetime | None = None

    def to_domain(self) -> APIKey:
        return APIKey(
            id=self.slug,
            name=self.name,
            partial_key=self.partial_key,
            created_at=self.created_at or datetime_zero(),
            last_used_at=self.last_used_at,
            created_by=self.created_by,
        )

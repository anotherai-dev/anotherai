from typing import override

from pydantic import BaseModel

from core.domain.exceptions import ObjectNotFoundError
from core.domain.tenant_data import TenantData
from core.storage.psql._psql_base_storage import PsqlBaseStorage
from core.storage.psql.psql_tenant_storage import PsqlTenantStorage
from core.storage.user_storage import UserStorage


class PsqlUserStorage(PsqlBaseStorage, UserStorage):
    @override
    @classmethod
    def table(cls) -> str:
        return "users"

    @override
    async def last_used_organization(self, user_id: str) -> TenantData:
        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT tenants.* FROM users LEFT JOIN tenants ON users.last_used_organization_uid = tenants.uid WHERE users.user_id = $1",
                user_id,
            )
            if not row:
                raise ObjectNotFoundError(object_type="user")
            return PsqlTenantStorage.validate_row(row)

    @override
    async def set_last_used_organization(self, user_id: str, organization_id: str | None) -> None:
        async with self._pool.acquire() as connection:
            where_query = "org_id = $1" if organization_id else "org_id IS NULL and owner_id = $1"

            uid: int | None = await connection.fetchval(
                # Ok here, where_query is defined above
                f"SELECT uid FROM tenants WHERE {where_query}",  # noqa: S608
                organization_id or user_id,
            )
            if not uid:
                raise ObjectNotFoundError(object_type="tenant", capture=True)

            await connection.execute(
                "INSERT INTO users (user_id, last_used_organization_uid) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET last_used_organization_uid = $2",
                user_id,
                uid,
            )


class _UserRow(BaseModel):
    uid: int | None = None
    user_id: str = ""
    last_used_organization_uid: int | None = None

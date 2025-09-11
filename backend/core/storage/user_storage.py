from typing import Protocol

from core.domain.tenant_data import TenantData


class UserStorage(Protocol):
    async def last_used_organization(self, user_id: str) -> TenantData: ...
    async def set_last_used_organization(self, user_id: str, organization_id: str | None) -> None: ...

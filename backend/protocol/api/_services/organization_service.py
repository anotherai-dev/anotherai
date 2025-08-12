from core.storage.tenant_storage import TenantStorage
from protocol.api._api_models import APIKey, CompleteAPIKey, CreateAPIKeyRequest, Page
from protocol.api._services.conversions import api_key_from_domain, api_key_from_domain_complete


class OrganizationService:
    def __init__(self, tenant_storage: TenantStorage):
        self._tenant_storage = tenant_storage

    async def list_api_keys(self) -> Page[APIKey]:
        api_keys = await self._tenant_storage.list_api_keys()
        return Page(
            items=[api_key_from_domain(api_key) for api_key in api_keys],
            total=len(api_keys),
        )

    async def create_api_key(self, request: CreateAPIKeyRequest) -> CompleteAPIKey:
        api_key = await self._tenant_storage.create_api_key(request.name, request.created_by)
        return api_key_from_domain_complete(api_key)

    async def delete_api_key(self, id: str) -> None:
        await self._tenant_storage.delete_api_key(id)

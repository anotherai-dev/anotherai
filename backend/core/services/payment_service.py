from core.storage.tenant_storage import TenantStorage


class PaymentService:
    def __init__(self, tenant_storage: TenantStorage):
        self._tenant_storage = tenant_storage

    async def decrement_credits(self, credits: float) -> None:
        await self._tenant_storage.decrement_credits(credits=credits)

from typing import Protocol

import structlog

from core.domain.tenant_data import TenantData
from core.storage.tenant_storage import TenantStorage

_log = structlog.get_logger(__name__)


class PaymentHandler(Protocol):
    async def handle_credit_decrement(self, tenant: TenantData) -> None: ...


# TODO: the split between payment service and stripe service is stupid
# We should extract all the common logic to the payment service and reduce the stripe service to
# What is stripe specific
class PaymentService:
    def __init__(
        self,
        tenant_storage: TenantStorage,
        payment_handler: PaymentHandler,
    ):
        self._tenant_storage = tenant_storage
        self._payment_handler = payment_handler

    async def decrement_credits(self, credits: float) -> None:
        new_data = await self._tenant_storage.decrement_credits(credits=credits)
        if self._payment_handler:
            await self._payment_handler.handle_credit_decrement(new_data)

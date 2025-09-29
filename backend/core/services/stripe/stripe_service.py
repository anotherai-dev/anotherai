import os

import stripe
from pydantic import BaseModel, field_serializer, field_validator

from core.services.payment_service import PaymentService
from core.storage.tenant_storage import TenantStorage
from core.utils.background import add_background_task


class _CustomerMetadata(BaseModel):
    tenant: str
    tenant_uid: int = 0
    organization_id: str | None = None
    owner_id: str | None = None

    @field_serializer("tenant_uid")
    def serialize_tenant_uid(self, tenant_uid: int) -> str:
        return str(tenant_uid)

    @field_validator("tenant_uid")
    def validate_tenant_uid(cls, v: int | str) -> int:
        if isinstance(v, str):
            return int(v)
        return v


stripe.api_key = os.environ.get("STRIPE_API_KEY")


class StripeService:
    def __init__(self, tenant_storage: TenantStorage, payment_service: PaymentService):
        self._tenant_storage = tenant_storage
        self._payment_service = payment_service

    async def _create_customer(self, user_email: str) -> str:
        org_settings = await self._tenant_storage.current_tenant()
        if org_settings.customer_id is not None:
            return org_settings.customer_id

        metadata = _CustomerMetadata(
            organization_id=org_settings.org_id or None,
            tenant=org_settings.slug,
            tenant_uid=org_settings.uid,
            owner_id=org_settings.owner_id or None,
        )

        # TODO: protect against race conditions here, we could be creating multiple customers
        customer = await stripe.Customer.create_async(
            name=org_settings.slug,
            email=user_email,
            metadata=metadata.model_dump(exclude_none=True),
        )

        await self._tenant_storage.set_customer_id(customer_id=customer.id)
        return customer.id

    async def add_payment_method(
        self,
        customer_id: str | None,
        payment_method_id: str,
        user_email: str,
    ) -> str:
        if customer_id is None:
            customer_id = await self._create_customer(user_email)

        payment_method = await stripe.PaymentMethod.attach_async(
            payment_method_id,
            customer=customer_id,
        )

        # Set as default payment method
        await stripe.Customer.modify_async(
            customer_id,
            invoice_settings={"default_payment_method": payment_method.id},
        )

        # Clear a payment failure if any
        await self._tenant_storage.clear_payment_failure()
        # Decrement 0 credits to trigger a payment if needed
        add_background_task(self._payment_service.decrement_credits(0))
        return payment_method.id

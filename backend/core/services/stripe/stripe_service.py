import math
import os
from typing import Literal, NamedTuple

import stripe
from pydantic import BaseModel, field_serializer, field_validator
from structlog import get_logger

from core.domain.exceptions import BadRequestError, InternalError
from core.domain.tenant_data import TenantData
from core.services.payment_service import PaymentService
from core.storage.tenant_storage import TenantStorage
from core.utils.background import add_background_task

_log = get_logger(__name__)


class PaymentMethodResponse(BaseModel):
    payment_method_id: str
    last4: str
    brand: str
    exp_month: int
    exp_year: int


class MissingPaymentMethodError(BadRequestError):
    pass


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

    async def delete_payment_method(self, data: TenantData) -> None:
        customer_id = _customer_id_or_raise(data)

        payment_method = await _get_payment_method(customer_id)
        if not payment_method:
            raise MissingPaymentMethodError(
                "Organization has no default payment method",
                capture=True,
                tenant_data=data,
            )

        await stripe.PaymentMethod.detach_async(payment_method.payment_method_id)

        await stripe.Customer.modify_async(
            customer_id,
            invoice_settings={"default_payment_method": ""},
        )

        # Opt-out from automatic payments
        await self._tenant_storage.update_automatic_payment(None)

    @classmethod
    async def create_payment_intent(
        cls,
        tenant_data: TenantData,
        amount: float,
        trigger: Literal["automatic", "manual"],
    ) -> "PaymentIntent":
        stripe_customer_id = _customer_id_or_raise(tenant_data)

        customer = await stripe.Customer.retrieve_async(
            stripe_customer_id,
            expand=["invoice_settings.default_payment_method"],
        )
        if customer.invoice_settings is None or customer.invoice_settings.default_payment_method is None:
            # This can happen if the client creates a payment intent before
            # Setting a default payment method.
            raise MissingPaymentMethodError(
                "Organization has no default payment method",
                capture=True,
                tenant_data=tenant_data,
            )

        metadata = _IntentMetadata(
            organization_id=tenant_data.org_id or None,
            tenant=tenant_data.slug,
            tenant_uid=tenant_data.uid,
            owner_id=tenant_data.owner_id or None,
            trigger=trigger,
        )
        if isinstance(customer.invoice_settings.default_payment_method, str):
            raise InternalError("Default payment method is not a payment method")

        payment_intent = await stripe.PaymentIntent.create_async(
            amount=math.ceil(amount * 100),
            currency="usd",
            customer=stripe_customer_id,
            payment_method=customer.invoice_settings.default_payment_method.id,
            setup_future_usage="off_session",
            # For automatic payment processing, we need to disable redirects to avoid getting stuck in a redirect path.
            # This does not affect manual payment processing.
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            metadata=metadata.model_dump(exclude_none=True),
        )

        # Client secret is not a great name but from the stripe doc it's
        # meant to be used by the client in combination with a publishable key.
        if not payment_intent.client_secret:
            raise ValueError("Payment intent has no client secret")

        return PaymentIntent(
            client_secret=payment_intent.client_secret,
            payment_intent_id=payment_intent.id,
        )


def _customer_id_or_raise(data: TenantData, capture: bool = True) -> str:
    if data.customer_id is None:
        raise BadRequestError(
            "Organization has no Stripe customer ID",
            capture=capture,
            tenant_data=data,
        )
    return data.customer_id


async def _get_payment_method(customer_id: str) -> PaymentMethodResponse | None:
    customer = await stripe.Customer.retrieve_async(
        customer_id,
        expand=["invoice_settings.default_payment_method"],
    )
    if customer.invoice_settings is None:
        return None

    if not customer.invoice_settings.default_payment_method:
        return None

    pm = customer.invoice_settings.default_payment_method
    if isinstance(pm, str):
        raise InternalError("Default payment method is not a payment method")
    if not pm.card:
        raise InternalError("Default payment method is not a card")
    return PaymentMethodResponse(
        payment_method_id=pm.id,
        last4=pm.card.last4,
        brand=pm.card.brand,
        exp_month=pm.card.exp_month,
        exp_year=pm.card.exp_year,
    )


class PaymentIntent(NamedTuple):
    client_secret: str
    payment_intent_id: str


class _CustomerMetadata(BaseModel):
    tenant: str
    tenant_uid: int = 0
    organization_id: str | None = None
    owner_id: str | None = None

    @field_serializer("tenant_uid")
    def serialize_tenant_uid(self, tenant_uid: int) -> str:
        return str(tenant_uid)

    @classmethod
    @field_validator("tenant_uid")
    def validate_tenant_uid(cls, v: int | str) -> int:
        if isinstance(v, str):
            return int(v)
        return v


class _IntentMetadata(_CustomerMetadata):
    trigger: Literal["automatic", "manual"] = "manual"

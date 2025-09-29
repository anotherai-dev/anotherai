from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from core.domain.exceptions import BadRequestError
from core.services.stripe.stripe_service import StripeService
from protocol._common.documentation import INCLUDE_PRIVATE_ROUTES
from protocol.api._dependencies._lifecycle import LifecycleDependenciesDep
from protocol.api._dependencies._services import PaymentServiceDep
from protocol.api._dependencies._tenant import TenantDep

router = APIRouter(prefix="/v1/payments", include_in_schema=INCLUDE_PRIVATE_ROUTES)


class PaymentMethodRequest(BaseModel):
    payment_method_id: str
    payment_method_currency: str = "USD"


class PaymentMethodIdResponse(BaseModel):
    payment_method_id: str


def _stripe_service(
    dependencies: LifecycleDependenciesDep,
    tenant: TenantDep,
    payment_service: PaymentServiceDep,
) -> StripeService:
    return StripeService(
        tenant_storage=dependencies.storage_builder.tenants(tenant.uid),
        payment_service=payment_service,
    )


type _StripeServiceDep = Annotated[StripeService, Depends(_stripe_service)]


@router.post("/payment-methods", description="Add a payment method to the organization")
async def add_payment_method(
    stripe_service: _StripeServiceDep,
    tenant: TenantDep,
    request: PaymentMethodRequest,
) -> PaymentMethodIdResponse:
    if not tenant.user or not tenant.user.email:
        raise BadRequestError("A user email is required")
    payment_method_id = await stripe_service.add_payment_method(
        tenant.customer_id,
        request.payment_method_id,
        tenant.user.email,
    )
    return PaymentMethodIdResponse(
        payment_method_id=payment_method_id,
    )


@router.delete("/payment-methods", description="Delete the payment method attached to the organization")
async def delete_payment_method(
    stripe_service: _StripeServiceDep,
    tenant: TenantDep,
) -> None:
    await stripe_service.delete_payment_method(tenant)


class CreatePaymentIntentRequest(BaseModel):
    amount: float


class PaymentIntentCreatedResponse(BaseModel):
    client_secret: str = Field(
        description="The stripe client secret for the payment intent, "
        "that can be used by the client to retrieve the payment using the client secret and a publishable key.",
    )
    payment_intent_id: str


@router.post("/payment-intents", description="Create a manual payment intent in Stripe for the organization")
async def create_payment_intent(
    request: CreatePaymentIntentRequest,
    tenant: TenantDep,
) -> PaymentIntentCreatedResponse:
    payment_intent = await StripeService.create_payment_intent(tenant, request.amount, trigger="manual")
    if not payment_intent.client_secret:
        raise ValueError("Payment intent creation failed")
    return PaymentIntentCreatedResponse(
        client_secret=payment_intent.client_secret,
        payment_intent_id=payment_intent.payment_intent_id,
    )

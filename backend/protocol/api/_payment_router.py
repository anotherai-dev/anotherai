from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.domain.exceptions import BadRequestError
from core.services.stripe.stripe_service import StripeService
from core.utils.background import add_background_task
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
    payment_service: PaymentServiceDep,
) -> PaymentMethodIdResponse:
    if not tenant.user or not tenant.user.email:
        raise BadRequestError("A user email is required")
    payment_method_id = await stripe_service.add_payment_method(
        tenant.customer_id,
        request.payment_method_id,
        tenant.user.email,
    )
    # Triggering an automatic payment only if under the threshold
    add_background_task(payment_service.decrement_credits(0))
    return PaymentMethodIdResponse(
        payment_method_id=payment_method_id,
    )

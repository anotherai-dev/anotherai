import math
import os
from collections.abc import Awaitable, Callable
from curses import ALL_MOUSE_EVENTS
from typing import Any, Literal, NamedTuple, Self

import stripe
from fastapi import Request
from pydantic import BaseModel, ValidationError, field_serializer, field_validator
from structlog import get_logger

from core.domain.events import EventRouter, PaymentUpdatedEvent
from core.domain.exceptions import (
    BadRequestError,
    InternalError,
    MissingPaymentMethodError,
    ObjectNotFoundError,
    PaymentRequiredError,
)
from core.domain.tenant_data import TenantData
from core.services.email_service import EmailService
from core.storage.tenant_storage import AutomaticPayment, TenantStorage
from core.utils.background import add_background_task
from core.utils.fields import datetime_factory

_log = get_logger(__name__)


class PaymentMethodResponse(BaseModel):
    payment_method_id: str
    last4: str
    brand: str
    exp_month: int
    exp_year: int


stripe.api_key = os.environ.get("STRIPE_API_KEY")


# TODO: a lot of logic should be moved to the payment service
class StripeService:
    def __init__(self, tenant_storage: TenantStorage, email_service: EmailService, event_router: EventRouter):
        self._tenant_storage = tenant_storage
        self._event_router = event_router
        self._email_service = email_service

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
        self._event_router(PaymentUpdatedEvent())
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

    @classmethod
    async def get_payment_method(cls, org_settings: TenantData) -> PaymentMethodResponse | None:
        if not org_settings.customer_id:
            return None

        return await _get_payment_method(org_settings.customer_id)

    async def configure_automatic_payment(
        self,
        org_settings: TenantData,
        opt_in: bool,
        threshold: float | None,
        balance_to_maintain: float | None,
    ):
        # This will throw an error if the customer does not exist
        stripe_customer_id = _customer_id_or_raise(org_settings, capture=False)

        default_payment_method = await _get_payment_method(stripe_customer_id)
        if not default_payment_method:
            raise MissingPaymentMethodError(
                "Organization has no default payment method",
                capture=True,  # Capturing, that would mean a bug in the frontend
            )

        if opt_in:
            if threshold is None or balance_to_maintain is None:
                raise ValueError("Threshold and balance_to_maintain are required when opt_in is true")

            if threshold > balance_to_maintain:
                raise ValueError("Threshold must be greater than balance_to_maintain")

            automatic_payment = AutomaticPayment(threshold, balance_to_maintain)
        else:
            if threshold is not None or balance_to_maintain is not None:
                raise ValueError("Threshold and balance_to_maintain must be None when opt_in is false")
            automatic_payment = None

        await self._tenant_storage.update_automatic_payment(automatic_payment)
        if opt_in:
            self._event_router(PaymentUpdatedEvent())

    async def _handle_payment_success(self, metadata: dict[str, str], amount: float):
        try:
            parsed_metadata = _IntentMetadata.model_validate(metadata)
            if parsed_metadata.trigger == "automatic":
                await self._tenant_storage.unlock_payment_for_success(amount)
                return
            # Otherwise we just need to add the credits
            await self._tenant_storage.add_credits(amount)
        except Exception as e:
            # Wrap everything in an InternalError to make sure it's easy to spot
            raise InternalError(
                "Urgent: Failed to process adding credits",
                extra={"metadata": metadata, "amount": amount},
            ) from e

    async def _handle_payment_requires_action(self, metadata: dict[str, str]):
        parsed_metadata = _IntentMetadata.model_validate(metadata)
        if parsed_metadata.trigger == "automatic":
            _log.error("Automatic payment requires action", metadata=metadata)

    async def _unlock_payment_for_failure(
        self,
        code: Literal["internal", "payment_failed"],
        failure_reason: str,
    ):
        await self._tenant_storage.unlock_payment_for_failure(
            now=datetime_factory(),
            code=code,
            failure_reason=failure_reason,
        )

        add_background_task(self._email_service.send_payment_failure_email())

    async def handle_payment_failure(self, metadata: dict[str, str], failure_reason: str):
        parsed_metadata = _IntentMetadata.model_validate(metadata)
        if parsed_metadata.trigger == "automatic":
            try:
                await self._unlock_payment_for_failure(
                    code="payment_failed",
                    failure_reason=failure_reason,
                )

            except ObjectNotFoundError as e:
                # That can happen if the payment was declined when confirming the intent
                # In which case we already unlocked the payment error
                # To make sure, let's just see that we have a payment error
                failure = await self._tenant_storage.check_unlocked_payment_failure()
                if not failure:
                    # If we don't have a failure, it means there is something else weird going on so we should raise
                    raise InternalError(
                        "Automatic payment failed but we don't have a payment failure",
                        extra={"metadata": metadata},
                    ) from e

    async def _send_low_credits_email_if_needed(self, tenant: TenantData):
        # For now only a single email at $5
        threshold = 5

        if not tenant.should_send_low_credits_email(threshold_usd=threshold):
            return

        try:
            await self._tenant_storage.add_low_credits_email_sent(threshold)
        except ObjectNotFoundError:
            # The email was already sent so we can just ignore
            return

        try:
            await self._email_service.send_low_credits_email()
        except Exception:  # noqa: BLE001
            _log.exception("Failed to send low credits email", tenant=tenant)

    async def handle_credit_decrement(self, tenant: TenantData):
        if tenant.should_trigger_automatic_payment(min_amount=0):
            await self.trigger_automatic_payment_if_needed(min_amount=2)

        add_background_task(self._send_low_credits_email_if_needed(tenant))

    @classmethod
    async def stripe_webhook(
        cls,
        service_builder: Callable[[int], Awaitable[Self]],
        request: Request,
        stripe_signature: str | None,
    ):
        _log.debug("Received Stripe webhook", request=request, stripe_signature=stripe_signature)
        event = await _verify_stripe_signature(request, stripe_signature)

        metadata = event.data.object.get("metadata", {})
        if not metadata:
            _log.error("Payment intent has no metadata", event_obj=event.data.object)
            return
        try:
            metadata = _BaseMetadata.model_validate(metadata)
        except ValidationError as e:
            _log.error("Payment intent has invalid metadata", event_obj=event.data.object, exc_info=e)
            return

        if _skip_webhook(metadata):
            _log.info("Skipping Stripe webhook", event_obj=event.data.object)
            return

        payment_service = await service_builder(metadata.tenant_uid)

        match event.type:
            case "payment_intent.created":
                # Nothing to do here
                pass
            case "payment_intent.succeeded":
                payment_intent = _PaymentIntentData.model_validate(event.data.object)
                await payment_service._handle_payment_success(payment_intent.metadata, payment_intent.amount / 100)  # noqa: SLF001
            case "payment_intent.requires_action":
                # Not sure what to do here, it should not happen for automatic payments
                payment_intent = _PaymentIntentData.model_validate(event.data.object)
                await payment_service._handle_payment_requires_action(payment_intent.metadata)  # noqa: SLF001
            case "payment_intent.payment_failed":
                payment_intent = _PaymentIntentData.model_validate(event.data.object)
                failure_reason = payment_intent.error_message
                if not failure_reason:
                    _log.error("Payment failed with an unknown error", event_obj=event.data.object)
                    failure_reason = "Payment failed with an unknown error"
                await payment_service.handle_payment_failure(payment_intent.metadata, failure_reason)
            case _:
                _log.warning("Unhandled Stripe event", event_obj=event.data.object)

    async def _trigger_automatic_payment(self, org_settings: TenantData, amount: float):
        """Create and confirm a payment intent on Stripe.
        This function expects that the org has already been locked for payment.
        It does not add credits or unlock the organization for intents since
        we need to wait for the webhook."""

        payment_intent = await self.create_payment_intent(org_settings, ALL_MOUSE_EVENTS, trigger="automatic")

        default_payment_method = await self.get_payment_method(org_settings)
        if default_payment_method is None:
            raise MissingPaymentMethodError(
                "Organization has no default payment method",
                tenant_data=org_settings,
            )

        # We need to confirm the payment so that it does not
        # remain in requires_confirmation state
        # From https://docs.stripe.com/payments/paymentintents/lifecycle it looks like
        # We may not need to do this in 2 steps (create + confirm) but ok for now
        res = await stripe.PaymentIntent.confirm_async(
            payment_intent.payment_intent_id,
            payment_method=default_payment_method.payment_method_id,
        )
        if not res.status == "succeeded":
            raise InternalError(
                "Confirming payment intent failed",
                extra={"confirm_response": res},
            )

    async def _start_automatic_payment_for_locked_org(self, tenant: TenantData, min_amount: float):
        """Create and confirm a payment intent on Stripe.
        This function expects that the org has already been locked for payment.
        It does not add credits or unlock the organization for intents since
        we need to wait for the webhook."""

        charge_amount = tenant.autocharge_amount(min_amount)
        if not charge_amount:
            # This should never happen
            raise InternalError(
                "Charge amount is None. Discarding Automatic payment",
                extra={"tenant": tenant.uid},
            )

        _log.info(
            "Organization has less than threshold credits so automatic payment processing is starting",
            tenant=tenant,
        )
        await self._trigger_automatic_payment(tenant, charge_amount)

    async def trigger_automatic_payment_if_needed(
        self,
        min_amount: float,
    ):
        """Trigger an automatic payment
        If `min_amount` is provided, a payment will be triggered no matter what the current balance is.

        Returns true if the payment was triggered successfully"""
        tenant = await self._tenant_storage.attempt_lock_for_payment()

        if not tenant:
            # There is already a payment being processed so there is no need to retry
            _log.debug("Failed to lock for payment")
            return False

        # TODO: check for org autopay status

        try:
            await self._start_automatic_payment_for_locked_org(tenant, min_amount=min_amount)
        except MissingPaymentMethodError:
            # Capture for now, this should not happen
            _log.error("Automatic payment failed due to missing payment method", tenant=tenant)
            # The customer has no default payment method so we can't process the payment
            await self._unlock_payment_for_failure(
                code="payment_failed",
                failure_reason="The account does not have a default payment method",
            )
        except stripe.CardError as e:
            await self._unlock_payment_for_failure(
                code="payment_failed",
                failure_reason=e.user_message or f"Payment failed with an unknown error. Code: {e.code or 'unknown'}",
            )
        except Exception:  # noqa: BLE001
            await self._unlock_payment_for_failure(
                code="internal",
                failure_reason="The payment process could not be initiated. This could be due to an internal error on "
                "our side or Stripe's. Your runs will not be locked for now until the issue is resolved.",
            )
            # TODO: send slack message, this is important as the error could be on our side
            # For now, since we don't really know what could cause the failure, we should fix manually
            # by updating the db or triggering a retry on the customer account.
            _log.exception("Automatic payment failed due to an internal error", tenant=tenant)
            return False

        return True

    async def raise_for_negative_credits(self):
        raise PaymentRequiredError(
            "Your credits are depleted. Please add more credits to continue using AnotherAI.",
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


class _BaseMetadata(BaseModel):
    app: str | None = "anotherai"
    tenant: str
    tenant_uid: int
    webhook_ignore: str | None = None

    @field_serializer("tenant_uid")
    def serialize_tenant_uid(self, tenant_uid: int) -> str:
        return str(tenant_uid)

    @classmethod
    @field_validator("tenant_uid")
    def validate_tenant_uid(cls, v: int | str) -> int:
        if isinstance(v, str):
            return int(v)
        return v


class _CustomerMetadata(_BaseMetadata):
    organization_id: str | None = None
    owner_id: str | None = None


class _IntentMetadata(_CustomerMetadata):
    trigger: Literal["automatic", "manual"] = "manual"


def _skip_webhook(metadata: _BaseMetadata) -> bool:
    if metadata.webhook_ignore == "true":
        return True

    return metadata.app != "anotherai"


async def _verify_stripe_signature(
    request: Request,
    stripe_signature: str | None,
) -> stripe.Event:
    if not stripe_signature:
        raise BadRequestError(
            "No signature header",
            capture=True,
        )

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if not webhook_secret:
        raise InternalError(
            "Webhook secret not configured",
            capture=True,
        )

    body = await request.body()
    stripe_event: stripe.Event = stripe.Webhook.construct_event(
        payload=body,
        sig_header=str(stripe_signature),
        secret=str(webhook_secret),
    )
    _log.debug("Raw Stripe Event", stripe_event=stripe_event)
    return stripe_event


class _PaymentIntentData(BaseModel):
    object: Literal["payment_intent"]
    id: str
    amount: int
    metadata: dict[str, Any]
    status: str

    class LastPaymentError(BaseModel):
        message: str | None

    last_payment_error: LastPaymentError | None = None

    @property
    def error_message(self) -> str | None:
        return self.last_payment_error.message if self.last_payment_error else None

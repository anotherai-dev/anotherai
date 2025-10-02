# pyright: reportPrivateUsage=false

from collections.abc import Awaitable, Callable
from typing import Any
from unittest import mock
from unittest.mock import AsyncMock, Mock, patch

import pytest
import stripe

from core.domain.exceptions import BadRequestError
from core.domain.tenant_data import TenantData
from core.services.email_service import EmailService
from core.services.stripe.stripe_service import StripeService, _BaseMetadata, _skip_webhook, _verify_stripe_signature
from core.utils.background import wait_for_background_tasks
from tests.fake_models import fake_tenant


@pytest.fixture
def mock_email_service():
    return Mock(spec=EmailService)


@pytest.fixture
def stripe_service(mock_tenant_storage: Mock, mock_event_router: Mock, mock_email_service: Mock):
    return StripeService(
        tenant_storage=mock_tenant_storage,
        event_router=mock_event_router,
        email_service=mock_email_service,
    )


@pytest.fixture
def mock_stripe():
    with patch("core.services.stripe.stripe_service.stripe") as mock:
        mock.PaymentIntent = AsyncMock(spec=stripe.PaymentIntent)
        mock.Customer = AsyncMock(spec=stripe.Customer)
        mock.PaymentMethod = AsyncMock(spec=stripe.PaymentMethod)
        mock.PaymentMethod.detach_async = AsyncMock(spec=stripe.PaymentMethod.detach_async)
        mock.Webhook = AsyncMock(spec=stripe.Webhook)
        mock.CardError = stripe.CardError

        yield mock


def _mock_customer(payment_method: bool):
    # It would be better to build customer objects but the inits are weird
    customer = Mock()
    customer.id = "cus_123"
    customer.invoice_settings = Mock()
    if payment_method:
        customer.invoice_settings.default_payment_method = _mock_payment_method()
    else:
        customer.invoice_settings.default_payment_method = None
    return customer


def _payment_intent():
    payment_intent = AsyncMock()
    payment_intent.client_secret = "secret_123"  # noqa: S105
    payment_intent.id = "pi_123"
    return payment_intent


def _mock_payment_method():
    payment_method = AsyncMock()
    payment_method.id = "pm_123"
    payment_method.card = Mock()
    payment_method.card.last4 = "4242"
    payment_method.card.brand = "visa"
    payment_method.card.exp_month = 12
    payment_method.card.exp_year = 2025
    return payment_method


class TestCreateCustomer:
    async def test_create_new_customer(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: AsyncMock,
        mock_stripe: Mock,
    ):
        # Mock stripe.Customer.create
        mock_customer = Mock()
        mock_customer.id = "cus_123"
        mock_tenant_storage.current_tenant.return_value = TenantData(
            slug="test-tenant",
            owner_id="test-owner",
            customer_id=None,
            uid=1,
        )
        mock_stripe.Customer.create_async.return_value = _mock_customer(payment_method=False)

        customer_id = await stripe_service._create_customer("test@example.com")

        assert customer_id == "cus_123"
        mock_stripe.Customer.create_async.assert_called_once_with(
            name="test-tenant",
            email="test@example.com",
            metadata={
                "app": "anotherai",
                "tenant": "test-tenant",
                "owner_id": "test-owner",
                "tenant_uid": "1",
            },
        )
        mock_tenant_storage.set_customer_id.assert_called_once_with(customer_id="cus_123")

    async def test_return_existing_customer(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: AsyncMock,
    ):
        # Set existing customer ID
        mock_tenant_storage.current_tenant.return_value.customer_id = "existing_cus_123"

        customer_id = await stripe_service._create_customer("test@example.com")

        assert customer_id == "existing_cus_123"
        mock_tenant_storage.set_customer_id.assert_not_called()


class TestAddPaymentMethod:
    async def test_existing_customer(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: AsyncMock,
        mock_stripe: Mock,
        mock_event_router: Mock,
    ):
        # Not sure whybut mock_stripe.PaymentMethod.attach_async is not working
        mock_stripe.PaymentMethod.attach_async = AsyncMock(return_value=_mock_payment_method())
        mock_stripe.Customer.modify_async.return_value = _mock_customer(payment_method=True)

        payment_method_id = await stripe_service.add_payment_method(
            "bla",
            "pm_123",
            "test@example.com",
        )

        assert payment_method_id == "pm_123"
        mock_stripe.PaymentMethod.attach_async.assert_called_once_with(
            "pm_123",
            customer="bla",
        )
        mock_stripe.Customer.modify_async.assert_called_once_with(
            "bla",
            invoice_settings={"default_payment_method": "pm_123"},
        )
        mock_tenant_storage.clear_payment_failure.assert_called_once()
        await wait_for_background_tasks()
        mock_event_router.assert_called_once()

    async def test_add_payment_method_no_customer(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: AsyncMock,
        mock_stripe: Mock,
    ):
        """Check that a customer is created if one does not exist"""
        mock_tenant_storage.current_tenant.return_value = TenantData(
            slug="test-tenant",
            owner_id="test-owner",
            customer_id=None,
            uid=1,
        )
        mock_stripe.Customer.create_async.return_value = _mock_customer(payment_method=False)
        mock_stripe.PaymentMethod.attach_async = AsyncMock(return_value=_mock_payment_method())

        await stripe_service.add_payment_method(
            None,
            "pm_123",
            "test@example.com",
        )
        mock_stripe.PaymentMethod.attach_async.assert_called_once()
        mock_stripe.Customer.modify_async.assert_called_once()

    async def test_add_payment_method_invalid_card(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: AsyncMock,
        mock_stripe: Mock,
    ):
        mock_payment_method = Mock()
        mock_payment_method.id = "pm_123"
        mock_attach = AsyncMock(
            side_effect=stripe.CardError(
                message="Your card's security code is incorrect.",
                code="incorrect_cvc",
                param="cvc",
            ),
        )
        mock_stripe.PaymentMethod.attach_async.side_effect = mock_attach

        with pytest.raises(stripe.CardError, match="security code is incorrect"):
            await stripe_service.add_payment_method(
                "bla",
                "pm_123",
                "test@example.com",
            )


class TestDeletePaymentMethod:
    async def test_delete_payment_method(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: AsyncMock,
        mock_stripe: Mock,
    ):
        customer = _mock_customer(payment_method=True)
        mock_stripe.Customer.retrieve_async.return_value = customer

        data = fake_tenant(customer_id="cus_123")

        await stripe_service.delete_payment_method(data)

        mock_tenant_storage.update_automatic_payment.assert_called_once_with(None)
        mock_stripe.PaymentMethod.detach_async.assert_called_once_with("pm_123")


class TestCreatePaymentIntent:
    async def test_create_payment_intent(
        self,
        mock_stripe: Mock,
    ):
        # Create a fake payment method
        customer = _mock_customer(payment_method=True)
        mock_stripe.Customer.retrieve_async.return_value = customer
        mock_stripe.PaymentIntent.create_async.return_value = _payment_intent()
        data = fake_tenant(customer_id="cus_123")

        payment_intent = await StripeService.create_payment_intent(
            data,
            100.0,
            trigger="manual",
        )

        assert payment_intent.client_secret == "secret_123"  # noqa: S105
        assert payment_intent.payment_intent_id == "pi_123"

        mock_stripe.PaymentIntent.create_async.assert_called_once_with(
            amount=10000,  # $100.00 in cents
            currency="usd",
            customer="cus_123",
            payment_method="pm_123",
            setup_future_usage="off_session",
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            metadata={
                "app": "anotherai",
                "tenant": "test-tenant",
                "tenant_uid": "1",
                "organization_id": "test-org",
                "owner_id": "test-owner",
                "trigger": "manual",
            },
        )

    async def test_create_payment_intent_no_payment_method(
        self,
        mock_stripe: Mock,
    ):
        tenant = fake_tenant(customer_id="cus_123")

        customer = _mock_customer(payment_method=False)
        mock_stripe.Customer.retrieve_async.return_value = customer

        with pytest.raises(BadRequestError, match="Organization has no default payment method"):
            await StripeService.create_payment_intent(
                tenant,
                100.0,
                trigger="manual",
            )


def _mock_event(obj: dict[str, Any]):
    return stripe.Event.construct_from(
        {
            "id": "evt_123",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "object": "payment_intent",
                    "id": "pi_123",
                    "amount": 1000,
                    "metadata": {"tenant": "test-tenant", "tenant_uid": "1", "app": "anotherai"},
                    "status": "succeeded",
                    **obj,
                },
            },
        },
        key="evt_123",
    )


class TestSkipWebhook:
    @pytest.mark.parametrize(
        ("metadata", "expected"),
        [
            pytest.param({}, False, id="default"),
            pytest.param({"webhook_ignore": "true"}, True, id="webhook_ignore"),
            pytest.param({"app": "workflowai"}, True, id="another app"),
        ],
    )
    async def test_skip_webhook(self, metadata: dict[str, Any], expected: bool):
        assert (
            _skip_webhook(_BaseMetadata.model_validate({**metadata, "tenant": "test-tenant", "tenant_uid": "1"}))
            == expected
        )


@pytest.fixture(autouse=True)
def mock_stripe_webhook_secret():
    with patch.dict("os.environ", {"STRIPE_WEBHOOK_SECRET": "whsec_test_secret"}):
        yield


def _mock_request(body: bytes = b"test_body"):
    req = Mock()
    req.body = AsyncMock(return_value=body)
    return req


class TestVerifyStripeSignature:
    async def test_success(self, mock_stripe: Mock):
        mock_event = _mock_event({})

        mock_stripe.Webhook.construct_event.return_value = mock_event

        mock_request = _mock_request()

        event = await _verify_stripe_signature(
            request=mock_request,
            stripe_signature="test_signature",
        )

        assert event["type"] == "payment_intent.succeeded"
        assert event["data"]["object"]["id"] == "pi_123"
        mock_stripe.Webhook.construct_event.assert_called_once_with(
            payload=b"test_body",
            sig_header="test_signature",
            secret="whsec_test_secret",  # noqa: S106
        )

    async def test_missing_signature(self):
        with pytest.raises(BadRequestError) as exc:
            await _verify_stripe_signature(
                request=Mock(),
                stripe_signature=None,
            )
        assert exc.value.status_code == 400
        assert exc.value.capture is True
        assert exc.value.args[0] == "No signature header"

    async def test_invalid_signature(self, mock_stripe: Mock):
        mock_stripe.Webhook.construct_event.side_effect = stripe.StripeError("Invalid", "sig")

        with pytest.raises(stripe.StripeError):
            await _verify_stripe_signature(
                request=Mock(body=AsyncMock(return_value="test_body")),
                stripe_signature="invalid_signature",
            )


class TestStripeWebhook:
    @pytest.fixture
    def builder(self, stripe_service: StripeService):
        async def _builder(_: int):
            return stripe_service

        return _builder

    async def test_payment_intent_succeeded(
        self,
        builder: Callable[[int], Awaitable[StripeService]],
        mock_stripe: Mock,
        mock_tenant_storage: Mock,
    ):
        mock_event = _mock_event({})
        mock_stripe.Webhook.construct_event.return_value = mock_event
        mock_request = _mock_request()

        await StripeService.stripe_webhook(
            builder,
            mock_request,
            "test_signature",
        )
        mock_tenant_storage.add_credits.assert_called_once_with(
            10.0,
        )

    async def test_payment_intent_no_tenant(
        self,
        builder: Callable[[int], Awaitable[StripeService]],
        mock_stripe: Mock,
        mock_tenant_storage: Mock,
    ):
        mock_event = _mock_event(
            {
                "metadata": {"app": "anotherai"},
            },
        )

        mock_stripe.Webhook.construct_event.return_value = mock_event
        mock_request = _mock_request()

        await StripeService.stripe_webhook(
            builder,
            mock_request,
            "test_signature",
        )

        mock_tenant_storage.add_credits.assert_not_called()

    async def test_ignored(
        self,
        builder: Callable[[int], Awaitable[StripeService]],
        mock_stripe: Mock,
        mock_tenant_storage: Mock,
    ):
        mock_event = _mock_event(
            {
                "metadata": {"webhook_ignore": "true", "app": "anotherai"},
            },
        )

        mock_stripe.Webhook.construct_event.return_value = mock_event
        mock_request = _mock_request()

        await StripeService.stripe_webhook(
            builder,
            mock_request,
            "test_signature",
        )

        mock_tenant_storage.add_credits.assert_not_called()


class TestHandleCreditDecrement:
    @pytest.fixture
    def test_org(self, mock_tenant_storage: AsyncMock):
        """Patch the org returned by decrement_credits"""
        org = TenantData(
            slug="test-tenant",
            owner_id="test-owner",
            org_id="test-org",
            current_credits_usd=4.0,  # Below threshold
            customer_id="cus_123",
            automatic_payment_enabled=True,
            automatic_payment_threshold=5.0,
            automatic_payment_balance_to_maintain=10.0,
        )

        mock_tenant_storage.decrement_credits.return_value = org
        return org

    async def test_decrement_credits_no_automatic_payment(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: Mock,
        test_org: TenantData,
    ):
        """Test when automatic payment is disabled"""
        test_org.automatic_payment_enabled = False

        await stripe_service.handle_credit_decrement(test_org)

        # No attempt to lock since credits are above threshold
        mock_tenant_storage.attempt_lock_for_payment.assert_not_called()

    async def test_decrement_credits_triggers_automatic_payment(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: Mock,
        mock_stripe: Mock,
        test_org: TenantData,
    ):
        # Mock the organization document returned after decrementing credits

        # Mock successful lock attempt
        mock_tenant_storage.attempt_lock_for_payment.return_value = test_org.model_copy(
            update={"locked_for_payment": True},
        )
        mock_stripe.Customer.retrieve_async.return_value = _mock_customer(payment_method=True)
        mock_stripe.PaymentIntent.create_async.return_value = _payment_intent()
        # Not sure why just using a return_value does not work here
        mock_stripe.PaymentIntent.confirm_async = AsyncMock(return_value=Mock(status="succeeded"))

        await stripe_service.handle_credit_decrement(test_org)

        # Verify all the expected calls
        mock_tenant_storage.attempt_lock_for_payment.assert_called_once()
        mock_tenant_storage.unlock_payment_for_failure.assert_not_called()
        mock_tenant_storage.unlock_payment_for_success.assert_not_called()

    async def test_decrement_credits_automatic_payment_fails(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: Mock,
        test_org: TenantData,
        mock_stripe: Mock,
        mock_email_service: Mock,
    ):
        # Mock successful lock attempt
        mock_lock_doc = Mock()
        mock_lock_doc.locked_for_payment = True
        mock_tenant_storage.attempt_lock_for_payment.return_value = test_org.model_copy(
            update={"locked_for_payment": True},
        )

        # Mock payment method retrieval
        mock_stripe.Customer.retrieve_async.return_value = _mock_customer(payment_method=True)

        # Mock payment intent creation and confirmation
        mock_payment_intent = Mock()
        mock_payment_intent.id = "pi_123"
        mock_stripe.PaymentIntent.create_async.return_value = mock_payment_intent
        mock_stripe.PaymentIntent.confirm_async.side_effect = Exception("Confirm payment failed")

        await stripe_service.handle_credit_decrement(test_org)

        # Verify all the expected calls
        mock_tenant_storage.attempt_lock_for_payment.assert_called_once()
        mock_tenant_storage.unlock_payment_for_failure.assert_called_once_with(
            now=mock.ANY,
            code="internal",
            failure_reason=mock.ANY,
        )

        await wait_for_background_tasks()
        mock_email_service.send_payment_failure_email.assert_called_once_with()

    async def test_decrement_credits_missing_payment_method(
        self,
        stripe_service: StripeService,
        mock_tenant_storage: Mock,
        test_org: TenantData,
        mock_stripe: Mock,
        mock_email_service: Mock,
    ):
        mock_lock_doc = Mock()
        mock_lock_doc.locked_for_payment = True
        mock_tenant_storage.attempt_lock_for_payment.return_value = test_org.model_copy(
            update={"locked_for_payment": True},
        )

        # Mock payment method retrieval
        mock_stripe.Customer.retrieve_async.return_value = _mock_customer(payment_method=False)

        await stripe_service.handle_credit_decrement(test_org)

        mock_tenant_storage.attempt_lock_for_payment.assert_called_once()
        mock_tenant_storage.unlock_payment_for_failure.assert_called_once_with(
            now=mock.ANY,
            code="payment_failed",
            failure_reason="The account does not have a default payment method",
        )

        await wait_for_background_tasks()
        mock_email_service.send_payment_failure_email.assert_called_once_with()

# pyright: reportPrivateUsage=false

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
import stripe

from core.domain.exceptions import BadRequestError
from core.domain.tenant_data import TenantData
from core.services.email_service import EmailService
from core.services.payment_service import PaymentService
from core.services.stripe.stripe_service import StripeService, _BaseMetadata, _skip_webhook
from core.utils.background import wait_for_background_tasks
from tests.fake_models import fake_tenant


@pytest.fixture
def mock_payment_service():
    return Mock(spec=PaymentService)


@pytest.fixture
def mock_email_service():
    return Mock(spec=EmailService)


@pytest.fixture
def stripe_service(mock_tenant_storage: Mock, mock_payment_service: Mock, mock_email_service: Mock):
    return StripeService(
        tenant_storage=mock_tenant_storage,
        payment_service=mock_payment_service,
        email_service=mock_email_service,
    )


@pytest.fixture
def mock_stripe():
    with patch("core.services.stripe.stripe_service.stripe") as mock:
        mock.PaymentIntent = AsyncMock(spec=stripe.PaymentIntent)
        mock.Customer = AsyncMock(spec=stripe.Customer)
        mock.PaymentMethod = AsyncMock(spec=stripe.PaymentMethod)
        mock.PaymentMethod.detach_async = AsyncMock(spec=stripe.PaymentMethod.detach_async)
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
        mock_payment_service: Mock,
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
        mock_payment_service.decrement_credits.assert_called_once_with(0)

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
        monkeypatch: Mock,
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
        monkeypatch.setattr(stripe.PaymentMethod, "attach_async", mock_attach)

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
                    "metadata": {"tenant": "test-tenant"},
                    "status": "succeeded",
                    "app": "anotherai",
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

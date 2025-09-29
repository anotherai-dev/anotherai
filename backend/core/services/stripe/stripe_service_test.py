# pyright: reportPrivateUsage=false

from unittest.mock import AsyncMock, Mock, patch

import pytest
import stripe

from core.domain.tenant_data import TenantData
from core.services.payment_service import PaymentService
from core.services.stripe.stripe_service import StripeService
from core.utils.background import wait_for_background_tasks


@pytest.fixture
def mock_payment_service():
    return Mock(spec=PaymentService)


@pytest.fixture
def stripe_service(mock_tenant_storage: Mock, mock_payment_service: Mock):
    return StripeService(tenant_storage=mock_tenant_storage, payment_service=mock_payment_service)


@pytest.fixture
def mock_stripe():
    with patch("core.services.stripe.stripe_service.stripe") as mock:
        mock.PaymentIntent = AsyncMock(spec=stripe.PaymentIntent)
        mock.Customer = AsyncMock(spec=stripe.Customer)
        mock.PaymentMethod = AsyncMock(spec=stripe.PaymentMethod)
        mock.CardError = stripe.CardError

        yield mock


def _mock_customer(payment_method: bool):
    # It would be better to build customer objects but the inits are weird
    customer = Mock()
    customer.id = "cus_123"
    customer.invoice_settings = Mock()
    if payment_method:
        customer.invoice_settings.default_payment_method = Mock()
        customer.invoice_settings.default_payment_method.id = "pm_123"
        customer.invoice_settings.default_payment_method.card = Mock()
        customer.invoice_settings.default_payment_method.card.last4 = "4242"
        customer.invoice_settings.default_payment_method.card.brand = "visa"
        customer.invoice_settings.default_payment_method.card.exp_month = 12
        customer.invoice_settings.default_payment_method.card.exp_year = 2025
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

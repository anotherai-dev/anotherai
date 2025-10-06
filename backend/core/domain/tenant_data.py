from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field
from structlog import get_logger

from core.domain.models import Provider
from core.providers._base.config import ProviderConfig

_log = get_logger(__name__)


class ProviderSettings(BaseModel):
    id: str
    created_at: datetime
    provider: Provider
    preserve_credits: bool | None = None

    def decrypt(self) -> ProviderConfig:
        # Implement decryption in subclasses
        raise NotImplementedError


class PublicOrganizationData(BaseModel):
    uid: int = 0  # will be filled by storage
    slug: str = ""
    org_id: str | None = None
    owner_id: str | None = None

    @computed_field
    @property
    def is_anonymous(self) -> bool:
        return not self.org_id and not self.owner_id


class User(BaseModel):
    sub: str
    email: str | None


class TenantData(PublicOrganizationData):
    created_at: datetime | None = None
    customer_id: str | None = None
    providers: list[ProviderSettings] = Field(default_factory=list, description="List of provider configurations")

    current_credits_usd: float = Field(default=0.0, description="Current credits available to the organization")
    locked_for_payment: bool | None = None

    automatic_payment_enabled: bool = Field(default=False, description="Automatic payment enabled")
    automatic_payment_threshold: float | None = Field(default=None, description="Automatic payment threshold")
    automatic_payment_balance_to_maintain: float | None = Field(
        default=None,
        description="Automatic payment balance to maintain",
    )
    feedback_slack_hook: str | None = Field(default=None, description="Slack webhook URL for feedback notifications")

    class PaymentFailure(BaseModel):
        failure_date: datetime
        failure_code: Literal["payment_failed", "internal"] | str
        failure_reason: str

    payment_failure: PaymentFailure | None = None

    # Set by the security service
    user: User | None = None

    def autocharge_amount(self, min_amount: float) -> float:
        """Returns the amount to charge or `min_amount` if no amount is needed"""
        if (
            self.automatic_payment_threshold is None
            or self.automatic_payment_balance_to_maintain is None
            or self.current_credits_usd > self.automatic_payment_threshold
        ):
            return min_amount

        amount = self.automatic_payment_balance_to_maintain - self.current_credits_usd
        # This can happen if automatic_payment_threshold > automatic_payment_balance_to_maintain
        # For example: threshold = 100, maintain = 50, current = 75
        # This would be a stupid case.
        if amount <= min_amount:
            _log.warning(
                "Automatic payment would charge negative amount",
                tenant={"tenant": self.model_dump(exclude_none=True, exclude={"providers"})},
            )
            # Returning the balance to maintain to avoid charging 0
            return min_amount or self.automatic_payment_balance_to_maintain

        return amount

    def should_trigger_automatic_payment(self, min_amount: float) -> bool:
        return (
            self.automatic_payment_enabled
            and not self.locked_for_payment
            and not self.payment_failure
            and self.autocharge_amount(min_amount=0) > 0
        )

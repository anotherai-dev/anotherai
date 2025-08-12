from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, computed_field

from core.domain.models import Provider
from core.providers._base.config import ProviderConfig


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

class TenantData(PublicOrganizationData):
    stripe_customer_id: str | None = None
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
        failure_code: Literal["payment_failed", "internal"]
        failure_reason: str

    payment_failure: PaymentFailure | None = None
    # Credits are expressed in cts to avoid floating point precision issues
    low_credits_email_sent_by_threshold: dict[int, datetime] | None = Field(
        default=None,
        description="A dictionary of low credits emails sent by threshold that triggered the email",
    )

    slack_channel_id: str | None = None

    def should_send_low_credits_email(self, threshold_usd: float) -> bool:
        if self.current_credits_usd >= threshold_usd:
            return False
        if not self.low_credits_email_sent_by_threshold:
            return True

        cts = round(threshold_usd * 100)
        # If there is a low_credits_email_sent_by_threshold entry for this threshold or any threshold below it
        # Then we should not send the email
        if any(k <= cts for k in self.low_credits_email_sent_by_threshold):  # noqa: SIM103
            return False

        return True

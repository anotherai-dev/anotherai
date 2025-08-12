from pydantic import BaseModel

from core.domain.error import Error
from core.domain.inference import LLMTrace
from core.domain.models.models import Model
from core.domain.models.providers import Provider
from core.providers._base.llm_usage import LLMUsage


# TODO: remove and use domain model instead
class LLMCompletion(BaseModel):
    duration_seconds: float | None = None

    response: str | None = None

    usage: LLMUsage

    # The provider that was used to generate the completion
    provider: Provider

    # None is for backwards compatibility
    # When model is None, the model that was used is the same model as the requested model from the version
    model: Model

    config_id: str | None = None

    preserve_credits: bool | None = None

    provider_request_incurs_cost: bool | None = None

    error: Error | None = None

    def should_incur_cost(self) -> bool:
        if self.provider_request_incurs_cost is not None:
            return self.provider_request_incurs_cost
        if self.usage.completion_image_count:
            return True
        return not (self.response is None and self.usage.completion_token_count == 0)

    def to_domain(self) -> LLMTrace:
        return LLMTrace(
            model=self.model,
            provider=self.provider,
            usage=self.usage.to_domain(),
            duration_seconds=self.duration_seconds or 0,
            cost_usd=self.usage.cost_usd or 0,
        )

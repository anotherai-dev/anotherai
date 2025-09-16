from pydantic import BaseModel, ConfigDict, Field

from core.domain.inference_usage import CompletionUsage, InferenceUsage, TokenUsage


# TODO: use domain model instead
class LLMPromptUsage(BaseModel):
    # Tokens are floats because it is possible for some providers to have fractional tokens.
    # For example, for google we count 4 characters as 1 token, so the number of tokens is 1/4 the number of characters.

    prompt_token_count: float | None = None
    prompt_token_count_cached: float | None = Field(
        default=None,
        description="The part of the prompt_token_count that were cached from a previous request.",
    )
    prompt_cost_usd: float | None = None
    prompt_audio_token_count: float | None = None
    prompt_audio_duration_seconds: float | None = None
    prompt_image_count: int | None = None
    prompt_image_token_count: float | None = None


class LLMCompletionUsage(BaseModel):
    completion_token_count: float | None = None
    completion_cost_usd: float | None = None
    reasoning_token_count: float | None = None
    completion_image_token_count: float | None = None
    completion_image_count: int | None = None


class LLMUsage(LLMPromptUsage, LLMCompletionUsage):
    model_context_window_size: int | None = None

    @property
    def cost_usd(self) -> float | None:
        if self.prompt_cost_usd is not None and self.completion_cost_usd is not None:
            return self.prompt_cost_usd + self.completion_cost_usd
        # If either 'prompt_cost_usd' or 'completion_cost_usd' is missing, we consider there is a problem and prefer
        # to return nothing rather than a False value.
        return None

    model_config = ConfigDict(
        protected_namespaces=(),
    )

    def to_domain(self) -> InferenceUsage:
        return InferenceUsage(
            prompt=TokenUsage(
                text_token_count=self.prompt_token_count,
                cost_usd=self.prompt_cost_usd or 0,
            ),
            completion=CompletionUsage(
                cached_token_count=self.prompt_token_count_cached,
                reasoning_token_count=self.reasoning_token_count,
                text_token_count=self.completion_token_count,
                cost_usd=self.completion_cost_usd or 0,
            ),
        )

    def apply(self, other: "LLMUsage"):
        for k in other.model_fields_set:
            setattr(self, k, getattr(other, k))

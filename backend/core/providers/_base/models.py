from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from core.providers._base.llm_completion import LLMCompletion
from core.providers._base.llm_usage import LLMUsage
from core.utils.fields import datetime_factory


class RawCompletion(BaseModel):
    response: str | None
    usage: LLMUsage
    finish_reason: str | None = None

    start_time: datetime = Field(default_factory=datetime_factory)

    model_config = ConfigDict(extra="allow")

    def apply_to(self, llm_completion: LLMCompletion):
        if self.usage.completion_image_count is not None:
            llm_completion.usage.completion_image_count = self.usage.completion_image_count
        if self.usage.completion_token_count is not None:
            llm_completion.usage.completion_token_count = self.usage.completion_token_count
        if self.usage.completion_cost_usd is not None:
            llm_completion.usage.completion_cost_usd = self.usage.completion_cost_usd
        if self.usage.prompt_token_count is not None:
            llm_completion.usage.prompt_token_count = self.usage.prompt_token_count
        if self.usage.prompt_cost_usd is not None:
            llm_completion.usage.prompt_cost_usd = self.usage.prompt_cost_usd
        if self.usage.prompt_token_count_cached is not None:
            llm_completion.usage.prompt_token_count_cached = self.usage.prompt_token_count_cached
        if self.usage.model_context_window_size is not None:
            llm_completion.usage.model_context_window_size = self.usage.model_context_window_size
        if self.usage.reasoning_token_count is not None:
            llm_completion.usage.reasoning_token_count = self.usage.reasoning_token_count

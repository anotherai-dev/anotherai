from typing import Any

import structlog
from pydantic import BaseModel

from core.domain.models.model_data import ModelReasoningBudget
from core.domain.models.models import Model
from core.domain.reasoning_effort import ReasoningEffort
from core.domain.tool import Tool
from core.domain.tool_choice import ToolChoice

log = structlog.get_logger(__name__)


class ProviderOptions(BaseModel):
    model: Model
    output_schema: dict[str, Any] | None = None
    task_name: str | None = None
    temperature: float = 0
    max_tokens: int | None = None
    structured_generation: bool = False
    timeout: float | None = None
    enabled_tools: list[Tool] | None = None
    tenant: str | None = None
    stream_deltas: bool = False
    tool_choice: ToolChoice | None = None
    top_p: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    parallel_tool_calls: bool | None = None
    reasoning_effort: ReasoningEffort | None = None
    reasoning_budget: int | None = None

    def _log_warning_if_no_reasoning_budget(self):
        if self.reasoning_effort is not None or self.reasoning_budget is not None:
            # TODO: remove warning
            # That could be linked to user error and so we should not log it. Logging for now to spot inconsistencies
            log.warning(
                "Version has reasoning configured but the model does not support reasoning",
                options=self,
            )

    def final_reasoning_effort(
        self,
        reasoning_budget: ModelReasoningBudget | None,
    ) -> ReasoningEffort | None:
        if reasoning_budget is None:
            self._log_warning_if_no_reasoning_budget()
            return None
        if self.reasoning_effort:
            # If the model does not support the reasoning effort, we return None
            if reasoning_budget[self.reasoning_effort] is None:
                log.info(
                    "Reasoning effort is not supported by the model",
                    options=self,
                )
                return None
            return self.reasoning_effort
        if self.reasoning_budget is None:
            return None
        return reasoning_budget.corresponding_effort(self.reasoning_budget)

    def final_reasoning_budget(
        self,
        reasoning_budget: ModelReasoningBudget | None,
    ) -> int | None:
        if reasoning_budget is None:
            self._log_warning_if_no_reasoning_budget()
            return None
        if self.reasoning_budget is not None:
            if self.reasoning_budget > reasoning_budget.max:
                return reasoning_budget.max
            if reasoning_budget.min and self.reasoning_budget < reasoning_budget.min:
                return reasoning_budget.min
            return self.reasoning_budget
        if self.reasoning_effort is None:
            return None
        return reasoning_budget.corresponding_budget(self.reasoning_effort)

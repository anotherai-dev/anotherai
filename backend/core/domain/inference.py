from typing import Annotated, Literal

from pydantic import BaseModel, Field

from core.domain.inference_usage import InferenceUsage


class _Trace(BaseModel):
    duration_seconds: float
    cost_usd: float


class LLMTrace(_Trace):
    kind: Literal["llm"] = "llm"

    model: str
    provider: str
    usage: InferenceUsage | None = None


class ToolTrace(_Trace):
    kind: Literal["tool"] = "tool"
    name: str
    tool_input_preview: str
    tool_output_preview: str


type Trace = Annotated[LLMTrace | ToolTrace, Field(discriminator="kind")]

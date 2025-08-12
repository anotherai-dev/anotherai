from typing import Literal

from pydantic import BaseModel, Field

INTERNAL_AGENT_RUN_RESULT_SCHEMA_KEY = "tool_call_error"


class ToolCallError(BaseModel):
    """An opportunity for a model to decide that a tool call failed.
    Added dynamically to response formats when possible."""

    error_code: Literal["tool_call_error", "missing_tool", "other"] | None = Field(
        default=None,
        description="The type of error that occurred during the inference, 'tool_call_error' if an error occurred "
        "during a tool call, 'missing_tool' if the agent is missing a tool in order to complete the inference, 'other' "
        "for any other error",
    )
    error_message: str | None = Field(
        default=None,
        description="A summary of the error",
    )

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from core.domain.agent import Agent
from core.domain.agent_input import AgentInput
from core.domain.agent_output import AgentOutput
from core.domain.message import Message
from core.domain.trace import LLMTrace, Trace
from core.domain.version import Version
from core.utils.uuid import uuid7_generation_time


class AgentCompletion(BaseModel):
    id: UUID = Field(
        description="the id of the task run. If not provided a uuid will be generated",
    )

    agent: Agent

    agent_input: AgentInput

    agent_output: AgentOutput

    messages: list[Message] = Field(
        description="The rendered list of messages that were sent to the agent. Not including the output messages.",
    )

    version: Version

    status: Literal["success", "failure"] = "success"

    duration_seconds: float | None = None
    cost_usd: float | None = None

    traces: list[Trace]

    from_cache: bool = False

    source: Literal["web", "api", "mcp"] = "api"

    metadata: dict[str, Any] | None = None

    @property
    def final_model(self) -> str | None:
        for t in reversed(self.traces):
            if isinstance(t, LLMTrace):
                return t.model
        return None

    @property
    def created_at(self) -> datetime:
        return uuid7_generation_time(self.id)

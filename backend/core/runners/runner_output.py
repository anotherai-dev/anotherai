import json
from collections.abc import Sequence
from typing import Any, NamedTuple

from structlog import get_logger

from core.domain.message import Message, MessageContent
from core.domain.tool_call import ToolCallRequest

_log = get_logger(__name__)


class RunnerOutput(NamedTuple):
    # agent_output should always be a string here
    agent_output: Any
    tool_call_requests: Sequence[ToolCallRequest] | None = None
    reasoning: str | None = None

    def _stringified_output(self) -> str:
        if isinstance(self.agent_output, str):
            return self.agent_output
        return json.dumps(self.agent_output)

    def to_messages(self) -> list[Message]:
        content: list[MessageContent] = []
        if self.agent_output:
            if isinstance(self.agent_output, str):
                content.append(MessageContent(text=self.agent_output))
            elif isinstance(self.agent_output, (dict, list)):
                content.append(MessageContent(object=self.agent_output))
            else:
                _log.warning("Unknown agent output type", agent_output=self.agent_output)
        if self.tool_call_requests:
            content.extend([MessageContent(tool_call_request=t) for t in self.tool_call_requests])
        if self.reasoning:
            content.append(MessageContent(text=self.reasoning))

        return [Message(role="assistant", content=content)]

    def as_chunk(self):
        """Forces a delta based on the agent output"""
        delta = self.agent_output if isinstance(self.agent_output, str) else json.dumps(self.agent_output)
        return RunnerOutputChunk(
            tool_call_requests=[ToolCallRequestDelta.from_domain(t) for t in self.tool_call_requests]
            if self.tool_call_requests
            else None,
            reasoning=self.reasoning,
            delta=delta,
            final_chunk=self,
        )


class ToolCallRequestDelta(NamedTuple):
    id: str
    idx: int | None
    tool_name: str
    arguments: str = ""
    arguments_dict: dict[str, Any] | None = None

    @classmethod
    def from_domain(cls, output: ToolCallRequest):
        return cls(
            id=output.id,
            idx=output.index,
            tool_name=output.tool_name,
            arguments=json.dumps(output.tool_input_dict),
        )


class RunnerOutputChunk(NamedTuple):
    tool_call_requests: Sequence[ToolCallRequestDelta] | None = None
    reasoning: str | None = None
    delta: str | None = None

    final_chunk: RunnerOutput | None = None

    def is_empty(self) -> bool:
        return all(v is None for v in self)

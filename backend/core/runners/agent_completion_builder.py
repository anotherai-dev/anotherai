from typing import Any

from pydantic import BaseModel, Field

from core.domain.agent import Agent
from core.domain.agent_completion import AgentCompletion
from core.domain.agent_input import AgentInput
from core.domain.agent_output import AgentOutput
from core.domain.error import Error
from core.domain.message import Message
from core.domain.trace import Trace
from core.domain.version import Version
from core.providers._base.llm_completion import LLMCompletion
from core.runners.runner_output import RunnerOutput


class AgentCompletionBuilder(BaseModel):
    id: str
    agent: Agent
    version: Version
    agent_input: AgentInput
    messages: list[Message]
    start_time: float
    conversation_id: str | None

    metadata: dict[str, Any]

    llm_completions: list[LLMCompletion] = Field(default_factory=list)

    file_download_seconds: float | None = None

    def add_metadata(self, key: str, value: Any) -> None:
        self.metadata[key] = value

    def get_metadata(self, key: str) -> Any | None:
        return self.metadata.get(key)

    def record_file_download_seconds(self, seconds: float):
        self.file_download_seconds = seconds

    _built_completion: AgentCompletion | None = None

    @property
    def completion(self):
        return self._built_completion

    def build(self, output: RunnerOutput, error: Error | None = None, force: bool = False) -> AgentCompletion:
        if self._built_completion and not force:
            return self._built_completion

        output_messages = output.to_messages()
        traces: list[Trace] = [llm_completion.to_domain() for llm_completion in self.llm_completions]

        self._built_completion = AgentCompletion(
            id=self.id,
            agent=self.agent,
            agent_input=self.agent_input,
            agent_output=AgentOutput(messages=output_messages, error=error),
            version=self.version,
            traces=traces,
            messages=self.messages,
            cost_usd=sum(trace.cost_usd for trace in traces),
            duration_seconds=sum(trace.duration_seconds for trace in traces),
            metadata=self.metadata,
        )
        return self._built_completion

    def append_metadata(self, key: str, value: Any) -> None:
        if metadata := self.get_metadata(key):
            if isinstance(metadata, list):
                metadata.append(value)  # pyright: ignore [reportUnknownMemberType]
            else:
                self.add_metadata(key, [metadata, value])
        else:
            self.add_metadata(key, [value])

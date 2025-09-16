from collections.abc import Callable
from typing import Any, NamedTuple

from pydantic import BaseModel, Field

from core.domain.finish_reason import FinishReason
from core.domain.tool_call import ToolCallRequest
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.models import RawCompletion
from core.providers._base.provider_error import FailedGenerationError, InvalidGenerationError, MaxTokensExceededError
from core.runners.runner_output import RunnerOutput, RunnerOutputChunk, ToolCallRequestDelta


class _ToolCallRequestBuffer(BaseModel):
    id: str | None = None
    idx: int | None = None
    tool_name: str | None = None
    tool_input: list[str] = Field(default_factory=list)


class ParsedResponse(NamedTuple):
    tool_call_requests: list[ToolCallRequestDelta] | None = None
    reasoning: str | None = None
    delta: str | None = None
    usage: LLMUsage | None = None
    finish_reason: FinishReason | None = None
    # TODO: we could pass final here since we usually know
    # This would avoid an extra streamed chunk


class StreamingContext:
    def __init__(self, raw_completion: RawCompletion):
        # self.streamer = JSONStreamParser() if json else RawStreamParser()
        # self.agg_output: dict[str, Any] = {}

        self.raw_completion = raw_completion

        self._tool_call_request_buffer: dict[int, _ToolCallRequestBuffer] = {}
        self._last_chunk: ParsedResponse | None = None

        self._agg_output: list[str] = []
        self._agg_tool_calls: list[ToolCallRequest] = []
        self._agg_reasoning: list[str] = []

        self._runner_output: RunnerOutput | None = None
        self._usage: LLMUsage = LLMUsage()

        # TODO: usage

    @property
    def final_output(self) -> RunnerOutput | None:
        return self._runner_output

    def _add_tool_call_delta(self, chunk: ToolCallRequestDelta):
        # TODO:
        pass

    def aggregated_output(self) -> str:
        return "".join(self._agg_output)

    def _apply_usage(self, usage: LLMUsage):
        self._usage.apply(usage)

    def add_chunk(self, chunk: ParsedResponse) -> RunnerOutputChunk:
        # TODO: agg reasoning and tool calls
        self._last_chunk = chunk

        if chunk.tool_call_requests:
            for tool_call_request in chunk.tool_call_requests:
                self._add_tool_call_delta(tool_call_request)
        if chunk.reasoning:
            self._agg_reasoning.append(chunk.reasoning)
        if chunk.delta:
            self._agg_output.append(chunk.delta)

        if chunk.finish_reason:
            self._raise_for_finish_reason(chunk.finish_reason)

        if chunk.usage:
            self._apply_usage(chunk.usage)

        return RunnerOutputChunk(
            tool_call_requests=self._last_chunk.tool_call_requests,
            reasoning=self._last_chunk.reasoning,
            delta=self._last_chunk.delta,
            final_chunk=self._runner_output,
        )

    def _raise_for_finish_reason(self, reason: FinishReason):
        self.raw_completion.usage = self._usage
        self.raw_completion.finish_reason = reason
        match reason:
            case "max_context":
                raise MaxTokensExceededError(
                    msg="Model returned a response with a length finish reason, meaning the maximum number of tokens was exceeded.",
                    raw_completion=self.raw_completion,
                )
            case "malformed_function_call":
                raise InvalidGenerationError(
                    msg="Model returned a malformed function call finish reason",
                    # Capturing so we can see why this happens
                    capture=True,
                )
            case "recitation":
                raise FailedGenerationError(
                    msg="Model returned a response with a recitation finish reason.",
                    raw_completion=self.raw_completion,
                )

    def complete(self, output_factory: Callable[[str], Any]) -> RunnerOutputChunk:
        self._runner_output = RunnerOutput(
            agent_output=output_factory("".join(self._agg_output)),
            reasoning="".join(self._agg_reasoning),
            tool_call_requests=self._agg_tool_calls,
        )
        return RunnerOutputChunk(
            tool_call_requests=None,
            reasoning=None,
            delta=None,
            final_chunk=self._runner_output,
        )

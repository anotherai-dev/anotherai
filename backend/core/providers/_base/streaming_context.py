import json
from collections.abc import Callable
from typing import NamedTuple

from pydantic import BaseModel, Field

from core.domain.finish_reason import FinishReason
from core.domain.tool_call import ToolCallRequest
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.models import RawCompletion
from core.providers._base.provider_error import FailedGenerationError, InvalidGenerationError, MaxTokensExceededError
from core.runners.runner_output import RunnerOutput, RunnerOutputChunk, ToolCallRequestDelta


class _ToolCallRequestBuffer(BaseModel):
    id: str | None = None
    idx: int
    tool_name: str | None = None
    tool_input: list[str] = Field(default_factory=list)

    def should_handle_delta(self, delta: ToolCallRequestDelta) -> bool:
        if delta.idx is not None:
            return delta.idx == self.idx
        if delta.id:
            return delta.id == self.id
        if delta.tool_name:
            return delta.tool_name == self.tool_name
        return True

    def add_delta(self, delta: ToolCallRequestDelta):
        self.tool_input.append(delta.arguments)

    @classmethod
    def from_delta(cls, delta: ToolCallRequestDelta, default_idx: int):
        return cls(
            id=delta.id,
            idx=delta.idx or default_idx,
            tool_name=delta.tool_name,
            tool_input=[delta.arguments],
        )

    def to_tool_call(self) -> ToolCallRequest:
        _final_input = "".join(self.tool_input)
        try:
            input_dict = json.loads(_final_input) if _final_input else {}
        except json.JSONDecodeError as e:
            raise InvalidGenerationError(
                msg="Model returned a tool call with unparseable arguments",
                capture=True,
                extras={
                    "arguments": _final_input,
                },
            ) from e
        return ToolCallRequest(
            index=self.idx,
            id=self.id or "",
            tool_name=self.tool_name or "",
            tool_input_dict=input_dict,
        )


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

        self._tool_call_buffers: list[_ToolCallRequestBuffer] = []
        self._last_chunk: ParsedResponse | None = None

        self._agg_output: list[str] = []
        self._agg_reasoning: list[str] = []

        self._runner_output: RunnerOutput | None = None
        self._usage: LLMUsage = LLMUsage()

        # TODO: usage

    @property
    def final_output(self) -> RunnerOutput | None:
        return self._runner_output

    def _add_tool_call_delta(self, chunk: ToolCallRequestDelta):
        for b in reversed(self._tool_call_buffers):
            if b.should_handle_delta(chunk):
                b.add_delta(chunk)
                return
        self._tool_call_buffers.append(_ToolCallRequestBuffer.from_delta(chunk, len(self._tool_call_buffers)))

    def _tool_calls(self) -> list[ToolCallRequest]:
        return [b.to_tool_call() for b in self._tool_call_buffers]

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

        if chunk.usage:
            self._apply_usage(chunk.usage)

        if chunk.finish_reason:
            self._raise_for_finish_reason(chunk.finish_reason)

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

    def complete(
        self,
        builder: Callable[[str, str | None, list[ToolCallRequest] | None], RunnerOutput],
    ) -> RunnerOutputChunk:
        self._runner_output = builder("".join(self._agg_output), "".join(self._agg_reasoning), self._tool_calls())

        return RunnerOutputChunk(
            tool_call_requests=None,
            reasoning=None,
            delta=None,
            final_chunk=self._runner_output,
        )

    @property
    def usage(self) -> LLMUsage:
        return self._usage

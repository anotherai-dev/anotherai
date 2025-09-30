from typing import override

from structlog import get_logger

from core.providers._base.models import RawCompletion
from core.providers._base.streaming_context import ParsedResponse, StreamingContext
from core.runners.runner_output import RunnerOutputChunk

_log = get_logger(__name__)


class FireworksStreamingContext(StreamingContext):
    @override
    def __init__(self, raw_completion: RawCompletion):
        super().__init__(raw_completion)

        self._thinking: bool | None = None

    @override
    def add_chunk(self, chunk: ParsedResponse) -> RunnerOutputChunk:
        # Fireworks returns the thinking within tags at the beginning of the stream
        if not chunk.delta or self._thinking is False:
            # if we don't have a delta, there is no thinking
            return super().add_chunk(chunk)

        if self._thinking is None:
            # Never passed a thinking tag so we look for the opening thinking tag
            index = chunk.delta.find("<think>")
            if index == -1:
                # No thinking so we can just call super
                return super().add_chunk(chunk)

            # We found a thinking tag
            if index:
                pre_thinking_content = chunk.delta[:index]
                if strped := pre_thinking_content.strip():
                    _log.warning("Unexpected pre thinking content", content=strped)
            self._thinking = True
            reasoning = chunk.delta[index + 6 :]
            chunk = chunk._replace(**_split_end_thinking_tag(reasoning))
            return super().add_chunk(chunk)
            # Not returning directly just in case the entire thinking block is streamed in one chunk

        # Thinking is true
        return super().add_chunk(chunk._replace(**_split_end_thinking_tag(chunk.delta)))


def _split_end_thinking_tag(var: str) -> dict[str, str | None]:
    """Returns a tuple [reasoning, delta]"""
    index = var.find("</think>")
    if index == -1:
        # Not found, still in reasoning
        return {"reasoning": var}
    return {"reasoning": var[:index], "delta": var[index + 7 :] or None}

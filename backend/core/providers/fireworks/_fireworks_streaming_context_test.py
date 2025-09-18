# pyright: reportPrivateUsage=false

import pytest

from core.providers._base.llm_usage import LLMUsage
from core.providers._base.models import RawCompletion
from core.providers._base.streaming_context import ParsedResponse
from core.providers.fireworks._fireworks_streaming_context import FireworksStreamingContext


@pytest.fixture
def streaming_context():
    return FireworksStreamingContext(RawCompletion(response="", usage=LLMUsage()))


class TestAddChunk:
    def test_add_chunk_reasoning_only_no_delta(self):
        ctx = FireworksStreamingContext(RawCompletion(response="", usage=LLMUsage()))
        chunk = ParsedResponse(reasoning="Some thoughts")
        ctx.add_chunk(chunk)
        assert ctx._agg_reasoning == ["Some thoughts"]
        assert ctx.aggregated_output() == ""

    def test_add_chunk_no_thinking_tag_delta_only(self, streaming_context):
        chunk = ParsedResponse(delta="hello world")
        streaming_context.add_chunk(chunk)
        assert streaming_context._agg_reasoning == []
        assert streaming_context.aggregated_output() == "hello world"

    def test_add_chunk_opening_tag_at_start_no_close(self, streaming_context):
        chunk = ParsedResponse(delta="<think>AAA")
        streaming_context.add_chunk(chunk)
        # Current implementation keeps the '>' from the opening tag and also appends original delta to output
        assert streaming_context._agg_reasoning == [">AAA"]
        assert streaming_context.aggregated_output() == "<think>AAA"
        assert streaming_context._thinking is True

    def test_add_chunk_opening_tag_with_pre_content_ignored(self, streaming_context):
        chunk = ParsedResponse(delta="PRE <think>AAA")
        streaming_context.add_chunk(chunk)
        assert streaming_context._agg_reasoning == [">AAA"]
        assert streaming_context.aggregated_output() == "PRE <think>AAA"

    def test_add_chunk_ongoing_thinking_no_close(self, streaming_context):
        streaming_context.add_chunk(ParsedResponse(delta="<think>AAA"))
        streaming_context.add_chunk(ParsedResponse(delta="BBB"))
        assert streaming_context._agg_reasoning == [">AAA", "BBB"]
        assert streaming_context.aggregated_output() == "<think>AAABBB"

    def test_add_chunk_thinking_end_and_post_content_same_chunk(self, streaming_context):
        streaming_context.add_chunk(ParsedResponse(delta="<think>AAA"))
        streaming_context.add_chunk(ParsedResponse(delta="BBB</think>AFTER"))
        assert streaming_context._agg_reasoning == [">AAA", "BBB"]
        # Current implementation yields an extra '>' before the post-content
        assert streaming_context.aggregated_output() == "<think>AAA>AFTER"

    def test_add_chunk_entire_thinking_in_single_chunk(self, streaming_context):
        streaming_context.add_chunk(ParsedResponse(delta="<think>XYZ</think>OUT"))
        assert streaming_context._agg_reasoning == [">XYZ"]
        assert streaming_context.aggregated_output() == ">OUT"

    def test_add_chunk_when_thinking_is_false_bypasses_processing(self, streaming_context):
        streaming_context._thinking = False
        streaming_context.add_chunk(ParsedResponse(delta="later"))
        assert streaming_context._agg_reasoning == []
        assert streaming_context.aggregated_output() == "later"

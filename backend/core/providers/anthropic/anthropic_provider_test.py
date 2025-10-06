# pyright: reportPrivateUsage=false

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

import pytest
from httpx import Response
from pytest_httpx import HTTPXMock, IteratorStream

from core.domain.file import File
from core.domain.message import Message, MessageContent, MessageDeprecated
from core.domain.models import Model
from core.domain.models.model_provider_data_mapping import ANTHROPIC_PROVIDER_DATA
from core.domain.models.utils import get_model_data
from core.domain.tool import Tool
from core.domain.tool_call import ToolCallRequest
from core.domain.tool_choice import ToolChoice, ToolChoiceFunction
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.models import RawCompletion
from core.providers._base.provider_error import (
    MaxTokensExceededError,
    ProviderBadRequestError,
    ProviderError,
    ProviderInternalError,
    ProviderInvalidFileError,
    ServerOverloadedError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers.anthropic.anthropic_domain import (
    AnthropicMessage,
    AntToolChoice,
    CompletionRequest,
    CompletionResponse,
    ContentBlock,
    TextContent,
    ThinkingContent,
    ToolUseContent,
    Usage,
)
from core.providers.anthropic.anthropic_provider import AnthropicConfig, AnthropicProvider
from tests.utils import fixture_bytes, fixtures_json, mock_aiter


@pytest.fixture
def anthropic_provider():
    return AnthropicProvider(
        config=AnthropicConfig(api_key="test"),
    )


def _output_factory(x: str):
    return x


class TestMaxTokens:
    @pytest.mark.parametrize(
        ("model", "requested_max_tokens", "thinking_budget", "expected_max_tokens"),
        [
            pytest.param(Model.CLAUDE_3_5_HAIKU_LATEST, 10, None, 10, id="Requested less than default, no thinking"),
            pytest.param(Model.CLAUDE_3_7_SONNET_20250219, None, None, 8192, id="Default, no thinking"),
            pytest.param(
                Model.CLAUDE_3_7_SONNET_20250219,
                50_000,
                None,
                50_000,
                id="Requested less than max, no thinking",
            ),
            pytest.param(
                Model.CLAUDE_3_7_SONNET_20250219,
                100_000,
                None,
                64_000,
                id="Requested more than max, no thinking",
            ),
            pytest.param(Model.CLAUDE_3_7_SONNET_20250219, 10, 500, 510, id="Requested with thinking budget"),
            pytest.param(Model.CLAUDE_3_7_SONNET_20250219, None, 1000, 9192, id="Default with thinking budget"),
            pytest.param(
                Model.CLAUDE_3_7_SONNET_20250219,
                50_000,
                2000,
                52_000,
                id="Requested with thinking budget less than max",
            ),
            pytest.param(
                Model.CLAUDE_3_7_SONNET_20250219,
                62_000,
                3000,
                64_000,
                id="Requested with thinking budget exceeds max",
            ),
            pytest.param(
                Model.CLAUDE_3_7_SONNET_20250219,
                100_000,
                5000,
                64_000,
                id="Both requested and thinking exceed max",
            ),
        ],
    )
    def test_max_tokens(
        self,
        anthropic_provider: AnthropicProvider,
        model: Model,
        requested_max_tokens: int | None,
        thinking_budget: int | None,
        expected_max_tokens: int,
    ):
        assert (
            anthropic_provider._max_tokens(get_model_data(model), requested_max_tokens, thinking_budget)
            == expected_max_tokens
        )

    def test_max_tokens_with_missing_model_data(self, anthropic_provider: AnthropicProvider):
        """Test that the method handles missing model max tokens by using default."""
        # Create a mock model data with no max_output_tokens
        model_data = get_model_data(Model.CLAUDE_3_7_SONNET_20250219)
        original_max_output_tokens = model_data.max_tokens_data.max_output_tokens

        # Temporarily set max_output_tokens to None to test the fallback
        model_data.max_tokens_data.max_output_tokens = None

        try:
            result = anthropic_provider._max_tokens(model_data, 1000, 500)
            # Should use DEFAULT_MAX_TOKENS (8192) as the ceiling
            assert result == 1500  # requested 1000 + thinking 500
        finally:
            # Restore original value
            model_data.max_tokens_data.max_output_tokens = original_max_output_tokens

    def test_max_tokens_with_missing_model_data_exceeds_default(self, anthropic_provider: AnthropicProvider):
        """Test that the method handles missing model max tokens when requested exceeds default."""
        # Create a mock model data with no max_output_tokens
        model_data = get_model_data(Model.CLAUDE_3_7_SONNET_20250219)
        original_max_output_tokens = model_data.max_tokens_data.max_output_tokens

        # Temporarily set max_output_tokens to None to test the fallback
        model_data.max_tokens_data.max_output_tokens = None

        try:
            result = anthropic_provider._max_tokens(model_data, 10000, 2000)
            # Should use DEFAULT_MAX_TOKENS (8192) as the ceiling
            assert result == 8192  # min(10000 + 2000, 8192) = 8192
        finally:
            # Restore original value
            model_data.max_tokens_data.max_output_tokens = original_max_output_tokens


class TestBuildRequest:
    def test_build_request(self, anthropic_provider: AnthropicProvider):
        request = cast(
            CompletionRequest,
            anthropic_provider._build_request(
                messages=[
                    MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="Hello 1"),
                    MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello"),
                ],
                options=ProviderOptions(model=Model.CLAUDE_3_5_SONNET_20241022, max_tokens=10, temperature=0),
                stream=False,
            ),
        )
        assert request.system == "Hello 1"
        assert request.model_dump(include={"messages"})["messages"] == [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Hello",
                    },
                ],
            },
        ]
        assert request.temperature == 0
        assert request.max_tokens == 10

    def test_build_request_without_max_tokens(self, anthropic_provider: AnthropicProvider):
        request = cast(
            CompletionRequest,
            anthropic_provider._build_request(
                messages=[
                    MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="Hello 1"),
                    MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello"),
                ],
                options=ProviderOptions(model=Model.CLAUDE_3_7_SONNET_20250219, temperature=0),
                stream=False,
            ),
        )

        assert request.max_tokens == 8192

    @pytest.mark.parametrize("model", ANTHROPIC_PROVIDER_DATA.keys())
    def test_build_request_with_tools(self, anthropic_provider: AnthropicProvider, model: Model) -> None:
        # Import the expected Tool type

        # Use a dummy tool based on SimpleNamespace and cast it to the expected Tool type
        dummy_tool = Tool(
            name="dummy",
            description="A dummy tool",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
        )

        options = ProviderOptions(model=model, max_tokens=10, temperature=0, enabled_tools=[dummy_tool])  # pyright: ignore [reportGeneralTypeIssues]
        message = MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")

        request = cast(
            CompletionRequest,
            anthropic_provider._build_request(
                messages=[message],
                options=options,
                stream=False,
            ),
        )

        request_dict = request.model_dump()
        assert "tools" in request_dict
        tools = cast(list[dict[str, Any]], request_dict["tools"])
        assert len(tools) == 1
        tool = tools[0]
        assert tool["name"] == "dummy"
        assert tool["description"] == "A dummy tool"
        assert tool["input_schema"] == {"type": "object", "properties": {}}

    @pytest.mark.parametrize(
        ("tool_choice_option", "expected_ant_tool_choice"),
        [
            pytest.param("none", AntToolChoice(type="none"), id="None"),
            pytest.param("auto", AntToolChoice(type="auto"), id="AUTO"),
            pytest.param("required", AntToolChoice(type="any"), id="required"),
            pytest.param(
                ToolChoiceFunction(name="specific_tool_name"),
                AntToolChoice(type="tool", name="specific_tool_name"),
                id="TOOL_NAME",
            ),
        ],
    )
    def test_build_request_with_tool_choice(
        self,
        anthropic_provider: AnthropicProvider,
        tool_choice_option: ToolChoice | None,
        expected_ant_tool_choice: AntToolChoice,
    ):
        model = Model.CLAUDE_3_5_SONNET_20241022  # Use a specific model for simplicity
        request = cast(
            CompletionRequest,
            anthropic_provider._build_request(
                messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
                options=ProviderOptions(model=model, tool_choice=tool_choice_option),
                stream=False,
            ),
        )
        assert request.tool_choice == expected_ant_tool_choice

    def test_build_request_no_messages(self, anthropic_provider: AnthropicProvider):
        request = cast(
            CompletionRequest,
            anthropic_provider._build_request(
                messages=[
                    MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="You are a helpful assistant."),
                ],
                options=ProviderOptions(model=Model.CLAUDE_3_5_SONNET_20241022),
                stream=False,
            ),
        )
        assert request.system == "You are a helpful assistant."
        assert request.messages == [
            AnthropicMessage(role="user", content=[TextContent(text="-")]),
        ]

    def test_build_request_with_thinking_budget(self, anthropic_provider: AnthropicProvider):
        """Test that thinking budget is properly configured in requests."""
        from core.domain.models.model_data import ModelReasoningBudget
        from core.domain.models.utils import get_model_data
        from core.providers._base.provider_options import ProviderOptions

        model = Model.CLAUDE_3_5_SONNET_20241022
        model_data = get_model_data(model)

        # Mock the model data to have reasoning capabilities
        original_reasoning = model_data.reasoning
        model_data.reasoning = ModelReasoningBudget(disabled=None, low=500, medium=1000, high=2000, min=500, max=2000)

        try:
            # Create options with reasoning budget
            options = ProviderOptions(
                model=model,
                max_tokens=1000,
                reasoning_budget=500,
            )

            request = cast(
                CompletionRequest,
                anthropic_provider._build_request(
                    messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
                    options=options,
                    stream=False,
                ),
            )

            # Check that thinking is configured
            assert request.thinking is not None
            assert request.thinking.type == "enabled"
            assert request.thinking.budget_tokens == 500

            # Check that max_tokens includes the thinking budget
            assert request.max_tokens == 1000 + 500

        finally:
            # Restore original reasoning value
            model_data.reasoning = original_reasoning

    def test_build_request_without_thinking_budget(self, anthropic_provider: AnthropicProvider):
        """Test that no thinking configuration is added when reasoning budget is not set."""
        options = ProviderOptions(
            model=Model.CLAUDE_3_5_SONNET_20241022,
            max_tokens=1000,
        )

        request = cast(
            CompletionRequest,
            anthropic_provider._build_request(
                messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
                options=options,
                stream=False,
            ),
        )

        # Check that thinking is not configured
        assert request.thinking is None

        # Check that max_tokens is not modified
        assert request.max_tokens == 1000


class TestSingleStream:
    async def test_stream_data(self, httpx_mock: HTTPXMock, anthropic_provider: AnthropicProvider):
        httpx_mock.add_response(
            url="https://api.anthropic.com/v1/messages",
            stream=IteratorStream(
                [
                    b"data: ",
                    b'{"type":"message_start","message":{"id":"msg_01UCabT2dPX4DXxC3eRDEeTE","type":"message","role":"assistant","model":"claude-3-5-sonnet-20241022","content":[],"stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":32507,"output_tokens":1}}    }\n',
                    b"dat",
                    b'a: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}         }\n',
                    b'data: {"type": "ping',
                    b'"}\n',
                    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"{\\"response\\": \\"Looking"}            }\n',
                    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" at Figure 2 in the"}     }\n',
                    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" document, Claude 3."}             }\n',
                    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"5 Sonnet "}           }\n',
                    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"New) - the upgraded version -"} }\n',
                    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"%- Multilingual: 48"}     }\n',
                    b'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":").\\"}"}            }\n',
                    b'data: {"type":"content_block_stop","index":0  }\n',
                    b'data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},"usage":{"output_tokens":233}         }\n',
                    b'data: {"type":"message_stop"   }\n',
                ],
            ),
        )

        raw = RawCompletion(usage=LLMUsage(), response="")

        raw_chunks = anthropic_provider._single_stream(
            request={"messages": [{"role": "user", "content": "Hello"}]},
            output_factory=lambda x: json.loads(x),
            raw_completion=raw,
            options=ProviderOptions(
                model=Model.CLAUDE_3_5_SONNET_20241022,
                max_tokens=10,
                temperature=0,
                output_schema={},
            ),
        )

        parsed_chunks = [o async for o in raw_chunks]

        assert len(parsed_chunks) == 9
        assert parsed_chunks[-1].final_chunk
        assert parsed_chunks[-1].final_chunk.agent_output == {
            "response": "Looking at Figure 2 in the document, Claude 3.5 Sonnet New) - the upgraded version -%- Multilingual: 48).",
        }

        assert raw.usage.prompt_token_count == 32507
        assert raw.usage.completion_token_count == 233

        assert len(httpx_mock.get_requests()) == 1

    async def test_stream_data_fixture_file(self, httpx_mock: HTTPXMock, anthropic_provider: AnthropicProvider):
        httpx_mock.add_response(
            url="https://api.anthropic.com/v1/messages",
            stream=IteratorStream(
                [
                    fixture_bytes("anthropic", "stream_data_with_usage.txt"),
                ],
            ),
        )

        raw = RawCompletion(usage=LLMUsage(), response="")

        raw_chunks = anthropic_provider._single_stream(
            request={"messages": [{"role": "user", "content": "Hello"}]},
            output_factory=lambda x: json.loads(x),
            raw_completion=raw,
            options=ProviderOptions(
                model=Model.CLAUDE_3_5_SONNET_20241022,
                max_tokens=10,
                temperature=0,
                output_schema={},
            ),
        )

        parsed_chunks = [o async for o in raw_chunks]

        assert len(parsed_chunks) == 5
        assert parsed_chunks[1].delta == ' {"response": " Looking'
        assert parsed_chunks[-1].final_chunk
        assert parsed_chunks[-1].final_chunk.agent_output == {
            "response": " Looking at the human preference win rates shown in Figure 2 of the document. ",
        }

        assert len(httpx_mock.get_requests()) == 1


class TestComplete:
    async def test_complete_pdf(self, httpx_mock: HTTPXMock, anthropic_provider: AnthropicProvider):
        httpx_mock.add_response(
            url="https://api.anthropic.com/v1/messages",
            json=fixtures_json("anthropic", "completion.json"),
        )

        o = await anthropic_provider.complete(
            [
                Message(
                    role="user",
                    content=[
                        MessageContent(text="Hello"),
                        MessageContent(file=File(data="data", content_type="application/pdf")),
                    ],
                ),
            ],
            options=ProviderOptions(model=Model.CLAUDE_3_5_SONNET_20241022, max_tokens=10, temperature=0),
            output_factory=_output_factory,
        )

        assert o.agent_output
        assert o.tool_call_requests is None

        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"
        body = json.loads(request.read().decode())
        assert str(body) == str(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Hello"},
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": "data",
                                },
                            },
                        ],
                    },
                ],
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 10,
                "temperature": 0.0,
                "stream": False,
            },
        )

    async def test_complete_image(self, httpx_mock: HTTPXMock, anthropic_provider: AnthropicProvider):
        httpx_mock.add_response(
            url="https://api.anthropic.com/v1/messages",
            json=fixtures_json("anthropic", "completion.json"),
        )

        o = await anthropic_provider.complete(
            [
                Message(
                    role="user",
                    content=[
                        MessageContent(text="Hello"),
                        MessageContent(file=File(data="bla=", content_type="image/png")),
                    ],
                ),
            ],
            options=ProviderOptions(model=Model.CLAUDE_3_5_SONNET_20241022, max_tokens=10, temperature=0),
            output_factory=_output_factory,
        )

        assert o.agent_output
        assert o.tool_call_requests is None

        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"
        body = json.loads(request.read().decode())
        assert str(body) == str(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Hello"},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": "bla=",
                                },
                            },
                        ],
                    },
                ],
                "model": "claude-3-5-sonnet-20241022",
                "max_tokens": 10,
                "temperature": 0.0,
                "stream": False,
            },
        )

    @pytest.mark.parametrize("model", ANTHROPIC_PROVIDER_DATA.keys())
    async def test_complete_with_max_tokens(
        self,
        httpx_mock: HTTPXMock,
        anthropic_provider: AnthropicProvider,
        model: Model,
    ):
        httpx_mock.add_response(
            url="https://api.anthropic.com/v1/messages",
            json=fixtures_json("anthropic", "completion.json"),
        )

        o = await anthropic_provider.complete(
            [Message(role="user", content=[MessageContent(text="Hello")])],
            options=ProviderOptions(model=model, max_tokens=10, temperature=0),
            output_factory=_output_factory,
        )

        assert o.agent_output
        assert o.tool_call_requests is None

        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"
        body = json.loads(request.read().decode())
        assert body["max_tokens"] == 10

    @pytest.mark.parametrize("model", ANTHROPIC_PROVIDER_DATA.keys())
    async def test_complete_with_max_tokens_not_set(
        self,
        httpx_mock: HTTPXMock,
        anthropic_provider: AnthropicProvider,
        model: Model,
    ):
        httpx_mock.add_response(
            url="https://api.anthropic.com/v1/messages",
            json=fixtures_json("anthropic", "completion.json"),
        )

        o = await anthropic_provider.complete(
            [Message(role="user", content=[MessageContent(text="Hello")])],
            options=ProviderOptions(model=model, temperature=0),
            output_factory=_output_factory,
        )

        assert o.agent_output
        assert o.tool_call_requests is None

        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"
        body = json.loads(request.read().decode())
        model_data = get_model_data(model)
        assert (
            body["max_tokens"] == model_data.max_tokens_data.max_output_tokens or model_data.max_tokens_data.max_tokens
        )


class TestWrapSSE:
    EXAMPLE = b"""
event: message_start
data: {"type":"message_start","message":{"id":"msg_4QpJur2dWWDjF6C758FbBw5vm12BaVipnK","type":"message","role":"assistant","content":[],"model":"claude-3-opus-20240229","stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":11,"output_tokens":1}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: ping
data: {"type": "ping"}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"!"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},"usage":{"output_tokens":6}}

event: message_stop
data: {"type":"message_stop"}
"""

    async def test_wrap_sse_all_lines(self, anthropic_provider: AnthropicProvider):
        it = mock_aiter(*(self.EXAMPLE.splitlines(keepends=True)))
        wrapped = [c async for c in anthropic_provider.wrap_sse(it)]
        assert len(wrapped) == 7

    async def test_cut_event_line(self, anthropic_provider: AnthropicProvider):
        async def _basic_iterator():
            for line in self.EXAMPLE.splitlines(keepends=True):
                yield line

        wrapped = [c async for c in anthropic_provider.wrap_sse(_basic_iterator())]
        assert len(wrapped) == 7

    _SHORT_EXAMPLE = b"""event: message_start
data: hello1

event: ping

event: content_block_start
data: hello2
"""

    @pytest.mark.parametrize("cut_idx", range(len(_SHORT_EXAMPLE)))
    async def test_all_cuts(self, anthropic_provider: AnthropicProvider, cut_idx: int):
        # Check that we return the same objects no matter where we cut
        chunks = [self._SHORT_EXAMPLE[:cut_idx] + self._SHORT_EXAMPLE[cut_idx:]]
        it = mock_aiter(*chunks)
        wrapped = [c async for c in anthropic_provider.wrap_sse(it)]
        assert wrapped == [b"hello1", b"hello2"]


class TestMaxTokensExceeded:
    async def test_max_tokens_exceeded(self, anthropic_provider: AnthropicProvider, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.anthropic.com/v1/messages",
            json=fixtures_json("anthropic", "finish_reason_max_tokens_completion.json"),
        )

        with pytest.raises(MaxTokensExceededError) as e:
            await anthropic_provider.complete(
                [Message(role="user", content=[MessageContent(text="Hello")])],
                options=ProviderOptions(model=Model.CLAUDE_3_5_SONNET_20241022, max_tokens=10, temperature=0),
                output_factory=_output_factory,
            )

        assert len(httpx_mock.get_requests()) == 1
        assert e.value.args[0] == "Model returned MAX_TOKENS stop reason, the max tokens limit was exceeded."

    async def test_max_tokens_exceeded_stream(self, anthropic_provider: AnthropicProvider, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.anthropic.com/v1/messages",
            stream=IteratorStream(
                [
                    fixture_bytes("anthropic", "finish_reason_max_tokens_stream_response.txt"),
                ],
            ),
        )

        raw = RawCompletion(usage=LLMUsage(), response="")

        with pytest.raises(MaxTokensExceededError):
            async for _ in anthropic_provider._single_stream(
                request={"messages": [{"role": "user", "content": "Hello"}]},
                output_factory=_output_factory,
                raw_completion=raw,
                options=ProviderOptions(model=Model.CLAUDE_3_5_SONNET_20241022, max_tokens=10, temperature=0),
            ):
                pass


class TestPrepareCompletion:
    async def test_role_before_content(self, anthropic_provider: AnthropicProvider):
        """Test that the 'role' key appears before 'content' in the prepared request."""
        request = cast(
            CompletionRequest,
            anthropic_provider._build_request(
                messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
                options=ProviderOptions(model=Model.CLAUDE_3_5_SONNET_20241022, max_tokens=10, temperature=0),
                stream=False,
            ),
        )

        # Get the first message from the request
        message = request.model_dump()["messages"][0]

        # Get the actual order of keys in the message dictionary
        keys = list(message.keys())

        # Find the indices of 'role' and 'content' in the keys list
        role_index = keys.index("role")
        content_index = keys.index("content")

        assert role_index < content_index, (
            "The 'role' key must appear before the 'content' key in the message dictionary"
        )


class TestExtractStreamDelta:
    def _load_fixture(self, anthropic_provider: AnthropicProvider, fixture_name: str):
        raw_completion = RawCompletion(response="", usage=LLMUsage())
        streaming_context = anthropic_provider._streaming_context(raw_completion)

        fixture_data = fixtures_json(f"anthropic/{fixture_name}")["SSEs"]
        for sse in fixture_data:
            delta = anthropic_provider._extract_stream_delta(json.dumps(sse).encode())
            streaming_context.add_chunk(delta)

        final_chunk = streaming_context.complete(
            lambda raw, reasoning, tool_calls: anthropic_provider._build_structured_output(
                lambda x: x,
                raw,
                reasoning,
                tool_calls,
            ),
        )

        return streaming_context, final_chunk

    async def test_stream_with_tools(
        self,
        anthropic_provider: AnthropicProvider,
    ):
        streaming_context, final_chunk = self._load_fixture(
            anthropic_provider,
            "anthropic_with_tools_streaming_fixture.json",
        )
        # Verify the content and tool calls
        assert final_chunk.final_chunk
        assert final_chunk.final_chunk.agent_output == "I'll help you search for the latest Jazz vs Lakers game score."

        # Verify tool calls were correctly extracted
        assert final_chunk.final_chunk.tool_call_requests == [
            ToolCallRequest(
                index=1,
                id="toolu_018BjmfDhLuQh15ghjQmwaWF",
                tool_name="@search-google",
                tool_input_dict={"query": "Jazz Lakers latest game score 2025"},
            ),
        ]

        # Verify usage metrics were captured
        assert streaming_context.usage == LLMUsage(
            prompt_token_count=717,
            completion_token_count=75,
            prompt_token_count_cached=0,
        )

    async def test_stream_with_multiple_tools(
        self,
        anthropic_provider: AnthropicProvider,
    ):
        streaming_context, final_chunk = self._load_fixture(
            anthropic_provider,
            "anthropic_with_multiple_tools_streaming_fixture.json",
        )

        # Verify the content and tool calls
        assert final_chunk.final_chunk is not None
        assert (
            final_chunk.final_chunk.agent_output == "\n\nNow I'll get all the weather information using the city code:"
        )

        # Verify tool calls were correctly extracted
        assert final_chunk.final_chunk.tool_call_requests == [
            ToolCallRequest(
                index=1,
                tool_name="get_temperature",
                tool_input_dict={"city_code": "125321"},
                id="toolu_019eEEq7enPNzjU6z6X34y7i",
            ),
            ToolCallRequest(
                index=2,
                tool_name="get_rain_probability",
                tool_input_dict={"city_code": "125321"},
                id="toolu_01UgGE25XyALN9fmi7QD3Q8u",
            ),
            ToolCallRequest(
                index=3,
                tool_name="get_wind_speed",
                tool_input_dict={"city_code": "125321"},
                id="toolu_01PRcJww2rnhd3BPbVdbkuXG",
            ),
            ToolCallRequest(
                index=4,
                tool_name="get_weather_conditions",
                tool_input_dict={"city_code": "125321"},
                id="toolu_01AS6J6V1Jp6awe6vh4zf4eJ",
            ),
        ]

        # Verify usage metrics were captured
        assert streaming_context.usage == LLMUsage(
            completion_token_count=194,
            prompt_token_count=1191.0,
            prompt_token_count_cached=0,
        )

    def test_raised_error(self, anthropic_provider: AnthropicProvider):
        with pytest.raises(ServerOverloadedError):
            anthropic_provider._extract_stream_delta(
                json.dumps(
                    {
                        "type": "error",
                        "error": {"type": "overloaded_error", "message": "Server is overloaded"},
                    },
                ).encode(),
            )

    def test_content_block_start_with_tool(self, anthropic_provider: AnthropicProvider):
        delta = anthropic_provider._extract_stream_delta(
            json.dumps(
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {
                        "type": "tool_use",
                        "id": "tool_123",
                        "name": "@search-google",
                    },
                },
            ).encode(),
        )

        assert delta.delta is None
        assert delta.tool_call_requests is not None
        assert len(delta.tool_call_requests) == 1
        assert delta.tool_call_requests[0].idx == 0
        assert delta.tool_call_requests[0].id == "tool_123"
        assert delta.tool_call_requests[0].tool_name == "@search-google"
        assert delta.tool_call_requests[0].arguments == ""

    def test_content_block_delta_with_tool_input(self, anthropic_provider: AnthropicProvider):
        # Test partial JSON input
        delta = anthropic_provider._extract_stream_delta(
            json.dumps(
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": 'latest news"}',
                    },
                },
            ).encode(),
        )

        assert delta.delta is None
        assert delta.tool_call_requests is not None
        assert len(delta.tool_call_requests) == 1
        assert delta.tool_call_requests[0].idx == 0
        assert delta.tool_call_requests[0].id == ""
        assert delta.tool_call_requests[0].tool_name == ""
        assert delta.tool_call_requests[0].arguments == 'latest news"}'

    def test_message_delta_with_max_tokens(self, anthropic_provider: AnthropicProvider):
        data = anthropic_provider._extract_stream_delta(
            json.dumps(
                {
                    "type": "message_delta",
                    "delta": {
                        "stop_reason": "max_tokens",
                        "stop_sequence": None,
                    },
                    "usage": {
                        "output_tokens": 100,
                    },
                },
            ).encode(),
        )

        assert data.finish_reason == "max_context"

    def test_ping_and_stop_events(self, anthropic_provider: AnthropicProvider):
        # Test ping event
        delta = anthropic_provider._extract_stream_delta(
            json.dumps({"type": "ping"}).encode(),
        )
        assert delta.delta is None

        # Test message_stop event
        delta = anthropic_provider._extract_stream_delta(
            json.dumps({"type": "message_stop"}).encode(),
        )
        assert delta.delta is None

        # Test content_block_stop event
        delta = anthropic_provider._extract_stream_delta(
            json.dumps({"type": "content_block_stop", "index": 0}).encode(),
        )
        assert delta.delta is None

    def test_content_block_delta_with_text(self, anthropic_provider: AnthropicProvider):
        delta = anthropic_provider._extract_stream_delta(
            json.dumps(
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "text_delta",
                        "text": "Hello world",
                    },
                },
            ).encode(),
        )

        assert delta.delta is not None
        assert delta.delta == "Hello world"
        assert delta.tool_call_requests is None

    def test_content_block_start_with_text(self, anthropic_provider: AnthropicProvider):
        delta = anthropic_provider._extract_stream_delta(
            json.dumps(
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {
                        "type": "text",
                        "text": "",
                    },
                },
            ).encode(),
        )

        assert delta.delta == ""
        assert delta.tool_call_requests is None

    def test_message_delta_with_stop_reason(self, anthropic_provider: AnthropicProvider):
        delta = anthropic_provider._extract_stream_delta(
            json.dumps(
                {
                    "type": "message_delta",
                    "delta": {
                        "stop_reason": "end_turn",
                        "stop_sequence": None,
                    },
                    "usage": {
                        "output_tokens": 75,
                    },
                },
            ).encode(),
        )

        assert delta.delta is None
        assert delta.usage == LLMUsage(completion_token_count=75)


def get_dummy_provider() -> AnthropicProvider:
    config = AnthropicConfig(api_key="dummy")
    return AnthropicProvider(config=config)


def test_extract_content_str_valid() -> None:
    provider = get_dummy_provider()
    response = CompletionResponse(
        content=[ContentBlock(type="text", text="Hello world")],
        usage=Usage(input_tokens=0, output_tokens=0),
        stop_reason=None,
    )
    text = provider._extract_content_str(response)
    assert text == "Hello world"


def test_extract_content_str_empty_content() -> None:
    provider = get_dummy_provider()
    response = CompletionResponse(
        content=[],
        usage=Usage(input_tokens=0, output_tokens=0),
        stop_reason=None,
    )
    with pytest.raises(ProviderInternalError):
        provider._extract_content_str(response)


def test_extract_content_str_max_tokens() -> None:
    provider = get_dummy_provider()
    response = CompletionResponse(
        content=[ContentBlock(type="text", text="Hello world")],
        usage=Usage(input_tokens=0, output_tokens=0),
        stop_reason="max_tokens",
    )
    with pytest.raises(MaxTokensExceededError) as exc_info:
        provider._extract_content_str(response)
    assert exc_info.value.args[0] == "Model returned MAX_TOKENS stop reason, the max tokens limit was exceeded."


class TestUnknownError:
    @pytest.fixture
    def unknown_error_fn(self, anthropic_provider: AnthropicProvider):
        # Wrapper to avoid having to silence the private warning
        # and instantiate the response
        def _build_unknown_error(payload: str | dict[str, Any], status_code: int = 400):
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            res = Response(status_code=status_code, text=payload)
            return anthropic_provider._unknown_error(res)

        return _build_unknown_error

    def test_unknown_error(self, unknown_error_fn: Callable[[dict[str, Any]], ProviderError]):
        payload = {
            "error": {
                "message": "messages.1.content.1.image.source.base64: invalid base64 data",
                "type": "invalid_request_error",
            },
            "type": "error",
        }
        err = unknown_error_fn(payload)

        assert isinstance(err, ProviderBadRequestError)
        assert str(err) == "messages.1.content.1.image.source.base64: invalid base64 data"
        assert err.capture

    @pytest.mark.parametrize(
        "error_message",
        [
            "prompt is too long: 201135 tokens > 200000 maximum",
            "input length and `max_tokens` exceed context limit: 198437 + 8192 > 200000, decrease input length or `max_tokens` and try again",
        ],
    )
    def test_unknown_error_max_tokens_exceeded(
        self,
        unknown_error_fn: Callable[[dict[str, Any]], ProviderError],
        error_message: str,
    ):
        payload = {
            "error": {
                "message": error_message,
                "type": "invalid_request_error",
            },
            "type": "error",
        }
        err = unknown_error_fn(payload)

        assert isinstance(err, MaxTokensExceededError)
        assert str(err) == error_message
        assert not err.capture

    def test_image_too_large(self, unknown_error_fn: Callable[[dict[str, Any]], ProviderError]):
        payload = {
            "error": {
                "message": "messages.1.content.1.image.source.base64: image exceeds 5 MB maximum: "
                "6746560 bytes > 5242880 bytes",
                "type": "invalid_request_error",
            },
            "type": "error",
        }
        err = unknown_error_fn(payload)

        assert isinstance(err, ProviderBadRequestError)
        assert str(err) == "Image exceeds the maximum size"
        assert not err.capture

    def test_invalid_image_media_type(self, unknown_error_fn: Callable[[dict[str, Any]], ProviderError]):
        payload = {
            "error": {
                "message": "messages.0.content.1.image.source.base64.media_type: Input should be 'image/jpeg', 'image/png', 'image/gif' or 'image/webp'",
                "type": "invalid_request_error",
            },
            "type": "error",
        }

        err = unknown_error_fn(payload)

        assert isinstance(err, ProviderInvalidFileError)
        assert not err.capture


class TestExtractReasoningSteps:
    def test_extract_reasoning_steps_with_thinking_content(self, anthropic_provider: AnthropicProvider):
        """Test extraction of reasoning steps from thinking content blocks."""
        response = CompletionResponse(
            content=[
                ContentBlock(type="text", text="Here's my response."),
                ThinkingContent(
                    type="thinking",
                    thinking="Let me think about this step by step...",
                    signature="sig_123",
                ),
                ThinkingContent(
                    type="thinking",
                    thinking="Now I need to consider another approach...",
                ),
            ],
            usage=Usage(input_tokens=100, output_tokens=50),
        )

        reasoning = anthropic_provider._extract_reasoning_steps(response)
        assert (
            reasoning
            == """Let me think about this step by step...

Now I need to consider another approach..."""
        )

    def test_extract_reasoning_steps_without_thinking_content(self, anthropic_provider: AnthropicProvider):
        """Test extraction when there are no thinking content blocks."""
        response = CompletionResponse(
            content=[
                ContentBlock(type="text", text="Here's my response."),
                ToolUseContent(
                    type="tool_use",
                    id="tool_123",
                    name="test_tool",
                    input={"param": "value"},
                ),
            ],
            usage=Usage(input_tokens=100, output_tokens=50),
        )

        reasoning_steps = anthropic_provider._extract_reasoning_steps(response)

        assert reasoning_steps is None

    def test_extract_reasoning_steps_empty_content(self, anthropic_provider: AnthropicProvider):
        """Test extraction with empty content list."""
        response = CompletionResponse(
            content=[],
            usage=Usage(input_tokens=100, output_tokens=50),
        )

        reasoning_steps = anthropic_provider._extract_reasoning_steps(response)

        assert reasoning_steps is None

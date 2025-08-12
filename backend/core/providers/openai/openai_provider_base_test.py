# pyright: reportPrivateUsage=false

from typing import Any, cast

import pytest
from httpx import Response
from pydantic import BaseModel

from core.domain.message import Message, MessageContent
from core.domain.models import Model, Provider
from core.domain.tool_call import ToolCallRequest, ToolCallResult
from core.providers._base.abstract_provider import RawCompletion
from core.providers._base.httpx_provider import ParsedResponse
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import MaxTokensExceededError, ProviderInvalidFileError
from core.providers._base.provider_options import ProviderOptions
from core.providers._base.streaming_context import StreamingContext
from core.providers.openai.openai_domain import (
    ChoiceDelta,
    CompletionRequest,
    JSONResponseFormat,
    JSONSchemaResponseFormat,
    OpenAIError,
    StreamedResponse,
    StreamedToolCall,
    StreamedToolCallFunction,
    TextResponseFormat,
    Usage,
)
from core.providers.openai.openai_provider_base import OpenAIProviderBase, OpenAIProviderBaseConfig
from tests import fake_models as test_models
from tests.utils import fixtures_json


class _TestProviderConfig(OpenAIProviderBaseConfig):
    """Test implementation of OpenAIProviderBaseConfig."""

    @property
    def provider(self) -> Provider:
        return Provider.OPEN_AI


class _TestOpenAIProviderBase(OpenAIProviderBase[_TestProviderConfig]):
    """Test implementation of OpenAIProviderBase."""

    @classmethod
    def required_env_vars(cls) -> list[str]:
        return []

    @classmethod
    def name(cls) -> Provider:
        return Provider.OPEN_AI

    @classmethod
    def _default_config(cls, index: int) -> _TestProviderConfig:
        return _TestProviderConfig()

    def _request_url(self, model: Model, stream: bool) -> str:
        return "test"

    async def _request_headers(self, request: dict[str, Any], url: str, model: Model) -> dict[str, str]:
        return {}


@pytest.fixture
def base_provider() -> _TestOpenAIProviderBase:
    return _TestOpenAIProviderBase()


def test_extract_stream_delta_max_tokens_exceeded() -> None:
    """Test that length finish_reason raises MaxTokensExceededError."""
    provider = _TestOpenAIProviderBase()
    raw_completion = RawCompletion(
        response="",
        usage=LLMUsage(
            prompt_token_count=0,
            completion_token_count=0,
            model_context_window_size=0,
        ),
    )

    event = (
        StreamedResponse(
            choices=[
                ChoiceDelta(
                    index=0,
                    delta=ChoiceDelta.MessageDelta(content="test"),
                    finish_reason="length",
                ),
            ],
        )
        .model_dump_json()
        .encode()
    )

    with pytest.raises(MaxTokensExceededError) as exc_info:
        provider._extract_stream_delta(event, raw_completion, {})  # pyright: ignore[reportPrivateUsage]

    assert "maximum number of tokens was exceeded" in str(exc_info.value)


def test_extract_stream_delta_with_content() -> None:
    """Test successful extraction of content from stream delta."""
    provider = _TestOpenAIProviderBase()
    raw_completion = RawCompletion(
        response="",
        usage=LLMUsage(
            prompt_token_count=0,
            completion_token_count=0,
            model_context_window_size=0,
        ),
    )

    event = (
        StreamedResponse(
            choices=[
                ChoiceDelta(
                    index=0,
                    delta=ChoiceDelta.MessageDelta(content="test content"),
                    finish_reason=None,
                ),
            ],
        )
        .model_dump_json()
        .encode()
    )

    result = provider._extract_stream_delta(event, raw_completion, {})  # pyright: ignore[reportPrivateUsage]

    assert result.content == "test content"
    assert result.tool_calls == []


def test_extract_stream_delta_with_tool_calls() -> None:
    """Test successful extraction of tool calls from stream delta."""
    provider = _TestOpenAIProviderBase()
    raw_completion = RawCompletion(
        response="",
        usage=LLMUsage(
            prompt_token_count=0,
            completion_token_count=0,
            model_context_window_size=0,
        ),
    )

    event = (
        StreamedResponse(
            choices=[
                ChoiceDelta(
                    index=0,
                    delta=ChoiceDelta.MessageDelta(
                        content=None,
                        tool_calls=[
                            StreamedToolCall(
                                id="call_123",
                                type="function",
                                function=StreamedToolCallFunction(
                                    name="test_tool",
                                    arguments='{"arg1": "value1"}',
                                ),
                                index=0,
                            ),
                        ],
                    ),
                    finish_reason=None,
                ),
            ],
        )
        .model_dump_json()
        .encode()
    )

    result = provider._extract_stream_delta(event, raw_completion, tool_call_request_buffer={})  # pyright: ignore[reportPrivateUsage]

    assert result.content == ""
    assert result.tool_calls is not None
    assert len(result.tool_calls) == 1
    tool_call = result.tool_calls[0]
    assert tool_call.id == "call_123"
    assert tool_call.tool_name == "test_tool"
    assert tool_call.tool_input_dict == {"arg1": "value1"}


def test_extract_stream_delta_with_usage() -> None:
    """Test successful extraction of usage information from stream delta."""
    provider = _TestOpenAIProviderBase()
    raw_completion = RawCompletion(
        response="",
        usage=LLMUsage(
            prompt_token_count=0,
            completion_token_count=0,
            model_context_window_size=0,
        ),
    )

    event = (
        StreamedResponse(
            choices=[
                ChoiceDelta(
                    index=0,
                    delta=ChoiceDelta.MessageDelta(content="test"),
                    finish_reason=None,
                ),
            ],
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
            ),
        )
        .model_dump_json()
        .encode()
    )

    provider._extract_stream_delta(event, raw_completion, {})  # pyright: ignore[reportPrivateUsage]

    assert raw_completion.usage is not None
    assert raw_completion.usage.prompt_token_count == 10
    assert raw_completion.usage.completion_token_count == 5


def test_extract_stream_delta_empty_choices() -> None:
    """Test handling of response with empty choices."""
    provider = _TestOpenAIProviderBase()
    raw_completion = RawCompletion(
        response="",
        usage=LLMUsage(
            prompt_token_count=0,
            completion_token_count=0,
            model_context_window_size=0,
        ),
    )

    event = StreamedResponse(choices=[]).model_dump_json().encode()

    result = provider._extract_stream_delta(event, raw_completion, {})  # pyright: ignore[reportPrivateUsage]

    assert result == ParsedResponse(content="")


def test_extract_stream_delta_with_incomplete_tool_call() -> None:
    """Test that incomplete JSON in tool call arguments results in no tool call being added."""
    provider = _TestOpenAIProviderBase()
    raw_completion = RawCompletion(
        response="",
        usage=LLMUsage(
            prompt_token_count=0,
            completion_token_count=0,
            model_context_window_size=0,
        ),
    )

    # Create an event with a tool call that has incomplete JSON (missing closing brace)
    event = (
        StreamedResponse(
            choices=[
                ChoiceDelta(
                    index=0,
                    delta=ChoiceDelta.MessageDelta(
                        content=None,
                        tool_calls=[
                            StreamedToolCall(
                                id="call_456",
                                type="function",
                                function=StreamedToolCallFunction(
                                    name="incomplete_tool",
                                    arguments='{"arg1": "value1"',
                                ),
                                index=0,
                            ),
                        ],
                    ),
                    finish_reason=None,
                ),
            ],
        )
        .model_dump_json()
        .encode()
    )

    result = provider._extract_stream_delta(event, raw_completion, {})  # pyright: ignore[reportPrivateUsage]

    assert result.content == ""
    assert result.tool_calls == []


def test_extract_stream_delta_consecutive_fragments() -> None:
    """Test that multiple consecutive SSE events with partial JSON fragments for a tool call are correctly accumulated to form a valid JSON tool call."""
    provider = _TestOpenAIProviderBase()
    raw_completion = RawCompletion(
        response="",
        usage=LLMUsage(
            prompt_token_count=0,
            completion_token_count=0,
            model_context_window_size=0,
        ),
    )

    # Fragments that when concatenated form a valid JSON: {"query": "latest Jazz Lakers score February 2025"}
    fragments = [
        '{"',
        "query",
        '":"',
        "latest",
        " Jazz",
        " Lakers",
        " score",
        " February",
        " 202",
        "5",
        '"}',
    ]

    stream_context = StreamingContext(RawCompletion(response="", usage=LLMUsage()), json=True)

    # Process all fragments except the last one; these should not yield a complete tool call
    for fragment in fragments[:-1]:
        event = (
            StreamedResponse(
                choices=[
                    ChoiceDelta(
                        index=0,
                        delta=ChoiceDelta.MessageDelta(
                            content=None,
                            tool_calls=[
                                StreamedToolCall(
                                    id="complex_call",
                                    type="function",
                                    function=StreamedToolCallFunction(
                                        name="complex_tool",
                                        arguments=fragment,
                                    ),
                                    index=0,
                                ),
                            ],
                        ),
                        finish_reason=None,
                    ),
                ],
            )
            .model_dump_json()
            .encode()
        )
        result = provider._extract_stream_delta(event, raw_completion, stream_context.tool_call_request_buffer)  # pyright: ignore[reportPrivateUsage]
        # Before the final fragment, no complete tool call should be formed
        assert result.tool_calls == []

    # Process the final fragment which should complete the JSON
    final_fragment = fragments[-1]
    final_event = (
        StreamedResponse(
            choices=[
                ChoiceDelta(
                    index=0,
                    delta=ChoiceDelta.MessageDelta(
                        content=None,
                        tool_calls=[
                            StreamedToolCall(
                                id="complex_call",
                                type="function",
                                function=StreamedToolCallFunction(
                                    name="complex_tool",
                                    arguments=final_fragment,
                                ),
                                index=0,
                            ),
                        ],
                    ),
                    finish_reason=None,
                ),
            ],
        )
        .model_dump_json()
        .encode()
    )
    final_result = provider._extract_stream_delta(final_event, raw_completion, stream_context.tool_call_request_buffer)  # pyright: ignore[reportPrivateUsage]

    # Now, the accumulated fragments should form a valid JSON tool call
    assert final_result.tool_calls is not None
    assert len(final_result.tool_calls) == 1
    tool_call = final_result.tool_calls[0]
    assert tool_call.id == "complex_call"
    assert tool_call.tool_name == "complex_tool"
    assert tool_call.tool_input_dict == {"query": "latest Jazz Lakers score February 2025"}


def test_extract_stream_delta_from_fixture() -> None:
    """Test processing streaming tool call events from a fixture file and verify aggregated tool calls."""
    import json

    provider = _TestOpenAIProviderBase()
    raw_completion = RawCompletion(
        response="",
        usage=LLMUsage(
            prompt_token_count=0,
            completion_token_count=0,
            model_context_window_size=0,
        ),
    )

    data = fixtures_json("openai", "stream_with_tools.json")

    # Feed each event sequentially to the provider

    tool_calls: list[ToolCallRequest] = []

    stream_context = StreamingContext(RawCompletion(response="", usage=LLMUsage()), json=True)

    for event in data["events"]:
        event_bytes = json.dumps(event).encode("utf-8")
        response = provider._extract_stream_delta(event_bytes, raw_completion, stream_context.tool_call_request_buffer)  # pyright: ignore[reportPrivateUsage]
        tool_calls.extend(response.tool_calls or [])

    assert tool_calls == [
        ToolCallRequest(
            tool_name="get_temperature",
            tool_input_dict={"city_code": "125321"},
            id="call_AU0Fw2imWtuWlmaLHXnwkZCQ",
        ),
        ToolCallRequest(
            tool_name="get_rain_probability",
            tool_input_dict={"city_code": "125321"},
            id="call_VtkV4ZpNh3nHxS84JnCiriVj",
        ),
        ToolCallRequest(
            tool_name="get_wind_speed",
            tool_input_dict={"city_code": "125321"},
            id="call_wfkYlsz09dYJvzoXn7spvgpy",
        ),
        ToolCallRequest(
            tool_name="get_weather_conditions",
            tool_input_dict={"city_code": "125321"},
            id="call_3oHEEsy8LFQectXu7wTSOiPx",
        ),
    ]


@pytest.mark.parametrize(
    ("messages", "expected_token_count"),
    [
        (
            # Single simple text message
            [{"role": "user", "content": "Hello, world!"}],
            # 3 (boilerplate) + (4 (message boilerplate) + 4 (tokens in "Hello, world!")) = 11
            11,
        ),
        (
            # Multiple text messages
            [
                {"role": "user", "content": "Hello, world!"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            # 3 (boilerplate) + 2 * (4 (message boilerplate)) + 4 (tokens in "Hello, world!") + 3 (tokens in "Hi there!") = 18
            18,
        ),
        (
            # Empty message list
            [],
            # 3 (boilerplate only)
            3,
        ),
        (
            # Message with empty content
            [{"role": "user", "content": ""}],
            # 3 (boilerplate) + 4 (message boilerplate) + 0 (tokens in empty content) = 7
            7,
        ),
        (
            # Message with tool call
            [{"role": "tool", "tool_call_id": "tc_valid", "content": "Hello"}],
            8,  # 3 (boilerplate) + 4 (message boilerplate) + 1 (tool call)
        ),
        (
            # Message with tool call and other messages
            [
                {"role": "tool", "tool_call_id": "tc_valid", "content": "Hello"},
                {"role": "user", "content": "Hello, world!"},
            ],
            16,  # 3 (boilerplate) + 4 (message boilerplate) + 1 (tool call) + 4 (message boilerplate) + 4 (tokens in "Hello, world!")
        ),
    ],
)
def test_compute_prompt_token_count(messages: list[dict[str, Any]], expected_token_count: int) -> None:
    """Test token count calculation for different message configurations."""
    provider = _TestOpenAIProviderBase()
    model = Model.GPT_4O_2024_08_06

    result = provider._compute_prompt_token_count(messages, model)  # pyright: ignore[reportPrivateUsage]
    # This is a high-level smoke test that '_compute_prompt_token_count' does not raise and return a value
    assert result == expected_token_count


class TestBuildRequest:
    async def test_with_tool_calls(self, base_provider: _TestOpenAIProviderBase):
        messages = [
            Message(
                role="system",
                content=[
                    MessageContent(
                        text="Be concise, reply with one sentence.Use the `get_lat_lng` tool to get the latitude and longitude of the locations, then use the `get_weather` tool to get the weather.",
                    ),
                ],
            ),
            Message(
                role="user",
                content=[
                    MessageContent(
                        text="What is the weather like in London?",
                    ),
                ],
            ),
            Message(
                role="assistant",
                content=[
                    MessageContent(
                        tool_call_request=ToolCallRequest(
                            tool_name="get_lat_lng",
                            tool_input_dict={"location_description": "London"},
                            id="call_ucYQgwUMFhWu2e91vA9FgRCj",
                        ),
                    ),
                ],
            ),
            Message(
                role="user",
                content=[
                    MessageContent(
                        tool_call_result=ToolCallResult(
                            tool_name="",
                            tool_input_dict={},
                            id="call_ucYQgwUMFhWu2e91vA9FgRCj",
                            result='{"lat":51.5074456,"lng":-0.1277653}',
                        ),
                    ),
                ],
            ),
        ]

        req = base_provider._build_request(
            [m.to_deprecated() for m in messages],
            ProviderOptions(model=Model.GPT_4O_2024_08_06),
            stream=False,
        )
        assert req.model_dump(exclude_none=True)["messages"] == [
            {
                "role": "system",
                "content": "Be concise, reply with one sentence.Use the `get_lat_lng` tool to get the latitude and longitude of the locations, then use the `get_weather` tool to get the weather.",
            },
            {"role": "user", "content": "What is the weather like in London?"},
            {
                "content": [],
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "arguments": '{"location_description": "London"}',
                            "name": "get_lat_lng",
                        },
                        "id": "call_ucYQgwUMFhWu2e91vA9FgRCj",
                        "type": "function",
                    },
                ],
            },
            {
                "content": '{"lat":51.5074456,"lng":-0.1277653}',
                "role": "tool",
                "tool_call_id": "call_ucYQgwUMFhWu2e91vA9FgRCj",
            },
        ]

    async def test_with_unsupported_temperature(self, base_provider: _TestOpenAIProviderBase):
        messages = [
            Message(
                role="system",
                content=[MessageContent(text="Be concise, reply with one sentence.")],
            ),
        ]
        req = cast(
            CompletionRequest,
            base_provider._build_request(
                [m.to_deprecated() for m in messages],
                # O3 mini does not support temperature
                ProviderOptions(model=Model.O3_MINI_2025_01_31, temperature=0.5),
                stream=False,
            ),
        )
        assert req.temperature is None


def test_invalid_request_error_too_many_images() -> None:
    """Test that 'Too many images in request' error returns ProviderInvalidFileError."""
    provider = _TestOpenAIProviderBase()

    # Create a mock OpenAI error payload
    error_payload = OpenAIError(
        error=OpenAIError.Payload(
            code="invalid_request_error",
            message="Too many images in request. Only 5 images are allowed per request.",
            type="invalid_request_error",
            param="messages",
        ),
    )

    # Create a mock HTTP response
    response = Response(
        status_code=400,
        headers={},
        content=b'{"error": {"code": "invalid_request_error", "message": "Too many images in request. Only 5 images are allowed per request.", "type": "invalid_request_error", "param": "messages"}}',
    )

    # Test the _invalid_request_error method
    result = provider._invalid_request_error(error_payload, response)  # pyright: ignore[reportPrivateUsage]

    # Verify it returns ProviderInvalidFileError
    assert isinstance(result, ProviderInvalidFileError)
    assert "Too many images in request" in str(result)


class TestResponseFormat:
    @pytest.fixture
    def base_options(self) -> ProviderOptions:
        return ProviderOptions(
            model=Model.GPT_4O_2024_08_06,
            output_schema={"type": "object"},
            structured_generation=True,
        )

    @pytest.mark.parametrize(
        ("supports_structured_output", "supports_json_mode", "expected_cls"),
        [
            pytest.param(True, True, JSONSchemaResponseFormat, id="structured_output_json_mode"),
            pytest.param(True, False, JSONSchemaResponseFormat, id="json_mode_unsupported"),
            pytest.param(False, True, JSONResponseFormat, id="json_mode"),
            pytest.param(False, False, TextResponseFormat, id="text_mode"),
        ],
    )
    async def test_with_structured_output(
        self,
        base_provider: _TestOpenAIProviderBase,
        base_options: ProviderOptions,
        supports_structured_output: bool,
        supports_json_mode: bool,
        expected_cls: type[BaseModel],
    ):
        format = base_provider._response_format(
            options=base_options,
            supports=test_models.fake_model_data(
                supports_structured_output=supports_structured_output,
                supports_json_mode=supports_json_mode,
            ),
        )
        assert isinstance(format, expected_cls)

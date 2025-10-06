# pyright: reportPrivateUsage=false
import json
import os
import unittest
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest
from httpx import Response
from pytest_httpx import HTTPXMock, IteratorStream

from core.domain.file import File
from core.domain.message import Message, MessageContent, MessageDeprecated
from core.domain.models import Model, Provider
from core.domain.models.model_data import FinalModelData, MaxTokensData
from core.domain.tool import Tool
from core.domain.tool_call import ToolCallRequest
from core.providers._base.abstract_provider import RawCompletion
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import (
    MaxTokensExceededError,
    MissingModelError,
    ProviderInternalError,
    ProviderInvalidFileError,
    UnknownProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers.fireworks.fireworks_domain import (
    Choice,
    ChoiceMessage,
    CompletionRequest,
    CompletionResponse,
    FireworksToolCall,
    FireworksToolCallFunction,
    Usage,
)
from core.providers.fireworks.fireworks_provider import FireworksAIProvider, FireworksConfig
from tests import fake_models as test_models
from tests.utils import fixture_bytes, fixtures_json


@pytest.fixture(scope="session")
def patch_fireworks_env_vars():
    with patch.dict(
        "os.environ",
        {
            "FIREWORKS_API_KEY": "worfklowai",
            "FIREWORKS_API_URL": "https://api.fireworks.ai/inference/v1/chat/completions",
        },
    ):
        yield


@pytest.fixture
def fireworks_provider():
    provider = FireworksAIProvider(
        config=FireworksConfig(
            provider=Provider.FIREWORKS,
            api_key=os.getenv("FIREWORKS_API_KEY", "test"),
            url=os.getenv("FIREWORKS_API_URL", "https://api.fireworks.ai/inference/v1/chat/completions"),
        ),
    )
    return provider


def _output_factory(x: str) -> Any:
    return x


class TestValues(unittest.TestCase):
    def test_name(self):
        """Test the name method returns the correct Provider enum."""
        assert FireworksAIProvider.name() == Provider.FIREWORKS

    def test_required_env_vars(self):
        """Test the required_env_vars method returns the correct environment variables."""
        expected_vars = ["FIREWORKS_API_KEY"]
        assert FireworksAIProvider.required_env_vars() == expected_vars

    def test_supports_model(self):
        """Test the supports_model method returns True for a supported model
        and False for an unsupported model"""
        provider = FireworksAIProvider()
        assert provider.supports_model(Model.LLAMA_3_3_70B)
        assert not provider.supports_model(Model.CLAUDE_3_OPUS_20240229)


class TestBuildRequest:
    def test_build_request(self, fireworks_provider: FireworksAIProvider):
        request = cast(
            CompletionRequest,
            fireworks_provider._build_request(  # pyright: ignore [reportPrivateUsage]
                messages=[
                    MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="Hello 1"),
                    MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello"),
                ],
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
                stream=False,
            ),
        )
        # The HTTPx provider does not include None values in the request body, so we need to exclude them
        assert request.model_dump(include={"messages"}, exclude_none=True)["messages"] == [
            {
                "role": "system",
                "content": "Hello 1",
            },
            {
                "role": "user",
                "content": "Hello",
            },
        ]
        assert request.temperature == 0
        assert request.max_tokens == 10

    # TODO[max-tokens]: Re-add test

    def test_build_request_with_max_output_tokens(self, fireworks_provider: FireworksAIProvider):
        request = cast(
            CompletionRequest,
            fireworks_provider._build_request(  # pyright: ignore [reportPrivateUsage]
                messages=[
                    MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content="Hello 1"),
                    MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello"),
                ],
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, temperature=0),
                stream=False,
            ),
        )
        # The HTTPx provider does not include None values in the request body, so we need to exclude them
        assert request.model_dump(include={"messages"}, exclude_none=True)["messages"] == [
            {
                "role": "system",
                "content": "Hello 1",
            },
            {
                "role": "user",
                "content": "Hello",
            },
        ]
        assert request.temperature == 0
        assert request.max_tokens is not None
        # TODO[max-tokens]: Re-add test
        # if model_data.max_tokens_data.max_output_tokens:
        #     assert request.max_tokens == model_data.max_tokens_data.max_output_tokens
        # elif model_data.max_tokens_data.max_tokens:
        #     assert request.max_tokens == model_data.max_tokens_data.max_tokens


def mock_fireworks_stream(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.fireworks.ai/inference/v1/chat/completions",
        stream=IteratorStream(
            [
                fixture_bytes("fireworks", "stream_data_with_usage.txt"),
            ],
        ),
    )


class TestSingleStream:
    @patch("core.providers.fireworks.fireworks_provider.get_model_data")
    async def test_stream_data(self, get_model_data_mock: Mock, httpx_mock: HTTPXMock):
        get_model_data_mock.return_value = FinalModelData.model_construct(
            max_tokens_data=MaxTokensData(max_output_tokens=1234, max_tokens=1235, source=""),
        )
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            stream=IteratorStream([fixture_bytes("fireworks", "stream_data_with_usage.txt")]),
        )

        provider = FireworksAIProvider()
        raw = RawCompletion(usage=LLMUsage(), response="")

        raw_chunks = provider._single_stream(  # pyright: ignore [reportPrivateUsage]
            request={"messages": [{"role": "user", "content": "Hello"}]},
            output_factory=_output_factory,
            raw_completion=raw,
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0, output_schema={}),
        )

        parsed_chunks = [o async for o in raw_chunks]
        assert not any(chunk.is_empty() for chunk in parsed_chunks)

        assert len(parsed_chunks) == 3

        req = httpx_mock.get_request(url="https://api.fireworks.ai/inference/v1/chat/completions")
        assert req

    async def test_max_message_length(self, httpx_mock: HTTPXMock, fireworks_provider: FireworksAIProvider):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            status_code=400,
            json={"error": {"code": "string_above_max_length", "message": "The string is too long"}},
        )
        raw = RawCompletion(usage=LLMUsage(), response="")

        with pytest.raises(MaxTokensExceededError) as e:
            raw_chunks = fireworks_provider._single_stream(  # pyright: ignore [reportPrivateUsage]
                request={"messages": [{"role": "user", "content": "Hello"}]},
                output_factory=_output_factory,
                raw_completion=raw,
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
            )
            [o async for o in raw_chunks]
        assert e.value.store_task_run

    async def test_context_length_exceeded(self, httpx_mock: HTTPXMock, fireworks_provider: FireworksAIProvider):
        """Test the full loop when streaming that we raise an error on context_length_exceeded"""
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            status_code=400,
            json={"error": {"code": "context_length_exceeded", "message": "Max token exceeded"}},
        )
        raw = RawCompletion(usage=LLMUsage(), response="")

        with pytest.raises(MaxTokensExceededError) as e:
            raw_chunks = fireworks_provider._single_stream(  # pyright: ignore [reportPrivateUsage]
                request={"messages": [{"role": "user", "content": "Hello"}]},
                output_factory=_output_factory,
                raw_completion=raw,
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
            )
            [o async for o in raw_chunks]
        assert e.value.store_task_run


class TestStream:
    # Tests overlap with single stream above but check the entire structure
    @patch("core.providers.fireworks.fireworks_provider.get_model_data")
    async def test_stream(self, get_model_data_mock: Mock, httpx_mock: HTTPXMock):
        get_model_data_mock.return_value = FinalModelData.model_construct(
            max_tokens_data=MaxTokensData(max_output_tokens=1234, max_tokens=1235, source=""),
            supports_structured_output=True,
        )
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            stream=IteratorStream(
                [
                    fixture_bytes("fireworks", "stream_data_with_usage.txt"),
                ],
            ),
        )

        provider = FireworksAIProvider()

        streamer = provider.stream(
            [Message.with_text("Hello")],
            options=ProviderOptions(model=Model.DEEPSEEK_V3_0324, temperature=0, output_schema={"type": "object"}),
            output_factory=_output_factory,
        )
        chunks = [chunk async for chunk in streamer]
        assert len(chunks) == 3

        # Not sure why the pyright in the CI reports an error here
        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"  # pyright: ignore reportUnknownMemberType
        body = json.loads(request.read().decode())
        assert body == {
            "context_length_exceeded_behavior": "truncate",
            "max_tokens": 1234,
            "model": "accounts/fireworks/models/deepseek-v3-0324",
            "messages": [
                {
                    "content": "Hello",
                    "role": "user",
                },
            ],
            "response_format": {
                "schema": {"type": "object"},
                "type": "json_object",
            },
            "stream": True,
            "temperature": 0.0,
        }

    async def test_stream_error(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            status_code=400,
            json={"error": {"message": "blabla"}},
        )

        provider = FireworksAIProvider()

        streamer = provider.stream(
            [Message.with_text("Hello")],
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
            output_factory=_output_factory,
        )
        with pytest.raises(UnknownProviderError) as e:
            [chunk async for chunk in streamer]

        assert e.value.capture
        assert str(e.value) == "blabla"


class TestComplete:
    # Tests overlap with single stream above but check the entire structure
    async def test_complete_images(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            json=fixtures_json("fireworks", "completion.json"),
        )

        provider = FireworksAIProvider()

        o = await provider.complete(
            [
                Message(
                    role="user",
                    content=[
                        MessageContent(text="Hello"),
                        MessageContent(file=File(data="data", content_type="image/png")),
                    ],
                ),
            ],
            options=ProviderOptions(
                model=Model.LLAMA_3_2_90B_VISION_PREVIEW,
                max_tokens=10,
                temperature=0,
                output_schema={"type": "object"},
            ),
            output_factory=_output_factory,
        )
        assert o.agent_output
        assert o.tool_call_requests is None
        # Not sure why the pyright in the CI reports an error here
        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"  # pyright: ignore reportUnknownMemberType
        body = json.loads(request.read().decode())
        assert body == {
            "context_length_exceeded_behavior": "truncate",
            "max_tokens": 10,
            "model": "accounts/fireworks/models/llama-v3p2-90b-vision-instruct",
            "messages": [
                {
                    "content": [
                        {
                            "text": "Hello",
                            "type": "text",
                        },
                        {
                            "image_url": {
                                "url": "data:image/png;base64,data#transform=inline",
                            },
                            "type": "image_url",
                        },
                    ],
                    "role": "user",
                },
            ],
            "response_format": {
                "type": "json_object",
                "schema": {"type": "object"},
            },
            "stream": False,
            "temperature": 0.0,
        }

    async def test_complete_500(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            status_code=500,
            text="Internal Server Error",
        )

        provider = FireworksAIProvider()

        with pytest.raises(ProviderInternalError) as e:
            await provider.complete(
                [Message.with_text("Hello")],
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
                output_factory=_output_factory,
            )

        details = e.value.serialized().details
        assert details
        assert details.get("provider_error") == {"raw": "Internal Server Error"}

    async def test_complete_structured(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            json=fixtures_json("fireworks", "completion.json"),
        )
        provider = FireworksAIProvider()

        o = await provider.complete(
            [
                Message(
                    role="user",
                    content=[
                        MessageContent(text="Hello"),
                        MessageContent(file=File(data="data", content_type="image/png")),
                    ],
                ),
            ],
            options=ProviderOptions(
                model=Model.LLAMA_3_3_70B,
                max_tokens=10,
                temperature=0,
                task_name="hello",
                structured_generation=True,
                output_schema={"type": "object"},
            ),
            output_factory=_output_factory,
        )
        assert o.agent_output
        assert o.tool_call_requests is None

        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"  # pyright: ignore reportUnknownMemberType
        body = json.loads(request.read().decode())
        assert body == {
            "context_length_exceeded_behavior": "truncate",
            "max_tokens": 10,
            "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
            "messages": [
                {
                    "content": [
                        {
                            "text": "Hello",
                            "type": "text",
                        },
                        {
                            "image_url": {
                                "url": "data:image/png;base64,data#transform=inline",
                            },
                            "type": "image_url",
                        },
                    ],
                    "role": "user",
                },
            ],
            "response_format": {
                "type": "json_object",
                "schema": {"type": "object"},
            },
            "stream": False,
            "temperature": 0.0,
        }

    async def test_complete_text_only(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            json=fixtures_json("fireworks", "completion.json"),
        )

        provider = FireworksAIProvider()

        o = await provider.complete(
            [Message.with_text("Hello")],
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0, output_schema=None),
            output_factory=_output_factory,
        )
        assert isinstance(o.agent_output, str)
        assert o.tool_call_requests is None

        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"  # pyright: ignore reportUnknownMemberType
        body = json.loads(request.read().decode())
        assert body["response_format"]["type"] == "text"

    @patch("core.providers.fireworks.fireworks_provider.get_model_data")
    @pytest.mark.parametrize(
        ("max_output_tokens", "option_max_tokens", "expected"),
        [(None, None, 1234), (1235, None, 1235), (1235, 1236, 1236)],
    )
    async def test_complete_with_max_tokens(
        self,
        get_model_data_mock: Mock,
        httpx_mock: HTTPXMock,
        fireworks_provider: FireworksAIProvider,
        max_output_tokens: int | None,
        option_max_tokens: int | None,
        expected: int,
    ):
        """Check that the max tokens is correctly set in the request based on the model data, by order of priority
        - option_max_tokens
        - model data max_output_tokens
        - model data max_tokens
        Also check that we send "truncate".
        This test covers streaming and non streaming requests since the build request is called in the same way.
        """
        get_model_data_mock.return_value = FinalModelData.model_construct(
            max_tokens_data=MaxTokensData(max_output_tokens=max_output_tokens, max_tokens=1234, source=""),
        )

        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            json=fixtures_json("fireworks", "completion.json"),
        )

        o = await fireworks_provider.complete(
            [
                Message(
                    role="user",
                    content=[
                        MessageContent(text="Hello"),
                        MessageContent(file=File(data="data", content_type="image/png")),
                    ],
                ),
            ],
            options=ProviderOptions(
                model=Model.LLAMA_3_3_70B,
                max_tokens=option_max_tokens,
                temperature=0,
                task_name="hello",
                structured_generation=True,
                output_schema={"type": "object"},
            ),
            output_factory=_output_factory,
        )
        assert o.agent_output

        request = httpx_mock.get_requests()[0]
        assert request
        assert request.method == "POST"
        body = json.loads(request.read().decode())
        assert body["context_length_exceeded_behavior"] == "truncate"
        assert body["max_tokens"] == expected

    async def test_missing_model(self, httpx_mock: HTTPXMock, fireworks_provider: FireworksAIProvider):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            status_code=400,
            json={"error": "model not found, inaccessible, and/or not deployed"},
        )
        with pytest.raises(MissingModelError):
            await fireworks_provider.complete(
                [Message.with_text("Hello")],
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
                output_factory=_output_factory,
            )


class TestCheckValid:
    async def test_valid(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            json={
                "id": "chatcmpl-91gL0PXUwQajck2pIp284pR9o7yVo",
                "object": "chat.completion",
                "created": 1710188102,
                "model": "accounts/fireworks/models/llama-v3p3-70b-instruct",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "index": 0,
                        "message": {"role": "assistant", "content": "{}"},
                    },
                ],
                "usage": {"prompt_tokens": 35, "completion_tokens": 109, "total_tokens": 144},
                "system_fingerprint": "fp_8abb16fa4e",
            },
        )

        provider = FireworksAIProvider()
        assert await provider.check_valid()

        request = httpx_mock.get_requests()[0]
        body = json.loads(request.read().decode())
        assert body["messages"] == [{"content": "Respond with an empty json", "role": "user"}]


class TestExtractContent:
    def test_extract_content(self, fireworks_provider: FireworksAIProvider):
        response = CompletionResponse.model_validate_json(
            fixture_bytes("fireworks", "r1_completion_with_reasoning.json"),
        )
        content = fireworks_provider._extract_content_str(response)
        assert (
            content
            == '\n\n```json\n{\n  "greeting": "The Azure Whisper",\n  "content": "On a cloudless morning, young Mira gazed upward, mesmerized by the endless blue canvas above. \'Why is the sky blue?\' she asked her grandmother, who tended sunflowers nearby. Her grandmother smiled, recalling an old tale. \'Long ago, the sky was colorless. A lonely star wept tears of sapphire, staining the heavens to remind us of its sorrow. But over time, the stars found joy again—scattering laughter as sunlight through the blue. Now, the sky sings their story.\' Mira squinted, imagining starry tears and shimmering light. From that day, the sky felt less like emptiness and more like a secret kept between the stars and her.",\n  "moral": "Even the simplest wonders hold stories waiting to be imagined."\n}\n```'
        )

    def test_extract_reasoning_steps(self, fireworks_provider: FireworksAIProvider):
        response = CompletionResponse.model_validate_json(
            fixture_bytes("fireworks", "r1_completion_with_reasoning.json"),
        )
        reasoning_steps = fireworks_provider._extract_reasoning_steps(response)
        assert (
            reasoning_steps
            == "Okay, let's see. The user asked for a short story based on the fact that the sky is blue. \n"
        )


class TestExtractStreamDelta:
    def test_extract_stream_delta(self, fireworks_provider: FireworksAIProvider):
        raw_completion = RawCompletion(response="", usage=LLMUsage())
        delta = fireworks_provider._extract_stream_delta(
            b'{"id":"39c134cd-a781-4843-bdd6-e3db43259273","object":"chat.completion.chunk","created":1734400681,"model":"accounts/fireworks/models/llama-v3p1-8b-instruct","choices":[{"index":0,"delta":{"content":"\\"greeting\\": \\"Hello James!\\"\\n}"},"finish_reason":null}],"usage":null}',
        )
        assert delta.delta == '"greeting": "Hello James!"\n}'
        assert raw_completion.usage == LLMUsage(prompt_token_count=None, completion_token_count=None)

    def test_extract_stream_delta_content_null(self, fireworks_provider: FireworksAIProvider):
        delta = fireworks_provider._extract_stream_delta(
            b'{"id":"39c134cd-a781-4843-bdd6-e3db43259273","object":"chat.completion.chunk","created":1734400681,"model":"accounts/fireworks/models/llama-v3p1-8b-instruct","choices":[{"index":0,"delta":{"content":null},"finish_reason":"stop"}],"usage":{"prompt_tokens":24,"total_tokens":32,"completion_tokens":8}}',
        )
        assert delta.delta is None
        assert delta.usage == LLMUsage(prompt_token_count=24, completion_token_count=8)

    def test_extract_stream_delta_with_tool_calls(self) -> None:
        provider = FireworksAIProvider(config=FireworksConfig(provider=Provider.FIREWORKS, api_key="test"))

        # Test complete tool call
        sse_event = b'{"id":"test-id","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"test_id_1","type":"function","function":{"name":"test_tool","arguments":"{\\"key\\": \\"value\\"}"}}]}}]}'
        parsed = provider._extract_stream_delta(sse_event)
        assert parsed.tool_call_requests is not None
        assert len(parsed.tool_call_requests) == 1
        assert parsed.tool_call_requests[0].id == "test_id_1"
        assert parsed.tool_call_requests[0].tool_name == "test_tool"
        assert parsed.tool_call_requests[0].arguments == '{"key": "value"}'


class TestRequiresDownloadingFile:
    @pytest.mark.parametrize(
        "file",
        [
            File(url="http://localhost/hello", content_type="image/png"),
            File(url="http://localhost/hello", content_type=None, format="image"),
        ],
    )
    def test_requires_downloading_file(self, file: File):
        assert FireworksAIProvider.requires_downloading_file(file, Model.LLAMA_3_3_70B)


class TestMaxTokensExceeded:
    """Occurs when the generation goes beyond the max tokens"""

    async def test_max_tokens_exceeded(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            json=fixtures_json("fireworks", "finish_reason_length_completion.json"),
        )
        provider = FireworksAIProvider()
        with pytest.raises(MaxTokensExceededError) as e:
            await provider.complete(
                [Message.with_text("Hello")],
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
                output_factory=_output_factory,
            )
        assert e.value.store_task_run is True
        assert (
            e.value.args[0]
            == "Model returned a response with a LENGTH finish reason, meaning the maximum number of tokens was exceeded."
        )

    async def test_max_tokens_exceeded_stream(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.fireworks.ai/inference/v1/chat/completions",
            stream=IteratorStream(
                [
                    fixture_bytes("fireworks", "finish_reason_length_stream_completion.txt"),
                ],
            ),
        )
        provider = FireworksAIProvider()
        with pytest.raises(MaxTokensExceededError) as e:
            async for _ in provider.stream(
                [Message.with_text("Hello")],
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
                output_factory=_output_factory,
            ):
                pass
        assert e.value.store_task_run is True


class TestPrepareCompletion:
    async def test_role_before_content(self, fireworks_provider: FireworksAIProvider):
        """Test that the 'role' key appears before 'content' in the prepared request."""
        request = fireworks_provider._build_request(
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
            stream=False,
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


class TestFireworksAIProviderNativeToolCalls:
    def test_build_request_with_tool_calls(self) -> None:
        provider = FireworksAIProvider(config=FireworksConfig(provider=Provider.FIREWORKS, api_key="test"))
        messages = [
            MessageDeprecated(
                role=MessageDeprecated.Role.USER,
                content="Test content",
                tool_call_requests=[
                    ToolCallRequest(
                        id="test_id_1",
                        tool_name="test_tool",
                        tool_input_dict={"key": "value"},
                    ),
                ],
            ),
        ]
        options = ProviderOptions(
            task_name="test",
            model=Model.LLAMA_3_3_70B,
            enabled_tools=[
                Tool(
                    name="test_tool",
                    description="Test tool",
                    input_schema={"type": "object", "properties": {"key": {"type": "string"}}},
                    output_schema={"type": "object", "properties": {"result": {"type": "string"}}},
                ),
            ],
        )

        request = provider._build_request(messages, options, stream=False)
        assert isinstance(request, CompletionRequest)
        assert request.tools is not None
        assert len(request.tools) == 1
        assert request.tools[0].type == "function"
        assert request.tools[0].function.name == "test_tool"
        assert request.tools[0].function.description == "Test tool"
        assert request.tools[0].function.parameters == {"type": "object", "properties": {"key": {"type": "string"}}}

    def test_extract_native_tool_calls(self) -> None:
        response = CompletionResponse(
            id="test",
            choices=[
                Choice(
                    message=ChoiceMessage(
                        role="assistant",
                        content=None,
                        tool_calls=[
                            FireworksToolCall(
                                id="test_id_1",
                                type="function",
                                function=FireworksToolCallFunction(
                                    name="test_tool",
                                    arguments='{"key": "value"}',
                                ),
                            ),
                        ],
                    ),
                ),
            ],
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

        provider = FireworksAIProvider(config=FireworksConfig(provider=Provider.FIREWORKS, api_key="test"))
        tool_calls = provider._extract_native_tool_calls(response)
        assert len(tool_calls) == 1
        assert tool_calls[0].id == "test_id_1"
        assert tool_calls[0].tool_name == "test_tool"
        assert tool_calls[0].tool_input_dict == {"key": "value"}

    def test_extract_content_str_with_tool_calls(self) -> None:
        provider = FireworksAIProvider(config=FireworksConfig(provider=Provider.FIREWORKS, api_key="test"))
        response = CompletionResponse(
            id="test",
            choices=[
                Choice(
                    message=ChoiceMessage(
                        role="assistant",
                        content=None,
                        tool_calls=[
                            FireworksToolCall(
                                id="test_id_1",
                                type="function",
                                function=FireworksToolCallFunction(
                                    name="test_tool",
                                    arguments='{"key": "value"}',
                                ),
                            ),
                        ],
                    ),
                ),
            ],
            usage=Usage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
        )

        content = provider._extract_content_str(response)
        assert content == ""


class TestUnknownError:
    def test_content_length_exceeded(self, fireworks_provider: FireworksAIProvider):
        e = fireworks_provider._unknown_error(
            Response(
                status_code=400,
                text="""{
                "error": {
                    "code": "string_above_max_length",
                    "message": "The string is too long"
                }
            }""",
            ),
        )
        assert isinstance(e, MaxTokensExceededError)
        assert str(e) == "The string is too long"

    def test_context_length_exceeded(self, fireworks_provider: FireworksAIProvider):
        e = fireworks_provider._unknown_error(
            Response(
                status_code=400,
                text="""{"error": {"code": "context_length_exceeded", "message": "Max token exceeded"}}""",
            ),
        )
        assert isinstance(e, MaxTokensExceededError)
        assert str(e) == "Max token exceeded"

    def test_invalid_request_error(self, fireworks_provider: FireworksAIProvider):
        e = fireworks_provider._unknown_error(
            Response(
                status_code=400,
                text="""{"error": {"type": "invalid_request_error", "message": "Prompt is too long"}}""",
            ),
        )
        assert isinstance(e, MaxTokensExceededError)
        assert str(e) == "Prompt is too long"

    def test_prompt_too_long(self, fireworks_provider: FireworksAIProvider):
        payload = {
            "error": {
                "message": "The prompt is too long: 140963, model maximum context length: 131071,",
                "object": "truncate",
                "type": "invalid_request_error",
            },
        }
        e = fireworks_provider._unknown_error(
            Response(
                status_code=400,
                text=json.dumps(payload),
            ),
        )
        assert isinstance(e, MaxTokensExceededError)
        assert e.capture is False
        assert e.store_task_run

    @pytest.mark.parametrize(
        "message",
        [
            "Cannot decode or download image Incorrect padding",
            "Failed to decode image cannot identify image file <_io.BytesIO object at 0x7fa71ede77e0>, supported images types are jpeg, png, ppm, gif, tiff and bmp",
        ],
    )
    def test_invalid_file_error(self, fireworks_provider: FireworksAIProvider, message: str):
        payload = {
            "error": {
                "message": message,
                "type": "invalid_request_error",
            },
        }
        error = fireworks_provider._unknown_error(
            Response(
                status_code=400,
                text=json.dumps(payload),
            ),
        )
        assert isinstance(error, ProviderInvalidFileError)
        assert str(error) == message


class TestExtractAndLogRateLimits:
    async def test_extract_and_log_rate_limits(self, fireworks_provider: FireworksAIProvider):
        response = Response(
            status_code=200,
            headers={
                "x-ratelimit-remaining-requests": "100",
                "x-ratelimit-limit-requests": "1000",
                "x-ratelimit-remaining-tokens-prompt": "10",
                "x-ratelimit-limit-tokens-prompt": "1000",
                "x-ratelimit-remaining-tokens-generated": "20",
                "x-ratelimit-limit-tokens-generated": "1000",
            },
        )
        await fireworks_provider._extract_and_log_rate_limits(response, ProviderOptions(model=Model.LLAMA_3_3_70B))

        # TODO[metrics]
        # assert patch_metric_send.call_count == 3
        # metrics = sorted(
        #     [cast(Metric, call[0][0]) for call in patch_metric_send.call_args_list],
        #     key=lambda x: x.tags["limit_name"],
        # )

        # assert all(metric.name == "provider_rate_limit" for metric in metrics)
        # assert all(metric.tags["provider"] == "fireworks" for metric in metrics)
        # assert all(metric.tags["model"] == "llama-3.3-70b" for metric in metrics)
        # assert all(metric.tags["config"] == "workflowai_0" for metric in metrics)

        # assert metrics[0].tags["limit_name"] == "input_tokens"
        # assert metrics[0].gauge == 0.99
        # assert metrics[1].tags["limit_name"] == "output_tokens"
        # assert metrics[1].gauge == 0.98
        # assert metrics[2].tags["limit_name"] == "requests"
        # assert metrics[2].gauge == 0.9


class TestResponseFormat:
    @pytest.mark.parametrize(
        "options",
        [
            pytest.param(ProviderOptions(model=Model.LLAMA_3_3_70B), id="plain-text"),
            pytest.param(
                ProviderOptions(model=Model.LLAMA_3_3_70B, output_schema={"type": "object"}),
                id="structured-output",
            ),
        ],
    )
    def test_response_format_none_when_tools(self, fireworks_provider: FireworksAIProvider, options: ProviderOptions):
        """Check that the response format is None whenever tools are involved no matter what the structured output set
        up is"""
        response_format = fireworks_provider._response_format(
            options=options.model_copy(
                update={"enabled_tools": [test_models.fake_tool()]},
            ),
            model_data=test_models.fake_model_data(supports_structured_output=True),
        )
        assert response_format is None

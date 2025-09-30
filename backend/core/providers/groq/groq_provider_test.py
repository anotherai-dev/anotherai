# pyright: reportPrivateUsage=false

import json
import logging
from collections.abc import Callable
from datetime import date
from typing import Any
from unittest.mock import Mock

import pytest
from httpx import Response
from pytest_httpx import HTTPXMock, IteratorStream

from core.domain.message import Message, MessageDeprecated
from core.domain.models import Model
from core.domain.models.model_data import MaxTokensData, ModelData, QualityData, SpeedData, SpeedIndex
from core.domain.models.model_data_mapping import DisplayedProvider
from core.domain.models.model_provider_data_mapping import GROQ_PROVIDER_DATA
from core.domain.tool import Tool
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.models import RawCompletion
from core.providers._base.provider_error import (
    ContentModerationError,
    FailedGenerationError,
    MaxTokensExceededError,
    ProviderError,
    ProviderInternalError,
    ProviderInvalidFileError,
    UnknownProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers.groq.groq_domain import Choice, CompletionResponse, GroqMessage, Usage
from core.providers.groq.groq_provider import _NAME_OVERRIDE_MAP, GroqConfig, GroqProvider
from core.utils.json_utils import extract_json_str
from tests.utils import fixture_bytes, fixtures_json


def _output_factory(x: str) -> Any:
    return json.loads(x)


@pytest.fixture
def groq_provider():
    provider = GroqProvider(config=GroqConfig(api_key="some_api_key"))
    provider.logger = Mock(spec=logging.Logger)
    return provider


class TestStream:
    # Tests overlap with single stream above but check the entire structure
    async def test_stream(self, httpx_mock: HTTPXMock, groq_provider: GroqProvider):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            stream=IteratorStream(
                [
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":null,"choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,"finish_reason":null}],"x_groq":{"id":"req_01j47pdq9cerqbp0w6bzqwmytq","queue_length":1}}\n\ndata: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":"```"},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":"json"},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":" {"},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":'
                    b'"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":" \\""},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":"sent"},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":"iment"},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":"\\":"},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":" \\""},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":"positive\\""},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{"content":"}```"},"logprobs":null,"finish_reason":null}]}\n\n',
                    b'data: {"id":"chatcmpl-96c29a0b-2a71-46fd-af4d-62d783cfc693","object":"chat.completion.chunk","created":1722540285,"model":"llama-3.3-70b-versatile","system_fingerprint":"fp_b3ae7e594e","choices":[{"index":0,"delta":{},"logprobs":null,"finish_reason":"stop"}],"x_groq":{"id":"req_01j47pdq9cerqbp0w6bzqwmytq","usage":{"queue_time":0.019005437000000007,"prompt_tokens":244,"prompt_time":0.058400983,"completion_tokens":15,"completion_time":0.06,"total_tokens":259,"total_time":0.11840098299999999}}}\n\n',
                    b"data: [DONE]",
                ],
            ),
        )

        streamer = groq_provider.stream(
            [
                Message.with_text("Hello"),
            ],
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=1000, temperature=0, output_schema={}),
            output_factory=lambda x: json.loads(extract_json_str(x)),
        )
        chunks = [o async for o in streamer]
        assert len(chunks) == 12
        assert not any(c.is_empty() for c in chunks)

        final_chunk = chunks[-1].final_chunk
        assert final_chunk
        assert final_chunk.agent_output == {"sentiment": "positive"}

        # Not sure why the pyright in the CI reports an error here
        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"  # pyright: ignore reportUnknownMemberType
        body = json.loads(request.read().decode())
        assert body == {
            "max_tokens": 1000,
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "content": "Hello",
                    "role": "user",
                },
            ],
            "response_format": {"type": "text"},
            "stream": True,
            "temperature": 0.0,
        }

    async def test_stream_error(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            status_code=400,
            json={"error": {"message": "blabla", "type": "bloblo", "param": "blibli", "code": "blublu"}},
        )

        provider = GroqProvider()

        streamer = provider.stream(
            [Message.with_text("Hello")],
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
            output_factory=_output_factory,
        )
        # TODO: be stricter about what error is returned here
        with pytest.raises(UnknownProviderError) as e:
            [chunk async for chunk in streamer]

        assert e.value.capture
        assert str(e.value) == "blabla"


class TestComplete:
    # Tests overlap with single stream above but check the entire structure
    # @pytest.mark.parametrize("provider, model", list_groq_provider_x_models())
    async def test_complete(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            json=CompletionResponse(
                id="some_id",
                choices=[
                    Choice(
                        message=GroqMessage(content='{"message": "Hello you"}', role="assistant"),
                    ),
                ],
                usage=Usage(prompt_tokens=10, completion_tokens=3, total_tokens=13),
            ).model_dump(),
        )

        provider = GroqProvider()

        o = await provider.complete(
            [
                Message.with_text("Hello"),
            ],
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
            output_factory=_output_factory,
        )
        assert o.agent_output == {"message": "Hello you"}
        assert o.tool_call_requests is None
        # Not sure why the pyright in the CI reports an error here
        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"  # pyright: ignore reportUnknownMemberType
        body = json.loads(request.read().decode())
        assert body == {
            "max_tokens": 10,
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "content": "Hello",
                    "role": "user",
                },
            ],
            "response_format": {"type": "text"},
            "stream": False,
            "temperature": 0.0,
        }

    async def test_complete_without_max_tokens(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            json=CompletionResponse(
                id="some_id",
                choices=[
                    Choice(
                        message=GroqMessage(content='{"message": "Hello you"}', role="assistant"),
                    ),
                ],
                usage=Usage(prompt_tokens=10, completion_tokens=3, total_tokens=13),
            ).model_dump(),
        )

        provider = GroqProvider()

        o = await provider.complete(
            [
                Message.with_text("Hello"),
            ],
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, temperature=0),
            output_factory=_output_factory,
        )
        assert o.agent_output == {"message": "Hello you"}
        assert o.tool_call_requests is None
        # Not sure why the pyright in the CI reports an error here
        request = httpx_mock.get_requests()[0]
        assert request.method == "POST"  # pyright: ignore reportUnknownMemberType
        body = json.loads(request.read().decode())

        assert body == {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "content": "Hello",
                    "role": "user",
                },
            ],
            "response_format": {"type": "text"},
            "stream": False,
            "temperature": 0.0,
        }

    async def test_complete_500(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            status_code=500,
            text="Internal Server Error",
        )

        provider = GroqProvider()

        with pytest.raises(ProviderInternalError) as e:
            await provider.complete(
                [Message.with_text("Hello")],
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
                output_factory=_output_factory,
            )

        details = e.value.serialized().details
        assert details
        assert details.get("provider_error") == {"raw": "Internal Server Error"}

    async def test_complete_with_tool_calls(self, httpx_mock: HTTPXMock, groq_provider: GroqProvider):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            json=fixtures_json("groq", "completion_with_tool_call.json"),
        )

        o = await groq_provider.complete(
            [Message.with_text("Hello")],
            options=ProviderOptions(
                model=Model.LLAMA_4_MAVERICK_BASIC,
                max_tokens=10,
                temperature=0,
                enabled_tools=[
                    Tool(
                        name="get_current_time",
                        description="Get the current time",
                        input_schema={},
                        output_schema={},
                    ),
                ],
            ),
            output_factory=_output_factory,
        )

        assert o.tool_call_requests is not None
        assert o.tool_call_requests[0].tool_name == "get_current_time"
        assert o.tool_call_requests[0].tool_input_dict == {"timezone": "America/New_York"}

    async def test_complete_failed_generation(self, httpx_mock: HTTPXMock, groq_provider: GroqProvider):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            json=fixtures_json("groq", "failed_generation.json"),
            status_code=400,
            is_reusable=True,
        )

        with pytest.raises(FailedGenerationError):
            await groq_provider.complete(
                [Message.with_text("Hello")],
                options=ProviderOptions(
                    model=Model.LLAMA_4_MAVERICK_BASIC,
                    max_tokens=10,
                    temperature=0,
                ),
                output_factory=_output_factory,
            )

    async def test_complete_content_moderation(self, httpx_mock: HTTPXMock, groq_provider: GroqProvider):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            json=fixtures_json("groq", "content_moderation.json"),
            status_code=200,
            is_reusable=True,  # TODO: figure out why it needs to be reusable
        )

        with pytest.raises(ContentModerationError):
            await groq_provider.complete(
                [Message.with_text("Hello")],
                options=ProviderOptions(model=Model.LLAMA_4_MAVERICK_BASIC, output_schema={}),
                output_factory=_output_factory,
            )


class TestExtractContentStr:
    def test_absent_json_does_not_raise(self, groq_provider: GroqProvider):
        # An absent JSON is caught upstream so this function should not raise
        response = CompletionResponse(
            id="some_id",
            choices=[Choice(message=GroqMessage(content="Hello", role="user"))],
            usage=Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

        res = groq_provider._extract_content_str(response)  # pyright: ignore [reportPrivateUsage]
        assert res == "Hello"
        groq_provider.logger.warning.assert_not_called()  # type: ignore


class TestSanitizeModelData:
    def test_sanitize_model_data(self, groq_provider: GroqProvider):
        model_data = ModelData(
            supports_structured_output=True,
            supports_json_mode=True,
            supports_input_image=True,
            supports_input_pdf=True,
            supports_input_audio=True,
            display_name="test",
            icon_url="test",
            max_tokens_data=MaxTokensData(source="", max_tokens=100),
            release_date=date(2024, 1, 1),
            quality_data=QualityData(index=100),
            speed_data=SpeedData(
                index=SpeedIndex(value=500),
            ),
            provider_name=DisplayedProvider.GROQ.value,
            supports_tool_calling=True,
            fallback=None,
        )
        groq_provider.sanitize_model_data(model_data)
        assert model_data.supports_structured_output is False


class TestFinishReasonLength:
    async def test_finish_reason_length(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            json=fixtures_json("groq", "finish_reason_length_response.json"),
        )

        provider = GroqProvider()
        with pytest.raises(MaxTokensExceededError) as e:
            await provider.complete(
                [Message.with_text("Hello")],
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
                output_factory=_output_factory,
            )
        assert (
            e.value.args[0] == "Model returned a response with a length finish reason, meaning the maximum "
            "number of tokens was exceeded."
        )

    async def test_finish_reason_length_stream(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.groq.com/openai/v1/chat/completions",
            stream=IteratorStream(
                [
                    fixture_bytes("groq", "finish_reason_length_stream_response.txt"),
                ],
            ),
        )
        provider = GroqProvider()
        with pytest.raises(MaxTokensExceededError) as e:
            async for _ in provider._single_stream(  # pyright: ignore reportPrivateUsage
                {"messages": [{"role": "user", "content": "Hello"}]},
                output_factory=_output_factory,
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
            ):
                pass

        assert (
            e.value.args[0]
            == "Model returned a response with a length finish reason, meaning the maximum number of tokens was exceeded."
        )


class TestPrepareCompletion:
    async def test_role_before_content(self, groq_provider: GroqProvider):
        """Test that the 'role' key appears before 'content' in the prepared request."""
        request = groq_provider._build_request(  # pyright: ignore[reportPrivateUsage]
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


class TestBuildRequest:
    def test_build_request_with_max_tokens(self, groq_provider: GroqProvider):
        request = groq_provider._build_request(  # pyright: ignore[reportPrivateUsage]
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, max_tokens=10, temperature=0),
            stream=False,
        )
        dumped = request.model_dump()
        assert dumped["messages"][0]["role"] == "user"
        assert dumped["messages"][0]["content"] == "Hello"
        assert dumped["max_tokens"] == 10

    def test_build_request_without_max_tokens(self, groq_provider: GroqProvider):
        request = groq_provider._build_request(  # pyright: ignore[reportPrivateUsage]
            messages=[MessageDeprecated(role=MessageDeprecated.Role.USER, content="Hello")],
            options=ProviderOptions(model=Model.LLAMA_3_3_70B, temperature=0),
            stream=False,
        )
        dumped = request.model_dump()
        assert dumped["messages"][0]["role"] == "user"
        assert dumped["messages"][0]["content"] == "Hello"
        assert dumped["max_tokens"] is None
        # TODO[max-tokens]: add a test for the max tokens
        # model_data = get_model_data(Model.LLAMA_3_3_70B)
        # if model_data.max_tokens_data.max_output_tokens:
        #     assert request.model_dump()["max_tokens"] == model_data.max_tokens_data.max_output_tokens
        # else:
        #     assert request.model_dump()["max_tokens"] == model_data.max_tokens_data.max_tokens


class TestUnknownError:
    @pytest.fixture
    def unknown_error_fn(self, groq_provider: GroqProvider):
        # Wrapper to avoid having to silence the private warning
        # and instantiate the response
        def _build_unknown_error(payload: str | dict[str, Any], status_code: int = 400):
            if isinstance(payload, dict):
                payload = json.dumps(payload)
            res = Response(status_code=status_code, text=payload)
            return groq_provider._unknown_error(res)  # pyright: ignore[reportPrivateUsage]

        return _build_unknown_error

    @pytest.mark.parametrize(
        "message",
        [
            'Get "http://localhost:3000/essai_ocr.jpeg": dial tcp: lookup localhost: no such host',
            'Get "http://localhost:3000/essai_ocr.jpeg": read: connection reset by peer',
        ],
    )
    def test_unknown_error_invalid_file(
        self,
        unknown_error_fn: Callable[[str | dict[str, Any]], ProviderError],
        message: str,
    ):
        payload = {
            "error": {
                "message": message,
                "type": "invalid_request_error",
            },
        }
        e = unknown_error_fn(payload)
        assert isinstance(e, ProviderInvalidFileError)
        assert e.capture is False

    def test_unknown_error_invalid_url(self, unknown_error_fn: Callable[[str | dict[str, Any]], ProviderError]):
        payload = {
            "error": {
                "message": "failed to retrieve media: received status code: 404",
                "type": "invalid_request_error",
            },
        }
        e = unknown_error_fn(payload)
        assert isinstance(e, ProviderInvalidFileError)
        assert e.capture is False

    def test_413_status_code(self, unknown_error_fn: Callable[[str | dict[str, Any], int], ProviderError]):
        e = unknown_error_fn("Request Entity Too Large", 413)
        assert isinstance(e, MaxTokensExceededError)
        assert str(e) == "Max tokens exceeded"

    def test_max_tokens_exceeded_error_message(self, unknown_error_fn: Callable[[str | dict[str, Any]], ProviderError]):
        e = unknown_error_fn({"error": {"message": "Please reduce the length of the messages or completion."}})
        assert isinstance(e, MaxTokensExceededError)

    def test_other_error_message(self, unknown_error_fn: Callable[[str | dict[str, Any]], ProviderError]):
        e = unknown_error_fn({"error": {"message": "Some other error occurred."}})
        assert isinstance(e, UnknownProviderError)
        assert e.capture is True

    def test_unparseable_error_message(self, unknown_error_fn: Callable[[str | dict[str, Any]], ProviderError]):
        e = unknown_error_fn("Unparseable error message")
        assert isinstance(e, UnknownProviderError)
        assert e.capture is True


@pytest.mark.parametrize(
    ("message", "expected_result"),
    [
        ("I can't help with that", True),
        ("I can help with that", False),
        ("I can't assist with that", True),
        ("I'm not going to help with that. Is there something else I can assist you with?", True),
        ("I can't help with that. Is there something else I can assist you with?", True),
    ],
)
def test_is_content_moderation_completion(message: str, expected_result: bool):
    assert GroqProvider.is_content_moderation_completion(message) == expected_result  # pyright: ignore [reportPrivateUsage]


def test_name_override_map_exhaustive():
    supported_models = set(GROQ_PROVIDER_DATA)
    models_in_map = set(_NAME_OVERRIDE_MAP)
    assert supported_models == models_in_map

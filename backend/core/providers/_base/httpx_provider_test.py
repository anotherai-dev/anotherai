import copy
import json
from json import JSONDecodeError
from typing import Any, override
from unittest.mock import AsyncMock, Mock

import pytest
from httpx import ConnectError, ReadError, ReadTimeout, RemoteProtocolError, Response
from pydantic import BaseModel
from pytest_httpx import HTTPXMock, IteratorStream

from core.domain.exceptions import JSONSchemaValidationError
from core.domain.file import File
from core.domain.message import Message, MessageContent, MessageDeprecated
from core.domain.models import Model, Provider
from core.domain.tool_call import ToolCallRequest
from core.providers._base.abstract_provider import RawCompletion
from core.providers._base.httpx_provider import HTTPXProvider
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import (
    ContentModerationError,
    FailedGenerationError,
    InvalidGenerationError,
    ProviderInternalError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ReadTimeOutError,
    UnknownProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers._base.provider_output import ProviderOutput
from core.providers._base.streaming_context import ParsedResponse, ToolCallRequestBuffer
from core.providers.anthropic.anthropic_domain import CompletionResponse
from core.providers.openai.openai_provider import OpenAIProvider
from tests.utils import mock_aiter


class DummyRequestModel(BaseModel):
    messages: list[MessageDeprecated]


class DummyResponseModel(BaseModel):
    content: str = ""


def _output_factory(x: str, _: bool) -> Any:
    return ProviderOutput(json.loads(x))


class MockedProvider(HTTPXProvider[Any, Any]):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.mock = Mock(spec=HTTPXProvider)
        self.mock._response_model_cls = Mock(return_value=DummyResponseModel)
        self.mock._extract_content_str = Mock(side_effect=lambda x: x.content)  # type: ignore
        self.mock._request_url = Mock(return_value="https://api.openai.com/v1/chat/completions")
        self.mock._request_headers.return_value = {}
        self.mock._build_request = Mock(return_value=DummyRequestModel(messages=[]))

    @classmethod
    @override
    def name(cls) -> Provider:
        return Provider.OPEN_AI

    @classmethod
    @override
    def required_env_vars(cls) -> list[str]:
        return []

    @override
    def _build_request(self, messages: list[MessageDeprecated], options: ProviderOptions, stream: bool) -> BaseModel:
        return self.mock._build_request(messages, options, stream)

    @override
    async def _request_headers(self, request: dict[str, Any], url: str, model: Model) -> dict[str, str]:
        return await self.mock._request_headers(request, url, model)

    @override
    def _request_url(self, model: Model, stream: bool) -> str:
        return self.mock._request_url(model, stream)

    @override
    def _response_model_cls(self) -> type[Any]:
        return self.mock._response_model_cls()

    @override
    def _extract_content_str(self, response: Any) -> str:
        return self.mock._extract_content_str(response)

    @override
    def _extract_usage(self, response: Any) -> LLMUsage | None:
        return self.mock._extract_usage(response)

    @override
    def _extract_stream_delta(
        self,
        sse_event: bytes,
        raw_completion: RawCompletion,
        tool_call_request_buffer: dict[int, ToolCallRequestBuffer],
    ):
        return self.mock._extract_stream_delta(sse_event, raw_completion, tool_call_request_buffer)

    @classmethod
    @override
    def _default_config(cls, index: int) -> dict[str, Any]:
        return {}

    @override
    def _compute_prompt_token_count(self, messages: list[dict[str, Any]], model: Model) -> float:
        return 0

    @override
    async def _compute_prompt_audio_token_count(self, messages: list[dict[str, Any]]):
        return 0, None


@pytest.fixture
def mocked_provider():
    return MockedProvider()


class TestWrapSSE:
    async def test_openai(self):
        iter = mock_aiter(
            b"data: 1",
            b"2\n\ndata: 3\n\n",
        )

        wrapped = OpenAIProvider().wrap_sse(iter)
        chunks = [chunk async for chunk in wrapped]
        assert chunks == [b"12", b"3"]

    async def test_multiple_events_in_single_chunk(self):
        iter = mock_aiter(
            b"data: 1\n\ndata: 2\n\ndata: 3\n\n",
        )
        chunks = [chunk async for chunk in OpenAIProvider().wrap_sse(iter)]
        assert chunks == [b"1", b"2", b"3"]

    async def test_split_at_newline(self):
        # Test that we correctly handle when a split happens between the new line chars
        iter = mock_aiter(
            b"data: 1\n",
            b"\ndata: 2\n\n",
        )
        chunks = [chunk async for chunk in OpenAIProvider().wrap_sse(iter)]
        assert chunks == [b"1", b"2"]

    async def test_split_at_data(self):
        # Test that we correctly handle when a split happens between the new line chars
        iter = mock_aiter(
            b"da",
            b"ta: 1\n",
            b"\ndata: 2\n\n",
        )
        chunks = [chunk async for chunk in OpenAIProvider().wrap_sse(iter)]
        assert chunks == [b"1", b"2"]


async def test_correct_validation_error(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://api.openai.com/v1/chat/completions",
        stream=IteratorStream(
            [
                b'data: {"id":"1","object":"chat.completion.chunk","created":1720404416,"model":"gpt-3.5-turbo-1106","system_fingerprint":"fp_44132a4de3","choices":[{"index":0,"delta":{"role":"assistant","content":""},"logprobs":null,',
                b'"finish_reason":null}]}\n\ndata: {"id":"chatcmpl-9iY4Gi66tnBpsuuZ20bUxfiJmXYQC","object":"chat.completion.chunk","created":1720404416,"model":"gpt-3.5-turbo-1106","system_fingerprint":"fp_44132a4de3","choices":[{"index":0,"delta":{"content":"{\\n"},"logprobs":null,"finish_reason":null}]}\n\n',
                b'data: {"id":"chatcmpl-9iY4Gi66tnBpsuuZ20bUxfiJmXYQC","object":"chat.completion.chunk","created":1720404416,"model":"gpt-3.5-turbo-1106","system_fingerprint":"fp_44132a4de3","choices":[{"index":0,"delta":{"content":"\\"greeting\\": \\"Hello James!\\"\\n}"},"logprobs":null,"finish_reason":null}]}\n\n',
                b"data: [DONE]\n\n",
            ],
        ),
    )

    provider = OpenAIProvider()

    def raise_validation_error(*args: Any, **kwargs: Any):
        raise JSONSchemaValidationError("specific validation error")

    with pytest.raises(InvalidGenerationError) as e:
        async for _ in provider._single_stream(  # pyright: ignore[reportPrivateUsage, reportUnknownVariableType]
            request={},
            output_factory=_output_factory,
            partial_output_factory=raise_validation_error,
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
        ):
            pass

    assert "specific validation error" in str(e)


async def test_read_timeout_stream(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(ReadTimeout("Unable to read within timeout"))

    provider = OpenAIProvider()

    with pytest.raises(ReadTimeOutError):
        async for _ in provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=_output_factory,
            partial_output_factory=lambda x: ProviderOutput(json.loads(x)),
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
        ):
            pass


async def test_read_timeout_run(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(ReadTimeout("Unable to read within timeout"))

    provider = OpenAIProvider()

    with pytest.raises(ReadTimeOutError):
        await provider._single_complete(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=_output_factory,
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
        )


async def test_remote_protocol_error_stream(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(RemoteProtocolError("Server disconnected without sending a response."))

    provider = OpenAIProvider()

    with pytest.raises(ProviderInternalError) as excinfo:
        async for _ in provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=_output_factory,
            partial_output_factory=lambda x: ProviderOutput(x),
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
        ):
            pass

    assert "Provider has disconnected without sending a response." in str(excinfo.value)


async def test_remote_protocol_error_run(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(RemoteProtocolError("Server disconnected without sending a response."))

    provider = OpenAIProvider()

    with pytest.raises(ProviderInternalError) as excinfo:
        await provider._single_complete(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=_output_factory,
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
        )

    assert "Provider has disconnected without sending a response." in str(excinfo.value)


class TestParseResponse:
    def test_failed_json_decode(self, mocked_provider: MockedProvider):
        response = Mock(spec=Response)
        response.text = "Arf arf"
        response.json = Mock(side_effect=JSONDecodeError("Failed to decode JSON", "Arf", 0))
        response.status_code = 200

        raw_completion = RawCompletion(response="", usage=LLMUsage())

        with pytest.raises(UnknownProviderError):
            mocked_provider._parse_response(response, Mock(), raw_completion, {})  # pyright: ignore[reportPrivateUsage]

        assert raw_completion.response == "Arf arf"

    def test_failed_finding_json(self, mocked_provider: MockedProvider):
        response = Mock(spec=Response)
        response.text = "Arf arf"
        response.json = Mock(return_value={"content": "hello"})
        response.status_code = 200

        raw_completion = RawCompletion(response="", usage=LLMUsage())

        output_factory = Mock(side_effect=JSONDecodeError("Failed to decode JSON", "Arf", 0))

        with pytest.raises(FailedGenerationError):
            mocked_provider._parse_response(response, output_factory, raw_completion, {})  # pyright: ignore[reportPrivateUsage]

        assert raw_completion.response == "hello"
        mocked_provider.mock._extract_content_str.assert_called_once_with(DummyResponseModel(content="hello"))

    def test_unexpected_response(self, mocked_provider: MockedProvider):
        response = Mock(spec=Response)
        # Provider will not be able to validate the response
        response.json = Mock(return_value={"content": 1})
        response.status_code = 200

        raw_completion = RawCompletion(response="", usage=LLMUsage())

        output_factory = Mock(side_effect=JSONDecodeError("Failed to decode JSON", "Arf", 0))

        with pytest.raises(ProviderInternalError):
            mocked_provider._parse_response(response, output_factory, raw_completion, {})  # pyright: ignore[reportPrivateUsage]

    def test_success(self, mocked_provider: MockedProvider):
        response = Mock(spec=Response)
        response.json = Mock(return_value={"content": '{"hello": "world"}'})
        response.status_code = 200

        mocked_provider.mock._extract_usage.return_value = LLMUsage(prompt_token_count=10, completion_token_count=100)

        raw_completion = RawCompletion(response="", usage=LLMUsage())

        output = mocked_provider._parse_response(response, _output_factory, raw_completion=raw_completion, request={})  # pyright: ignore[reportPrivateUsage]
        assert output == ProviderOutput(output={"hello": "world"}, final=True)
        assert raw_completion.response == '{"hello": "world"}'

        mocked_provider.mock._extract_usage.assert_called_once_with(DummyResponseModel(content='{"hello": "world"}'))
        assert raw_completion.usage == LLMUsage(prompt_token_count=10, completion_token_count=100)

    @pytest.mark.parametrize(
        ("exception", "raised_cls", "text"),
        [
            (IndexError("blabla"), FailedGenerationError, '{"hello": "world"}'),
            (KeyError("blabla"), FailedGenerationError, '{"hello": "world"}'),
            (UnknownProviderError("blabla"), UnknownProviderError, '{"hello": "world"}'),
            (
                ValueError("blabla"),
                ContentModerationError,
                "I apologize, but I do not feel comfortable responding to this request as it is inappropriate.",
            ),
        ],
    )
    def test_extract_usage_on_unknown_failure(
        self,
        mocked_provider: MockedProvider,
        exception: Exception,
        raised_cls: type[Exception],
        text: str,
    ):
        """Check that the usage is properly extracted even on an unknown error"""
        mocked_provider.mock._extract_usage.return_value = LLMUsage(prompt_token_count=100)
        mocked_provider.mock._extract_content_str.side_effect = exception

        response = Mock(spec=Response)
        response.json.return_value = {"content": text}
        response.text = text
        response.status_code = 200

        raw_completion = RawCompletion(response="", usage=LLMUsage())

        # Parse response should re-raise the exception
        with pytest.raises(raised_cls):
            mocked_provider._parse_response(response, _output_factory, raw_completion=raw_completion, request={})  # pyright: ignore[reportPrivateUsage]

        # In all use cases we should call extract usage and set the completion
        mocked_provider.mock._extract_usage.assert_called_once_with(DummyResponseModel(content=text))
        assert raw_completion.usage == LLMUsage(prompt_token_count=100)

    def test_extract_usage_on_empty_content(
        self,
        mocked_provider: MockedProvider,
    ):
        """Check that the usage is properly extracted even on an unknown error"""
        mocked_provider.mock._extract_usage.return_value = LLMUsage(prompt_token_count=100)

        response = Mock(spec=Response)
        response.json.return_value = {"content": ""}
        response.text = """{"content": ""}"""
        response.status_code = 200

        raw_completion = RawCompletion(response="", usage=LLMUsage())

        # Parse response should re-raise the exception
        with pytest.raises(FailedGenerationError):
            mocked_provider._parse_response(response, _output_factory, raw_completion=raw_completion, request={})  # pyright: ignore[reportPrivateUsage]

        # In all use cases we should call extract usage and set the completion
        mocked_provider.mock._extract_usage.assert_called_once_with(DummyResponseModel(content=""))
        assert raw_completion.usage == LLMUsage(prompt_token_count=100)


class TestReadErrors:
    async def test_fail_on_single_read_error(self, httpx_mock: HTTPXMock):
        # Check that the returned error is a ProviderUnavailableError
        httpx_mock.add_exception(ReadError("Failed to read"))

        provider = MockedProvider()

        with pytest.raises(ProviderUnavailableError) as e:
            await provider._single_complete(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=_output_factory,
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
            )

        assert e.value.capture is True
        assert str(e.value) == "Failed to reach provider: Failed to read"

    async def test_retry_on_read_error(self, httpx_mock: HTTPXMock):
        httpx_mock.add_exception(ReadError("Failed to read"))
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            json={"content": '{"hello": "world"}'},
            status_code=200,
        )

        provider = MockedProvider()

        output = await provider.complete(
            [],
            ProviderOptions(model=Model.GPT_4O_2024_05_13),
            lambda x, _: ProviderOutput(json.loads(x)),
        )
        assert output == ProviderOutput(output={"hello": "world"}, final=True)

        requests = httpx_mock.get_requests()
        assert len(requests) == 2

    async def test_max_retry_count(self, httpx_mock: HTTPXMock):
        httpx_mock.add_exception(ReadError("Failed to read"), is_reusable=True)

        with pytest.raises(ProviderUnavailableError):
            await MockedProvider().complete(  # pyright: ignore[reportPrivateUsage]
                [],
                ProviderOptions(model=Model.GPT_4O_2024_05_13),
                lambda x, _: ProviderOutput(json.loads(x)),
            )
        requests = httpx_mock.get_requests()
        assert len(requests) == 3


class TestConnectErrors:
    async def test_fail_on_single_connect_error(self, httpx_mock: HTTPXMock):
        # Check that the returned error is a ProviderUnavailableError
        httpx_mock.add_exception(ConnectError("Failed to connect"))

        provider = MockedProvider()

        with pytest.raises(ProviderUnavailableError) as e:
            await provider._single_complete(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=_output_factory,
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
            )

        assert e.value.capture is True
        assert str(e.value) == "Failed to reach provider: Failed to connect"

    async def test_retry_on_connect_error(self, httpx_mock: HTTPXMock):
        httpx_mock.add_exception(ConnectError("Failed to read"))
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            json={"content": '{"hello": "world"}'},
            status_code=200,
        )

        provider = MockedProvider()

        output = await provider.complete(
            [],
            ProviderOptions(model=Model.GPT_4O_2024_05_13),
            lambda x, _: ProviderOutput(json.loads(x)),
        )
        assert output == ProviderOutput(output={"hello": "world"}, final=True)

        requests = httpx_mock.get_requests()
        assert len(requests) == 2


class TestPrepareCompletion:
    async def test_prepare_completion_text_only(self, mocked_provider: MockedProvider):
        messages = [Message.with_text("Hello")]

        _, completion = await mocked_provider._prepare_completion(  # pyright: ignore[reportPrivateUsage]
            messages,
            ProviderOptions(model=Model.GPT_4O_2024_05_13),
            stream=False,
        )
        assert completion.usage.prompt_image_count == 0
        assert completion.usage.prompt_audio_token_count == 0
        assert completion.usage.prompt_audio_duration_seconds == 0

    async def test_prepare_completion_with_image(self, mocked_provider: MockedProvider):
        messages = [
            Message.with_text("Hello"),
            Message(content=[MessageContent(file=File(url="https://example.com/image.png"))], role="user"),
        ]
        _, completion = await mocked_provider._prepare_completion(  # pyright: ignore[reportPrivateUsage]
            messages,
            ProviderOptions(model=Model.GPT_4O_2024_05_13),
            stream=False,
        )
        assert completion.usage.prompt_image_count == 1
        assert completion.usage.prompt_audio_token_count == 0
        assert completion.usage.prompt_audio_duration_seconds == 0

    async def test_prepare_completion_with_audio(self, mocked_provider: MockedProvider):
        messages = [
            Message(
                content=[MessageContent(file=File(url="https://example.com/audio.mp3"))],
                role="user",
            ),
        ]
        _, completion = await mocked_provider._prepare_completion(  # pyright: ignore[reportPrivateUsage]
            messages,
            ProviderOptions(model=Model.GPT_4O_2024_05_13),
            stream=False,
        )
        assert completion.usage.prompt_image_count == 0
        assert completion.usage.prompt_audio_token_count is None
        assert completion.usage.prompt_audio_duration_seconds is None


class TestOperationTimeout:
    async def test_operation_timeout(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            status_code=408,
            json={
                "error": {
                    "message": "The operation timed out",
                    "type": "timeout",
                },
            },
        )

        provider = MockedProvider()

        with pytest.raises(ProviderTimeoutError) as e:
            await provider._single_complete(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=_output_factory,
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
            )

        assert e.value.code == "timeout"


class TestInvalidJSONError:
    async def test_invalid_json_error(self, mocked_provider: MockedProvider):
        completion = "Bedrock returned a non-JSON response that we don't handle"

        error = mocked_provider._invalid_json_error(  # pyright: ignore[reportPrivateUsage]
            Mock(),
            None,
            completion,
            "Generation does not contain a valid JSON",
        )
        assert isinstance(error, FailedGenerationError)
        assert error.args[0] == "Generation does not contain a valid JSON"  # type: ignore

    async def test_invalid_json_error_content_moderation(self, mocked_provider: MockedProvider):
        completion = "I apologize, but I do not feel comfortable responding to this request as it is inappropriate."
        error = mocked_provider._invalid_json_error(  # pyright: ignore[reportPrivateUsage]
            Mock(),
            None,
            completion,
            "Generation does not contain a valid JSON",
        )
        assert isinstance(error, ContentModerationError)
        assert error.retry is False
        assert error.provider_error == completion


class TestFailedGenerationError:
    async def test_failed_generation_error_retry(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            stream=IteratorStream(
                [
                    b'data: {"id":"1","choices":[{"delta":{"content":"invalid json"}}]}\n\n',
                    b"data: [DONE]\n\n",
                ],
            ),
        )

        provider = OpenAIProvider()

        with pytest.raises(FailedGenerationError) as e:
            async for _ in provider._single_stream(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=Mock(side_effect=JSONDecodeError(doc="", pos=1, msg="hello")),
                partial_output_factory=lambda x: ProviderOutput(x),
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
            ):
                pass

        assert e.value.retry is True
        assert "Model failed to generate a valid json" in str(e.value)


class DummyNativeToolProvider(MockedProvider):
    @classmethod
    def _extract_native_tool_calls(cls, response: CompletionResponse) -> list[ToolCallRequest]:
        return [ToolCallRequest(id="tool-123", tool_name="dummy_tool", tool_input_dict={})]


class DummyNativeToolStreamingProvider(DummyNativeToolProvider):
    def _extract_stream_delta(
        self,
        sse_event: bytes,
        raw_completion: RawCompletion,
        tool_call_request_buffer: dict[int, ToolCallRequestBuffer],
    ) -> ParsedResponse | None:
        # Return a dummy ParsedResponse on the first call only
        if not hasattr(self, "_delta_called"):
            self._delta_called = True
            return ParsedResponse(
                content='{"hello": "world"}',
                reasoning=None,
                tool_calls=[ToolCallRequest(id="tool-123", tool_name="dummy_tool", tool_input_dict={})],
            )
        return None


class TestNativeToolCalls:
    def test_native_tool_calls_non_stream(self) -> None:
        # Create a dummy response with valid JSON content
        response = Mock(spec=Response)
        response.json = Mock(return_value={"content": '{"hello": "world"}'})
        response.text = '{"hello": "world"}'

        raw_completion = RawCompletion(response="", usage=LLMUsage())
        provider = DummyNativeToolProvider()

        output = provider._parse_response(  # pyright: ignore[reportPrivateUsage]
            response,
            lambda x, _: ProviderOutput(output=json.loads(x)),
            raw_completion=raw_completion,
            request={},
        )
        expected_tool_calls = [ToolCallRequest(id="tool-123", tool_name="dummy_tool", tool_input_dict={})]
        assert output.output == {"hello": "world"}
        assert output.tool_calls == expected_tool_calls

    async def test_native_tool_calls_stream(self, httpx_mock: HTTPXMock) -> None:
        provider = DummyNativeToolStreamingProvider()
        # Override methods to use a dummy URL and empty headers
        provider._request_url = Mock(return_value="https://dummy.url")  # pyright: ignore[reportPrivateUsage]
        provider._request_headers = AsyncMock(return_value={})  # pyright: ignore[reportPrivateUsage]

        # Create a dummy SSE stream with a single event
        sse_stream = IteratorStream([b"data: test\n\n"])
        httpx_mock.add_response(
            url="https://dummy.url",
            stream=sse_stream,
            status_code=200,
        )

        raw_completion = RawCompletion(response="", usage=LLMUsage())
        outputs: list[ProviderOutput] = [
            output
            async for output in provider._single_stream(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=lambda x, _: ProviderOutput(output=json.loads(x)),
                partial_output_factory=lambda data: ProviderOutput(output=data),
                raw_completion=raw_completion,
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
            )
        ]

        # We expect a single final output
        assert len(outputs) == 2
        final_output = outputs[1]
        expected_tool_calls = [ToolCallRequest(id="tool-123", tool_name="dummy_tool", tool_input_dict={})]
        assert final_output.output == {"hello": "world"}
        assert final_output.tool_calls == expected_tool_calls


class TestStreamingHandlers:
    def test_handle_chunk_output(self, mocked_provider: MockedProvider):
        from core.providers._base.abstract_provider import RawCompletion
        from core.providers._base.llm_usage import LLMUsage
        from core.providers._base.streaming_context import StreamingContext

        context = StreamingContext(RawCompletion(response="", usage=LLMUsage()), json=True)

        # Test no updates
        context.streamer.process_chunk = Mock(return_value=None)
        assert mocked_provider._handle_chunk_output(context, "test content") is False  # pyright: ignore[reportPrivateUsage]

        # Test successful update
        context.streamer.process_chunk = Mock(return_value=[("path", "value")])
        assert mocked_provider._handle_chunk_output(context, "test content") is True  # pyright: ignore[reportPrivateUsage]
        assert context.agg_output == {"path": "value"}

    def test_handle_chunk_reasoning_steps(self, mocked_provider: MockedProvider):
        from core.providers._base.abstract_provider import RawCompletion
        from core.providers._base.llm_usage import LLMUsage
        from core.providers._base.streaming_context import StreamingContext

        context = StreamingContext(RawCompletion(response="", usage=LLMUsage()), json=True)

        # Test no reasoning steps
        assert mocked_provider._handle_chunk_reasoning_steps(context, None) is False  # pyright: ignore[reportPrivateUsage]
        assert context.reasoning is None

        # Test first reasoning step
        assert mocked_provider._handle_chunk_reasoning_steps(context, "First step") is True  # pyright: ignore[reportPrivateUsage]
        assert context.reasoning == "First step"

        # Test appending to existing reasoning step
        assert mocked_provider._handle_chunk_reasoning_steps(context, " continued") is True  # pyright: ignore[reportPrivateUsage]
        assert context.reasoning == "First step continued"

    def test_handle_chunk_tool_calls(self, mocked_provider: MockedProvider):
        from core.domain.tool_call import ToolCallRequest
        from core.providers._base.abstract_provider import RawCompletion
        from core.providers._base.llm_usage import LLMUsage
        from core.providers._base.streaming_context import StreamingContext

        context = StreamingContext(RawCompletion(response="", usage=LLMUsage()), json=True)

        # Test no tool calls
        assert mocked_provider._handle_chunk_tool_calls(context, None) is False  # pyright: ignore[reportPrivateUsage]
        assert context.tool_calls is None

        # Test adding tool calls
        tool_call = ToolCallRequest(id="123", tool_name="test_tool", tool_input_dict={})
        assert mocked_provider._handle_chunk_tool_calls(context, [tool_call]) is False  # pyright: ignore[reportPrivateUsage]
        assert context.tool_calls is not None
        assert len(context.tool_calls) == 1
        assert context.tool_calls[0] == tool_call

        # Test adding more tool calls
        tool_call2 = ToolCallRequest(id="456", tool_name="test_tool2", tool_input_dict={})
        assert mocked_provider._handle_chunk_tool_calls(context, [tool_call2]) is False  # pyright: ignore[reportPrivateUsage]
        assert context.tool_calls is not None
        assert len(context.tool_calls) == 2
        assert context.tool_calls[1] == tool_call2

    def test_handle_chunk(self, mocked_provider: MockedProvider):
        from core.domain.tool_call import ToolCallRequest
        from core.providers._base.abstract_provider import RawCompletion
        from core.providers._base.llm_usage import LLMUsage
        from core.providers._base.streaming_context import StreamingContext

        context = StreamingContext(RawCompletion(response="", usage=LLMUsage()), json=True)

        # Test no delta
        mocked_provider.mock._extract_stream_delta.return_value = None
        assert mocked_provider._handle_chunk(context, b"test") is False  # pyright: ignore[reportPrivateUsage]

        # Test delta with content only
        mocked_provider.mock._extract_stream_delta.return_value = ParsedResponse(content='{"key": "value"}')
        context.streamer.process_chunk = Mock(return_value=[("key", "value")])
        assert mocked_provider._handle_chunk(context, b"test") is True  # pyright: ignore[reportPrivateUsage]
        assert context.agg_output == {"key": "value"}

        # Test delta with reasoning steps
        mocked_provider.mock._extract_stream_delta.return_value = ParsedResponse(
            content='{"key": "value"}',
            reasoning="Step 1",
        )
        assert mocked_provider._handle_chunk(context, b"test") is True  # pyright: ignore[reportPrivateUsage]
        assert context.reasoning == "Step 1"

        # Test delta with tool calls (should not trigger yield)
        tool_call = ToolCallRequest(id="123", tool_name="test_tool", tool_input_dict={})
        mocked_provider.mock._extract_stream_delta.return_value = ParsedResponse(
            content='{"key": "value"}',
            tool_calls=[tool_call],
        )
        context.streamer.process_chunk = Mock(return_value=None)  # No content updates
        assert mocked_provider._handle_chunk(context, b"test") is False  # pyright: ignore[reportPrivateUsage]
        assert context.tool_calls is not None
        assert len(context.tool_calls) == 1
        assert context.tool_calls[0] == tool_call

    async def test_single_stream_success(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        # Setup mock response with multiple chunks
        sse_stream = IteratorStream(
            [
                b'data: {"content": "{\\"key\\": \\"value\\","}\n\n',
                b'data: {"content": "\\"key2\\": \\"value2\\"}"}\n\n',
                b"data: [DONE]\n\n",
            ],
        )
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            stream=sse_stream,
            status_code=200,
        )

        # Setup mock for stream delta extraction
        mocked_provider.mock._extract_stream_delta.side_effect = [
            ParsedResponse(content='{"key": "value",'),
            ParsedResponse(content='"key2": "value2"}'),
            None,
        ]

        outputs: list[ProviderOutput] = []
        async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=lambda x, _: ProviderOutput(output=json.loads(x)),
            partial_output_factory=lambda x: ProviderOutput(output=json.loads(x) if isinstance(x, str) else x),
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
        ):
            outputs.append(copy.deepcopy(output))  # noqa: PERF401

        assert len(outputs) == 3  # Two partial outputs and one final
        assert outputs[0].output == {"key": "value"}
        assert outputs[1].output == {"key": "value", "key2": "value2"}
        assert outputs[2].output == {"key": "value", "key2": "value2"}  # Final output should be the last complete JSON

    async def test_single_stream_invalid_json(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        # Setup mock response with invalid JSON
        sse_stream = IteratorStream(
            [
                b'data: {"content": "invalid json"}\n\n',
                b"data: [DONE]\n\n",
            ],
        )
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            stream=sse_stream,
            status_code=200,
        )

        mocked_provider.mock._extract_stream_delta.side_effect = [
            ParsedResponse(content="invalid json"),
            None,
        ]

        with pytest.raises(FailedGenerationError) as exc_info:
            async for _ in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=lambda x, _: ProviderOutput(output=json.loads(x)),
                partial_output_factory=lambda x: ProviderOutput(output=x),
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
            ):
                pass

        assert "Model failed to generate a valid json" in str(exc_info.value)
        assert exc_info.value.retry is True

    async def test_single_stream_with_tool_calls_invalid_json(
        self,
        mocked_provider: MockedProvider,
        httpx_mock: HTTPXMock,
    ):
        """Test that when we have tool calls, invalid JSON in the content is allowed"""
        # Setup mock response with invalid JSON but valid tool calls
        sse_stream = IteratorStream(
            [
                b'data: {"content": "invalid json"}\n\n',
                b"data: [DONE]\n\n",
            ],
        )
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            stream=sse_stream,
            status_code=200,
        )

        tool_call = ToolCallRequest(id="123", tool_name="test_tool", tool_input_dict={})
        mocked_provider.mock._extract_stream_delta.side_effect = [
            ParsedResponse(content="invalid json", tool_calls=[tool_call]),
            None,
        ]

        outputs: list[ProviderOutput] = []
        async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=lambda x, _: ProviderOutput(output=json.loads(x)),
            partial_output_factory=lambda x: ProviderOutput(output=x),
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
        ):
            outputs.append(output)  # noqa: PERF401

        assert len(outputs) == 1  # Only final output
        assert outputs[0].output is None
        assert outputs[0].tool_calls == [tool_call]

    async def test_single_stream_error_response(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        # Test error handling when the API returns an error status
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            json={"error": {"message": "Internal server error"}},
            status_code=500,
        )

        with pytest.raises(ProviderInternalError):
            async for _ in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=lambda x, _: ProviderOutput(output=json.loads(x)),
                partial_output_factory=lambda x: ProviderOutput(output=x),
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
            ):
                pass

    async def test_single_stream_with_reasoning_steps(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        # Setup mock response with reasoning steps
        sse_stream = IteratorStream(
            [
                b'data: {"content": "{\\"key\\": \\"value\\"}"}\n\n',
                b"data: [DONE]\n\n",
            ],
        )
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            stream=sse_stream,
            status_code=200,
        )

        mocked_provider.mock._extract_stream_delta.side_effect = [
            ParsedResponse(content='{"key": "value"}', reasoning="Step 1"),
            None,
        ]

        outputs: list[ProviderOutput] = []
        async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=lambda x, _: ProviderOutput(output=json.loads(x)),
            partial_output_factory=lambda x: ProviderOutput(output=x),
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
        ):
            outputs.append(output)  # noqa: PERF401

        assert len(outputs) == 2  # One partial output and one final
        assert outputs[0].reasoning == "Step 1"
        assert outputs[1].reasoning == "Step 1"

    async def test_single_stream_validation_error(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        # Setup mock response that will trigger a validation error
        sse_stream = IteratorStream(
            [
                b'data: {"content": "{\\"key\\": \\"value\\"}"}\n\n',
                b"data: [DONE]\n\n",
            ],
        )
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            stream=sse_stream,
            status_code=200,
        )

        mocked_provider.mock._extract_stream_delta.side_effect = [
            ParsedResponse(content='{"key": "value"}'),
            None,
        ]

        def failing_output_factory(x: str, _: bool) -> ProviderOutput:
            raise JSONSchemaValidationError("Invalid schema")

        with pytest.raises(FailedGenerationError) as exc_info:
            async for _ in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=failing_output_factory,
                partial_output_factory=lambda x: ProviderOutput(output=x),
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
            ):
                pass

        assert "Invalid schema" in str(exc_info.value)

    async def test_stream_raw_string(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        sse_stream = IteratorStream(
            [
                b'data: {"content": "Hello"}\n\n',
                b'data: {"content": " world"}\n\n',
                b"data: [DONE]\n\n",
            ],
        )
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            stream=sse_stream,
            status_code=200,
        )

        # Setup mock for stream delta extraction
        mocked_provider.mock._extract_stream_delta.side_effect = [
            ParsedResponse(content="Hello"),
            ParsedResponse(content=" world"),
            None,
        ]

        outputs: list[ProviderOutput] = []
        async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=lambda x, _: ProviderOutput(output=x),
            partial_output_factory=lambda x: ProviderOutput(output=x),
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
        ):
            outputs.append(copy.deepcopy(output))  # noqa: PERF401

        assert len(outputs) == 3
        assert outputs[0].output == "Hello"
        assert outputs[1].output == "Hello world"

    async def test_stream_deltas(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        sse_stream = IteratorStream(
            [
                b'data: {"content": "Hello"}\n\n',
                b'data: {"content": " world"}\n\n',
                b"data: [DONE]\n\n",
            ],
        )
        httpx_mock.add_response(
            url="https://api.openai.com/v1/chat/completions",
            stream=sse_stream,
            status_code=200,
        )

        # Setup mock for stream delta extraction
        mocked_provider.mock._extract_stream_delta.side_effect = [
            ParsedResponse(content="Hello"),
            ParsedResponse(content=" world"),
            None,
        ]

        outputs: list[ProviderOutput] = []
        async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=lambda x, _: ProviderOutput(output=x),
            partial_output_factory=lambda x: ProviderOutput(output=x),
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13, stream_deltas=True, output_schema={}),
        ):
            outputs.append(copy.deepcopy(output))  # noqa: PERF401

        assert len(outputs) == 3  # Two partial outputs and one final
        assert outputs[0].delta == "Hello"
        assert outputs[1].delta == " world"
        assert outputs[2].delta is None
        assert outputs[2].output == "Hello world"


class TestBuildProviderOutput:
    def test_basic_output(self, mocked_provider: MockedProvider):
        """Test basic output without reasoning steps or tool calls"""
        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            lambda x, _: ProviderOutput(output=json.loads(x)),
            '{"hello": "world"}',
            None,
            None,
        )
        assert output.output == {"hello": "world"}
        assert output.reasoning is None
        assert output.tool_calls is None

    def test_with_reasoning_steps(self, mocked_provider: MockedProvider):
        """Test output with reasoning steps"""
        reasoning = "Step 1"
        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            lambda x, _: ProviderOutput(output=json.loads(x)),
            '{"hello": "world"}',
            reasoning,
            None,
        )
        assert output.output == {"hello": "world"}
        assert output.reasoning == reasoning
        assert output.tool_calls is None

    def test_with_tool_calls(self, mocked_provider: MockedProvider):
        """Test output with tool calls"""
        tool_calls = [ToolCallRequest(id="123", tool_name="test_tool", tool_input_dict={})]
        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            lambda x, _: ProviderOutput(output=json.loads(x)),
            '{"hello": "world"}',
            None,
            tool_calls,
        )
        assert output.output == {"hello": "world"}
        assert output.reasoning is None
        assert output.tool_calls == tool_calls

    def test_with_existing_tool_calls(self, mocked_provider: MockedProvider):
        """Test output when the ProviderOutput already has tool calls"""
        new_tool_call = ToolCallRequest(id="123", tool_name="new_tool", tool_input_dict={})
        existing_tool_call = ToolCallRequest(id="456", tool_name="existing_tool", tool_input_dict={})

        def output_factory(x: str, _: bool) -> ProviderOutput:
            return ProviderOutput(output=json.loads(x), tool_calls=[new_tool_call])

        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            output_factory,
            '{"hello": "world"}',
            None,
            [existing_tool_call],
        )
        assert output.output == {"hello": "world"}
        assert output.reasoning is None
        assert output.tool_calls == [existing_tool_call, new_tool_call]

    def test_validation_error_without_tool_calls(self, mocked_provider: MockedProvider):
        """Test that validation error is raised when there are no tool calls"""

        def failing_factory(x: str, _: bool) -> ProviderOutput:
            raise JSONSchemaValidationError("Invalid schema")

        with pytest.raises(FailedGenerationError) as exc_info:
            mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
                failing_factory,
                '{"hello": "world"}',
                None,
                None,
            )
        assert "Invalid schema" in str(exc_info.value)

    def test_validation_error_with_tool_calls(self, mocked_provider: MockedProvider):
        """Test that validation error is suppressed when there are tool calls"""
        tool_calls = [ToolCallRequest(id="123", tool_name="test_tool", tool_input_dict={})]

        def failing_factory(x: str, _: bool) -> ProviderOutput:
            raise JSONSchemaValidationError("Invalid schema")

        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            failing_factory,
            '{"hello": "world"}',
            None,
            tool_calls,
        )
        assert output.output is None  # Empty output when validation fails but tool calls exist
        assert output.reasoning is None
        assert output.tool_calls == tool_calls

    def test_with_all_fields(self, mocked_provider: MockedProvider):
        """Test output with reasoning steps and tool calls"""
        reasoning = "Step 1"
        tool_calls = [ToolCallRequest(id="123", tool_name="test_tool", tool_input_dict={})]
        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            lambda x, _: ProviderOutput(output=json.loads(x)),
            '{"hello": "world"}',
            reasoning,
            tool_calls,
        )
        assert output.output == {"hello": "world"}
        assert output.reasoning == reasoning
        assert output.tool_calls == tool_calls

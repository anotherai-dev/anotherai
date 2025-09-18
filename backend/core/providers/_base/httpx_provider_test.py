import copy
import json
from json import JSONDecodeError
from typing import Any, override
from unittest.mock import Mock, patch

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
    ProviderInternalError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ReadTimeOutError,
    UnknownProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers._base.streaming_context import ParsedResponse
from core.providers.openai.openai_provider import OpenAIProvider
from core.runners.runner_output import RunnerOutput, RunnerOutputChunk, ToolCallRequestDelta
from tests.utils import mock_aiter


class DummyRequestModel(BaseModel):
    messages: list[MessageDeprecated]


class DummyResponseModel(BaseModel):
    content: str = ""


def _output_factory(x: str) -> Any:
    return json.loads(x)


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
    def _extract_stream_delta(self, sse_event: bytes) -> ParsedResponse:
        return self.mock._extract_stream_delta(sse_event)

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


async def test_read_timeout_stream(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(ReadTimeout("Unable to read within timeout"))

    provider = OpenAIProvider()

    with pytest.raises(ReadTimeOutError):
        async for _ in provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=_output_factory,
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
        assert output == RunnerOutput(agent_output={"hello": "world"})
        assert raw_completion.response == '{"hello": "world"}'

        mocked_provider.mock._extract_usage.assert_called_once_with(DummyResponseModel(content='{"hello": "world"}'))
        assert raw_completion.usage == LLMUsage(prompt_token_count=10, completion_token_count=100)

    @pytest.mark.parametrize(
        ("exception", "raised_cls", "text"),
        [
            pytest.param(IndexError("blabla"), FailedGenerationError, '{"hello": "world"}', id="index_error"),
            pytest.param(KeyError("blabla"), FailedGenerationError, '{"hello": "world"}', id="key_error"),
            pytest.param(
                UnknownProviderError("blabla"),
                UnknownProviderError,
                '{"hello": "world"}',
                id="unknown_provider_error",
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
            _output_factory,
        )
        assert output == RunnerOutput(agent_output={"hello": "world"})

        requests = httpx_mock.get_requests()
        assert len(requests) == 2

    async def test_max_retry_count(self, httpx_mock: HTTPXMock):
        httpx_mock.add_exception(ReadError("Failed to read"), is_reusable=True)

        with pytest.raises(ProviderUnavailableError):
            await MockedProvider().complete(  # pyright: ignore[reportPrivateUsage]
                [],
                ProviderOptions(model=Model.GPT_4O_2024_05_13),
                _output_factory,
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
            _output_factory,
        )
        assert output == RunnerOutput(agent_output={"hello": "world"})

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
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
            ):
                pass

        assert e.value.retry is True
        assert "Model failed to generate a valid json" in str(e.value)


def _mock_stream(mocked_provider: MockedProvider, httpx_mock: HTTPXMock, *res: ParsedResponse):
    httpx_mock.add_response(
        url="https://api.openai.com/v1/chat/completions",
        stream=IteratorStream([b"data: \n\n" for _ in range(len(res))]),
        status_code=200,
    )

    mocked_provider.mock._extract_stream_delta.side_effect = res


class TestNativeToolCalls:
    @patch.object(
        MockedProvider,
        "_extract_native_tool_calls",
        return_value=[ToolCallRequest(id="tool-123", tool_name="dummy_tool", tool_input_dict={})],
    )
    def test_native_tool_calls_non_stream(self, patched_extract_native_tool_calls: Mock) -> None:
        # Create a dummy response with valid JSON content
        response = Mock(spec=Response)
        response.json = Mock(return_value={"content": '{"hello": "world"}'})
        response.text = '{"hello": "world"}'

        raw_completion = RawCompletion(response="", usage=LLMUsage())

        provider = MockedProvider()

        output = provider._parse_response(  # pyright: ignore[reportPrivateUsage]
            response,
            _output_factory,
            raw_completion=raw_completion,
            request={},
        )
        expected_tool_calls = [ToolCallRequest(id="tool-123", tool_name="dummy_tool", tool_input_dict={})]
        assert output.agent_output == {"hello": "world"}
        assert output.tool_call_requests == expected_tool_calls

    async def test_native_tool_calls_stream(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock) -> None:
        _mock_stream(
            mocked_provider,
            httpx_mock,
            ParsedResponse(
                delta='{"hello": "world"}',
                tool_call_requests=[ToolCallRequestDelta(idx=0, id="tool-123", tool_name="dummy_tool", arguments="")],
            ),
        )

        raw_completion = RawCompletion(response="", usage=LLMUsage())
        outputs = [
            output
            async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=_output_factory,
                raw_completion=raw_completion,
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
            )
        ]

        # We expect a single final output
        assert len(outputs) == 2
        final_output = outputs[1].final_chunk
        assert final_output is not None
        assert final_output.agent_output == {"hello": "world"}
        assert final_output.tool_call_requests == [
            ToolCallRequest(id="tool-123", tool_name="dummy_tool", tool_input_dict={}),
        ]


class TestSingleStream:
    async def test_single_stream_success(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        _mock_stream(
            mocked_provider,
            httpx_mock,
            ParsedResponse(delta='{"key": "value",'),
            ParsedResponse(delta='"key2": "value2"}'),
        )

        outputs: list[RunnerOutputChunk] = []
        async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=_output_factory,
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
        ):
            outputs.append(copy.deepcopy(output))  # noqa: PERF401

        assert len(outputs) == 3  # Two partial outputs and one final
        assert outputs[0].delta == '{"key": "value",'
        assert outputs[1].delta == '"key2": "value2"}'
        assert outputs[2].final_chunk is not None
        assert outputs[2].final_chunk.agent_output == {"key": "value", "key2": "value2"}

    async def test_single_stream_invalid_json(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        # Setup mock response with invalid JSON
        _mock_stream(
            mocked_provider,
            httpx_mock,
            ParsedResponse(delta="invalid json"),
        )

        with pytest.raises(FailedGenerationError) as exc_info:
            async for _ in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=_output_factory,
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

        _mock_stream(
            mocked_provider,
            httpx_mock,
            ParsedResponse(
                delta="invalid json",
                tool_call_requests=[ToolCallRequestDelta(idx=0, id="123", tool_name="test_tool", arguments="")],
            ),
        )

        outputs: list[RunnerOutputChunk] = []
        async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=_output_factory,
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
        ):
            outputs.append(output)  # noqa: PERF401

        assert len(outputs) == 2  # Only final output
        assert outputs[-1].final_chunk is not None
        assert outputs[-1].final_chunk.tool_call_requests == [
            ToolCallRequest(index=0, id="123", tool_name="test_tool", tool_input_dict={}),
        ]

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
                output_factory=_output_factory,
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
            ):
                pass

    async def test_single_stream_with_reasoning_steps(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        _mock_stream(
            mocked_provider,
            httpx_mock,
            ParsedResponse(delta='{"key": "value"}', reasoning="Step 1"),
        )

        outputs: list[RunnerOutputChunk] = []
        async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=_output_factory,
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
        ):
            outputs.append(output)  # noqa: PERF401

        assert len(outputs) == 2  # One partial output and one final
        assert outputs[0].reasoning == "Step 1"
        assert outputs[1].reasoning is None
        assert outputs[1].final_chunk is not None
        assert outputs[1].final_chunk.reasoning == "Step 1"

    async def test_single_stream_validation_error(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        # Setup mock response that will trigger a validation error
        _mock_stream(
            mocked_provider,
            httpx_mock,
            ParsedResponse(delta='{"key": "value"}'),
            ParsedResponse(),
        )

        with pytest.raises(FailedGenerationError) as exc_info:
            async for _ in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
                request={},
                output_factory=Mock(side_effect=JSONSchemaValidationError("Invalid schema")),
                raw_completion=RawCompletion(response="", usage=LLMUsage()),
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13, output_schema={}),
            ):
                pass

        assert "Invalid schema" in str(exc_info.value)

    async def test_stream_raw_string(self, mocked_provider: MockedProvider, httpx_mock: HTTPXMock):
        _mock_stream(
            mocked_provider,
            httpx_mock,
            ParsedResponse(delta="Hello"),
            ParsedResponse(delta=" world"),
        )

        outputs: list[RunnerOutputChunk] = []
        async for output in mocked_provider._single_stream(  # pyright: ignore[reportPrivateUsage]
            request={},
            output_factory=lambda x: x,
            raw_completion=RawCompletion(response="", usage=LLMUsage()),
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
        ):
            outputs.append(copy.deepcopy(output))  # noqa: PERF401

        assert len(outputs) == 3
        assert outputs[0].delta == "Hello"
        assert outputs[1].delta == " world"
        assert outputs[2].final_chunk is not None
        assert outputs[2].final_chunk.agent_output == "Hello world"


class TestBuildProviderOutput:
    def test_basic_output(self, mocked_provider: MockedProvider):
        """Test basic output without reasoning steps or tool calls"""
        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            _output_factory,
            '{"hello": "world"}',
            None,
            None,
        )
        assert output.agent_output == {"hello": "world"}
        assert output.reasoning is None
        assert output.tool_call_requests is None

    def test_with_reasoning_steps(self, mocked_provider: MockedProvider):
        """Test output with reasoning steps"""
        reasoning = "Step 1"
        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            _output_factory,
            '{"hello": "world"}',
            reasoning,
            None,
        )
        assert output.agent_output == {"hello": "world"}
        assert output.reasoning == reasoning
        assert output.tool_call_requests is None

    def test_with_tool_calls(self, mocked_provider: MockedProvider):
        """Test output with tool calls"""
        tool_calls = [ToolCallRequest(id="123", tool_name="test_tool", tool_input_dict={})]
        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            _output_factory,
            '{"hello": "world"}',
            None,
            tool_calls,
        )
        assert output.agent_output == {"hello": "world"}
        assert output.reasoning is None
        assert output.tool_call_requests == tool_calls

    def test_validation_error_without_tool_calls(self, mocked_provider: MockedProvider):
        """Test that validation error is raised when there are no tool calls"""

        with pytest.raises(FailedGenerationError) as exc_info:
            mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
                Mock(side_effect=JSONSchemaValidationError("Invalid schema")),
                '{"hello": "world"}',
                None,
                None,
            )
        assert "Invalid schema" in str(exc_info.value)

    def test_validation_error_with_tool_calls(self, mocked_provider: MockedProvider):
        """Test that validation error is suppressed when there are tool calls"""
        tool_calls = [ToolCallRequest(id="123", tool_name="test_tool", tool_input_dict={})]

        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            Mock(side_effect=JSONSchemaValidationError("Invalid schema")),
            '{"hello": "world"}',
            None,
            tool_calls,
        )
        assert output.agent_output is None  # Empty output when validation fails but tool calls exist
        assert output.reasoning is None
        assert output.tool_call_requests == tool_calls

    def test_with_all_fields(self, mocked_provider: MockedProvider):
        """Test output with reasoning steps and tool calls"""
        reasoning = "Step 1"
        tool_calls = [ToolCallRequest(id="123", tool_name="test_tool", tool_input_dict={})]
        output = mocked_provider._build_structured_output(  # pyright: ignore[reportPrivateUsage]
            _output_factory,
            '{"hello": "world"}',
            reasoning,
            tool_calls,
        )
        assert output.agent_output == {"hello": "world"}
        assert output.reasoning == reasoning
        assert output.tool_call_requests == tool_calls

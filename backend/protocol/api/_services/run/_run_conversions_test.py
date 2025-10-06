# pyright: reportPrivateUsage=false

import json

import pytest

from core.domain.agent_output import AgentOutput
from core.domain.error import Error
from core.domain.exceptions import BadRequestError
from core.domain.file import FileKind
from core.domain.message import Message, MessageContent
from core.domain.tool_call import ToolCallRequest
from core.runners.runner_output import RunnerOutputChunk, ToolCallRequestDelta
from protocol.api._run_models import (
    OpenAIAudioInput,
    OpenAIProxyContent,
    OpenAIProxyFile,
    OpenAIProxyImageURL,
)
from tests.fake_models import fake_completion

from ._run_conversions import (
    _extract_completion_from_output,
    completion_chunk_choice_final_from_completion,
    completion_response_from_domain,
    content_to_domain,
)


class TestExtractCompletionFromOutput:
    def test_empty_output_with_no_messages(self):
        """Test extraction from AgentOutput with no messages"""
        output = AgentOutput(messages=None)

        text, tool_calls = _extract_completion_from_output(output)

        assert text == ""
        assert tool_calls is None

    def test_output_with_error(self):
        """Test extraction from AgentOutput with error"""
        output = AgentOutput(
            error=Error(message="Something went wrong"),
            messages=[Message.with_text("Hello", "assistant")],
        )

        text, tool_calls = _extract_completion_from_output(output)

        assert text == ""
        assert tool_calls is None

    def test_empty_messages_list(self):
        """Test extraction from AgentOutput with empty messages list"""
        output = AgentOutput(messages=[])

        text, tool_calls = _extract_completion_from_output(output)

        assert text == ""
        assert tool_calls is None

    def test_single_text_message(self):
        """Test extraction from single message with text content"""
        message = Message(
            role="assistant",
            content=[MessageContent(text="Hello world")],
        )
        output = AgentOutput(messages=[message])

        text, tool_calls = _extract_completion_from_output(output)

        assert text == "Hello world"
        assert tool_calls == []

    def test_multiple_text_contents_in_single_message(self):
        """Test extraction from message with multiple text contents"""
        message = Message(
            role="assistant",
            content=[
                MessageContent(text="Hello"),
                MessageContent(text="world"),
            ],
        )
        output = AgentOutput(messages=[message])

        text, tool_calls = _extract_completion_from_output(output)

        assert text == "Hello\nworld"
        assert tool_calls == []

    def test_multiple_messages_with_text(self):
        """Test extraction from multiple messages with text content"""
        messages = [
            Message(role="assistant", content=[MessageContent(text="First message")]),
            Message(role="assistant", content=[MessageContent(text="Second message")]),
        ]
        output = AgentOutput(messages=messages)

        text, tool_calls = _extract_completion_from_output(output)

        assert text == "First message\nSecond message"
        assert tool_calls == []

    def test_json_object_content(self):
        """Test extraction from message with JSON object content"""
        json_obj = {"key": "value", "number": 42}
        message = Message(
            role="assistant",
            content=[MessageContent(object=json_obj)],
        )
        output = AgentOutput(messages=[message])

        text, tool_calls = _extract_completion_from_output(output)

        assert text == json.dumps(json_obj)
        assert tool_calls == []

    def test_json_array_content(self):
        """Test extraction from message with JSON array content"""
        json_array = [1, 2, {"nested": "value"}]
        message = Message(
            role="assistant",
            content=[MessageContent(object=json_array)],
        )
        output = AgentOutput(messages=[message])

        text, tool_calls = _extract_completion_from_output(output)

        assert text == json.dumps(json_array)
        assert tool_calls == []

    def test_single_tool_call(self):
        """Test extraction from message with single tool call"""
        tool_call = ToolCallRequest(
            id="call_123",
            tool_name="get_weather",
            tool_input_dict={"location": "New York"},
        )
        message = Message(
            role="assistant",
            content=[MessageContent(tool_call_request=tool_call)],
        )
        output = AgentOutput(messages=[message])

        text, tool_calls = _extract_completion_from_output(output)

        assert text == ""
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0].id == "call_123"
        assert tool_calls[0].tool_name == "get_weather"
        assert tool_calls[0].tool_input_dict == {"location": "New York"}

    def test_multiple_tool_calls(self):
        """Test extraction from message with multiple tool calls"""
        tool_call1 = ToolCallRequest(
            id="call_123",
            tool_name="get_weather",
            tool_input_dict={"location": "New York"},
        )
        tool_call2 = ToolCallRequest(
            id="call_456",
            tool_name="send_email",
            tool_input_dict={"to": "user@example.com", "subject": "Weather"},
        )
        message = Message(
            role="assistant",
            content=[
                MessageContent(tool_call_request=tool_call1),
                MessageContent(tool_call_request=tool_call2),
            ],
        )
        output = AgentOutput(messages=[message])

        text, tool_calls = _extract_completion_from_output(output)

        assert text == ""
        assert tool_calls is not None
        assert len(tool_calls) == 2
        assert tool_calls[0].id == "call_123"
        assert tool_calls[0].tool_name == "get_weather"
        assert tool_calls[1].id == "call_456"
        assert tool_calls[1].tool_name == "send_email"

    def test_mixed_content_text_and_tool_calls(self):
        """Test extraction from message with both text and tool calls"""
        tool_call = ToolCallRequest(
            id="call_123",
            tool_name="get_weather",
            tool_input_dict={"location": "New York"},
        )
        message = Message(
            role="assistant",
            content=[
                MessageContent(text="Let me check the weather for you."),
                MessageContent(tool_call_request=tool_call),
                MessageContent(text="I'll get that information now."),
            ],
        )
        output = AgentOutput(messages=[message])

        text, tool_calls = _extract_completion_from_output(output)

        assert text == "Let me check the weather for you.\nI'll get that information now."
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "get_weather"

    def test_mixed_content_all_types(self):
        """Test extraction from message with text, JSON object, and tool calls"""
        tool_call = ToolCallRequest(
            id="call_123",
            tool_name="calculate",
            tool_input_dict={"expression": "2 + 2"},
        )
        json_obj = {"result": 4, "operation": "addition"}

        message = Message(
            role="assistant",
            content=[
                MessageContent(text="Here's the calculation:"),
                MessageContent(object=json_obj),
                MessageContent(tool_call_request=tool_call),
                MessageContent(text="Done!"),
            ],
        )
        output = AgentOutput(messages=[message])

        text, tool_calls = _extract_completion_from_output(output)

        expected_text = f"Here's the calculation:\n{json.dumps(json_obj)}\nDone!"
        assert text == expected_text
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "calculate"

    def test_multiple_messages_with_mixed_content(self):
        """Test extraction from multiple messages with various content types"""
        tool_call = ToolCallRequest(
            id="call_123",
            tool_name="search",
            tool_input_dict={"query": "python"},
        )

        messages = [
            Message(role="assistant", content=[MessageContent(text="First, I'll search:")]),
            Message(
                role="assistant",
                content=[
                    MessageContent(tool_call_request=tool_call),
                    MessageContent(text="Searching now..."),
                ],
            ),
            Message(
                role="assistant",
                content=[
                    MessageContent(object={"status": "complete"}),
                    MessageContent(text="Search completed!"),
                ],
            ),
        ]
        output = AgentOutput(messages=messages)

        text, tool_calls = _extract_completion_from_output(output)

        expected_text = 'First, I\'ll search:\nSearching now...\n{"status": "complete"}\nSearch completed!'
        assert text == expected_text
        assert tool_calls is not None
        assert len(tool_calls) == 1
        assert tool_calls[0].tool_name == "search"

    def test_empty_content_items(self):
        """Test extraction from message with empty content items (None values)"""
        message = Message(
            role="assistant",
            content=[
                MessageContent(text=None),  # Should be ignored
                MessageContent(text="Valid text"),
                MessageContent(object=None),  # Should be ignored
                MessageContent(tool_call_request=None),  # Should be ignored
            ],
        )
        output = AgentOutput(messages=[message])

        text, tool_calls = _extract_completion_from_output(output)

        assert text == "Valid text"
        assert tool_calls == []


class TestCompletionResponseFromDomain:
    def test_completion_response_from_domain_basic(self):
        """Test conversion from domain AgentCompletion to OpenAI proxy response"""
        # Create a fake completion using fake_models
        completion = fake_completion()

        # Call the function
        response = completion_response_from_domain(completion, deprecated_function=False)

        # Verify the response structure
        assert response.id == str(completion.id)
        assert response.model == (completion.final_model if completion.final_model else "unknown")
        assert response.created == int(completion.created_at.timestamp())
        assert response.version_id == completion.version.id
        assert response.metadata == completion.metadata

        # Verify choices
        assert len(response.choices) == 1
        choice = response.choices[0]
        assert choice.index == 0
        assert choice.message.role == "assistant"
        assert choice.message.content == "Hello my name is John"
        assert choice.finish_reason == "stop"
        assert choice.duration_seconds == completion.duration_seconds
        assert choice.cost_usd == completion.cost_usd

        # Verify usage is calculated from traces
        # Note: fake_completion has no text_token_count for prompt, only cached/reasoning tokens
        # So prompt_tokens will be 0, but completion_tokens will be 100
        assert response.usage is not None
        assert response.usage.prompt_tokens == 0  # fake_completion has no prompt text_token_count
        assert response.usage.completion_tokens == 100
        assert response.usage.total_tokens == 100


class TestCompletionChunkChoiceFinalFromCompletion:
    def test_basic_completion_without_final_chunk(self):
        """Test completion_chunk_choice_final_from_completion with basic completion and no final_chunk"""
        completion = fake_completion()

        result = completion_chunk_choice_final_from_completion(
            run=completion,
            final_chunk=None,
            deprecated_function=False,
        )

        # Verify the structure
        assert result.index == 0
        assert result.finish_reason == "stop"
        assert result.cost_usd == completion.cost_usd
        assert result.duration_seconds == completion.duration_seconds
        assert result.url.endswith(str(completion.id))

        # Verify delta content
        assert result.delta.role == "assistant"
        assert result.delta.content == "Hello my name is John"
        assert result.delta.function_call is None
        assert result.delta.tool_calls is None

        # Verify usage
        assert result.usage is not None
        assert result.usage.prompt_tokens == 0
        assert result.usage.completion_tokens == 100
        assert result.usage.total_tokens == 100

    def test_completion_with_final_chunk(self):
        """Test completion_chunk_choice_final_from_completion with final_chunk provided"""
        completion = fake_completion()
        final_chunk = RunnerOutputChunk(
            delta="Final chunk content",
            tool_call_requests=None,
            reasoning=None,
        )

        result = completion_chunk_choice_final_from_completion(
            run=completion,
            final_chunk=final_chunk,
            deprecated_function=False,
        )

        # Verify the structure
        assert result.index == 0
        assert result.finish_reason == "stop"
        assert result.cost_usd == completion.cost_usd
        assert result.duration_seconds == completion.duration_seconds

        # Verify delta content comes from final_chunk
        assert result.delta.role == "assistant"
        assert result.delta.content == "Final chunk content"
        assert result.delta.function_call is None
        assert result.delta.tool_calls is None

    def test_completion_with_tool_calls(self):
        """Test completion_chunk_choice_final_from_completion with tool calls"""
        # Create completion with tool calls
        tool_call = ToolCallRequest(
            id="call_123",
            tool_name="get_weather",
            tool_input_dict={"location": "New York"},
        )
        output = AgentOutput(
            messages=[
                Message(
                    role="assistant",
                    content=[
                        MessageContent(text="I'll check the weather for you."),
                        MessageContent(tool_call_request=tool_call),
                    ],
                ),
            ],
        )
        completion = fake_completion(agent_output=output)

        result = completion_chunk_choice_final_from_completion(
            run=completion,
            final_chunk=None,
            deprecated_function=False,
        )

        # Verify finish reason for tool calls
        assert result.finish_reason == "tool_calls"

        # Verify delta content
        assert result.delta.role == "assistant"
        assert result.delta.content == "I'll check the weather for you."
        assert result.delta.tool_calls is not None
        assert len(result.delta.tool_calls) == 1
        assert result.delta.tool_calls[0].id == "call_123"
        assert result.delta.tool_calls[0].function.name == "get_weather"

    def test_completion_with_tool_calls_deprecated_function(self):
        """Test completion_chunk_choice_final_from_completion with deprecated function calls"""
        # Create completion with tool calls
        tool_call = ToolCallRequest(
            id="call_123",
            tool_name="get_weather",
            tool_input_dict={"location": "New York"},
        )
        output = AgentOutput(
            messages=[
                Message(
                    role="assistant",
                    content=[
                        MessageContent(text="I'll check the weather for you."),
                        MessageContent(tool_call_request=tool_call),
                    ],
                ),
            ],
        )
        completion = fake_completion(agent_output=output)

        result = completion_chunk_choice_final_from_completion(
            run=completion,
            final_chunk=None,
            deprecated_function=True,
        )

        # Verify finish reason for function calls
        assert result.finish_reason == "function_call"

        # Verify delta content uses function_call instead of tool_calls
        assert result.delta.role == "assistant"
        assert result.delta.content == "I'll check the weather for you."
        assert result.delta.function_call is not None
        assert result.delta.function_call.name == "get_weather"
        assert result.delta.tool_calls is None

    def test_completion_with_no_traces(self):
        """Test completion_chunk_choice_final_from_completion with no traces (null usage)"""
        completion = fake_completion(traces=[])

        result = completion_chunk_choice_final_from_completion(
            run=completion,
            final_chunk=None,
            deprecated_function=False,
        )

        # Verify usage is None when no traces
        assert result.usage is None
        assert result.finish_reason == "stop"

    def test_final_chunk_with_tool_call_deltas(self):
        """Test completion_chunk_choice_final_from_completion with tool call deltas in final_chunk"""
        completion = fake_completion()
        tool_call_delta = ToolCallRequestDelta(
            id="call_456",
            idx=0,
            tool_name="send_email",
            arguments='{"to": "user@example.com"}',
        )
        final_chunk = RunnerOutputChunk(
            delta="Sending email...",
            tool_call_requests=[tool_call_delta],
            reasoning=None,
        )

        result = completion_chunk_choice_final_from_completion(
            run=completion,
            final_chunk=final_chunk,
            deprecated_function=False,
        )

        # Verify delta content from final_chunk
        assert result.delta.content == "Sending email..."
        assert result.delta.tool_calls is not None
        assert len(result.delta.tool_calls) == 1
        assert result.delta.tool_calls[0].id == "call_456"
        assert result.delta.tool_calls[0].index == 0
        assert result.delta.tool_calls[0].function.name == "send_email"

    def test_final_chunk_with_deprecated_function_call(self):
        """Test completion_chunk_choice_final_from_completion with deprecated function call in final_chunk"""
        completion = fake_completion()
        tool_call_delta = ToolCallRequestDelta(
            id="call_789",
            idx=0,
            tool_name="calculate",
            arguments='{"expression": "2+2"}',
        )
        final_chunk = RunnerOutputChunk(
            delta="Calculating...",
            tool_call_requests=[tool_call_delta],
            reasoning=None,
        )

        result = completion_chunk_choice_final_from_completion(
            run=completion,
            final_chunk=final_chunk,
            deprecated_function=True,
        )

        # Verify delta content uses function_call
        assert result.delta.content == "Calculating..."
        assert result.delta.function_call is not None
        assert result.delta.function_call.name == "calculate"
        assert result.delta.function_call.arguments == '{"expression": "2+2"}'
        assert result.delta.tool_calls is None

    @pytest.mark.parametrize(
        ("has_tool_calls", "deprecated_function", "expected_finish_reason"),
        [
            (False, False, "stop"),
            (False, True, "stop"),
            (True, False, "tool_calls"),
            (True, True, "function_call"),
        ],
    )
    def test_finish_reason_logic(self, has_tool_calls, deprecated_function, expected_finish_reason):
        """Test that finish_reason is correctly determined based on tool calls and deprecated_function flag"""
        if has_tool_calls:
            tool_call = ToolCallRequest(
                id="call_test",
                tool_name="test_tool",
                tool_input_dict={"param": "value"},
            )
            output = AgentOutput(
                messages=[
                    Message(
                        role="assistant",
                        content=[MessageContent(tool_call_request=tool_call)],
                    ),
                ],
            )
        else:
            output = AgentOutput(
                messages=[Message.with_text("Just a text response", role="assistant")],
            )

        completion = fake_completion(agent_output=output)

        result = completion_chunk_choice_final_from_completion(
            run=completion,
            final_chunk=None,
            deprecated_function=deprecated_function,
        )

        assert result.finish_reason == expected_finish_reason


class TestContentToDomain:
    def test_text_content_type(self):
        """Test content_to_domain with text content type"""
        content = OpenAIProxyContent(
            type="text",
            text="Hello, world!",
        )

        result = content_to_domain(content)

        assert isinstance(result, MessageContent)
        assert result.text == "Hello, world!"
        assert result.file is None
        assert result.tool_call_request is None
        assert result.tool_call_result is None
        assert result.object is None

    def test_text_content_type_with_whitespace(self):
        """Test content_to_domain with text content that has leading/trailing whitespace"""
        content = OpenAIProxyContent(
            type="text",
            text="  \n  Hello, world!  \n  ",
        )

        result = content_to_domain(content)

        assert result.text == "Hello, world!"

    def test_text_content_type_empty_text_raises_error(self):
        """Test content_to_domain with empty text raises BadRequestError"""
        content = OpenAIProxyContent(
            type="text",
            text="",
        )

        with pytest.raises(BadRequestError, match="Text content is required"):
            content_to_domain(content)

    def test_text_content_type_none_text_raises_error(self):
        """Test content_to_domain with None text raises BadRequestError"""
        content = OpenAIProxyContent(
            type="text",
            text=None,
        )

        with pytest.raises(BadRequestError, match="Text content is required"):
            content_to_domain(content)

    def test_image_url_content_type(self):
        """Test content_to_domain with image_url content type"""
        content = OpenAIProxyContent(
            type="image_url",
            image_url=OpenAIProxyImageURL(url="https://example.com/image.png"),
        )

        result = content_to_domain(content)

        assert isinstance(result, MessageContent)
        assert result.text is None
        assert result.file is not None
        assert result.file.url == "https://example.com/image.png"
        assert result.file.format == FileKind.IMAGE
        assert result.file.data is None
        assert result.file.content_type is None

    def test_image_url_content_type_with_detail(self):
        """Test content_to_domain with image_url content type including detail"""
        content = OpenAIProxyContent(
            type="image_url",
            image_url=OpenAIProxyImageURL(
                url="https://example.com/image.jpg",
                detail="high",
            ),
        )

        result = content_to_domain(content)

        assert result.file is not None
        assert result.file.url == "https://example.com/image.jpg"
        assert result.file.format == FileKind.IMAGE

    def test_image_url_content_type_missing_image_url_raises_error(self):
        """Test content_to_domain with missing image_url raises BadRequestError"""
        content = OpenAIProxyContent(
            type="image_url",
            image_url=None,
        )

        with pytest.raises(BadRequestError, match="Image URL content is required"):
            content_to_domain(content)

    def test_input_audio_content_type_with_url(self):
        """Test content_to_domain with input_audio content type using URL"""
        content = OpenAIProxyContent(
            type="input_audio",
            input_audio=OpenAIAudioInput(
                data="https://example.com/audio.mp3",
                format="mp3",
            ),
        )

        result = content_to_domain(content)

        assert isinstance(result, MessageContent)
        assert result.text is None
        assert result.file is not None
        assert result.file.url == "https://example.com/audio.mp3"
        assert result.file.format == FileKind.AUDIO
        assert result.file.data is None
        assert result.file.content_type is None

    def test_input_audio_content_type_with_base64_data(self):
        """Test content_to_domain with input_audio content type using base64 data"""
        content = OpenAIProxyContent(
            type="input_audio",
            input_audio=OpenAIAudioInput(
                data="dGVzdCBhdWRpbyBkYXRh",  # base64 encoded "test audio data"
                format="wav",
            ),
        )

        result = content_to_domain(content)

        assert isinstance(result, MessageContent)
        assert result.text is None
        assert result.file is not None
        assert result.file.data == "dGVzdCBhdWRpbyBkYXRh"
        assert result.file.content_type == "audio/wav"
        assert result.file.format == FileKind.AUDIO
        assert result.file.url is None

    def test_input_audio_content_type_format_without_slash(self):
        """Test content_to_domain with input_audio format that doesn't include slash"""
        content = OpenAIProxyContent(
            type="input_audio",
            input_audio=OpenAIAudioInput(
                data="dGVzdCBhdWRpbyBkYXRh",
                format="mp3",  # No slash, should be converted to audio/mp3
            ),
        )

        result = content_to_domain(content)

        assert result.file is not None
        assert result.file.content_type == "audio/mp3"

    def test_input_audio_content_type_missing_input_audio_raises_error(self):
        """Test content_to_domain with missing input_audio raises BadRequestError"""
        content = OpenAIProxyContent(
            type="input_audio",
            input_audio=None,
        )

        with pytest.raises(BadRequestError, match="Input audio content is required"):
            content_to_domain(content)

    def test_file_content_type_with_url(self):
        """Test content_to_domain with file content type using URL"""
        content = OpenAIProxyContent(
            type="file",
            file=OpenAIProxyFile(file_data="https://example.com/document.pdf"),
        )

        result = content_to_domain(content)

        assert isinstance(result, MessageContent)
        assert result.text is None
        assert result.file is not None
        assert result.file.url == "https://example.com/document.pdf"
        assert result.file.data is None
        assert result.file.content_type is None
        assert result.file.format is None

    def test_file_content_type_with_base64_data(self):
        """Test content_to_domain with file content type using base64 data"""
        content = OpenAIProxyContent(
            type="file",
            file=OpenAIProxyFile(file_data="dGVzdCBmaWxlIGRhdGE="),  # base64 encoded "test file data"
        )

        result = content_to_domain(content)

        assert isinstance(result, MessageContent)
        assert result.text is None
        assert result.file is not None
        assert result.file.data == "dGVzdCBmaWxlIGRhdGE="
        assert result.file.url is None
        assert result.file.content_type is None
        assert result.file.format is None

    def test_file_content_type_missing_file_raises_error(self):
        """Test content_to_domain with missing file raises BadRequestError"""
        content = OpenAIProxyContent(
            type="file",
            file=None,
        )

        with pytest.raises(BadRequestError, match="File content is required"):
            content_to_domain(content)

    def test_unknown_content_type_raises_error(self):
        """Test content_to_domain with unknown content type raises BadRequestError"""
        content = OpenAIProxyContent(
            type="unknown_type",
            text="Some text",
        )

        with pytest.raises(BadRequestError, match="Unknown content type: unknown_type"):
            content_to_domain(content)

    @pytest.mark.parametrize(
        ("content_type", "expected_error"),
        [
            ("text", "Text content is required"),
            ("image_url", "Image URL content is required"),
            ("input_audio", "Input audio content is required"),
            ("file", "File content is required"),
        ],
    )
    def test_content_type_validation_errors(self, content_type, expected_error):
        """Test that appropriate validation errors are raised for each content type"""
        content = OpenAIProxyContent(type=content_type)

        with pytest.raises(BadRequestError, match=expected_error):
            content_to_domain(content)

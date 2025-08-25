# pyright: reportPrivateUsage=false

import json

from core.domain.agent_output import AgentOutput
from core.domain.error import Error
from core.domain.message import Message, MessageContent
from core.domain.tool_call import ToolCallRequest

from ._run_conversions import _extract_completion_from_output


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

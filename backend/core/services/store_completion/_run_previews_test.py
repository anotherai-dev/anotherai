# pyright: reportPrivateUsage=false


from core.domain.file import File
from core.domain.message import Message, MessageContent
from core.domain.tool_call import ToolCallRequest, ToolCallResult
from core.services.store_completion._run_previews import (
    _input_preview,
    _messages_list_preview,
    _tool_call_request_preview,
)


class TestMessageListPreview:
    def test_messages_preview(self):
        messages = [Message.with_text("Hello, world!", role="user")]
        assert _messages_list_preview(messages) == "User: Hello, world!"

    def test_with_system_message(self):
        messages = [
            Message.with_text("You are a helpful assistant.", role="system"),
            Message.with_text("Hello, world!", role="user"),
        ]
        assert _messages_list_preview(messages) == "User: Hello, world!"

    def test_messages_preview_with_file(self):
        messages = [Message(content=[MessageContent(file=File(url="https://example.com/file.png"))], role="user")]
        assert _messages_list_preview(messages) == "User: [[img:https://example.com/file.png]]"

    def test_system_only(self):
        messages = [Message.with_text("Hello, world!", role="system")]
        assert _messages_list_preview(messages) == "System: Hello, world!"

    def test_empty_messages(self):
        """Test that empty messages list returns None"""
        assert _messages_list_preview([]) == ""

    def test_messages_with_run_id_no_prefix(self):
        """Test messages with no run_id (no prefix should be added)"""
        messages = [
            Message.with_text("First message", role="user"),
            Message.with_text("Second message", role="user"),
        ]
        assert _messages_list_preview(messages) == "User: First message"

    def test_messages_with_run_id_single_message_prefix(self):
        """Test messages with run_id creates proper prefix for single message"""

        messages = [
            Message.with_text("Message before run", role="assistant"),
            Message.with_text("New message after run", role="user"),
        ]

        result = _messages_list_preview(messages)
        assert result == "User: New message after run"

    def test_messages_with_run_id_multiple_messages_prefix(self):
        """Test messages with run_id creates proper prefix for multiple messages"""

        messages = [
            Message.with_text("Message before run", role="user"),
            Message.with_text("First new message", role="assistant"),
            Message.with_text("Second new message", role="user"),
        ]
        result = _messages_list_preview(messages)
        assert result == "User: Second new message"

    def test_messages_with_multiple_run_ids_uses_last(self):
        """Test that with multiple run_ids, it uses the last one"""

        messages = [
            Message.with_text("First run message", role="assistant"),
            Message.with_text("Middle message", role="user"),
            Message.with_text("Second run message", role="assistant"),
            Message.with_text("Final message", role="user"),
        ]

        result = _messages_list_preview(messages)
        assert result is not None
        assert result == "User: Final message"

    def test_include_roles_user_only(self):
        """Test default include_roles={'user'} behavior"""
        messages = [
            Message.with_text("System message", role="system"),
            Message.with_text("Assistant message", role="assistant"),
            Message.with_text("User message", role="user"),
        ]
        assert _messages_list_preview(messages, include_roles={"user"}) == "User: User message"

    def test_include_roles_no_match_fallback(self):
        """Test include_roles with no matches falls back to first message"""
        messages = [
            Message.with_text("System message", role="system"),
            Message.with_text("User message", role="user"),
        ]
        # Looking for assistant role that doesn't exist, should fallback to first message
        result = _messages_list_preview(messages, include_roles={"assistant"})
        assert result == "System: System message"

    def test_with_tool_call_result(self):
        """Test message with tool call result"""
        tool_call = ToolCallResult(
            id="test_id",
            tool_name="test_tool",
            tool_input_dict={"param": "value"},
            result="Whatever execution result",
        )
        messages = [
            Message(
                content=[MessageContent(tool_call_result=tool_call)],
                role="user",
            ),
        ]
        result = _messages_list_preview(messages)
        assert result == "Tool: Whatever execution result"

    def test_message_with_no_content(self):
        """Test message with no content returns None"""
        messages = [Message(content=[], role="user")]
        assert _messages_list_preview(messages) is None

    def test_message_content_priority_text_over_file(self):
        """Test that text content takes priority over file content"""
        messages = [
            Message(
                content=[
                    MessageContent(
                        text="Text content",
                        file=File(url="https://example.com/file.png"),
                    ),
                ],
                role="user",
            ),
        ]
        result = _messages_list_preview(messages)
        assert result == "User: [[img:https://example.com/file.png]]"

    def test_message_content_priority_file_over_tool_result(self):
        """Test that file content takes priority over tool_call_result"""
        tool_call = ToolCallResult(
            id="test_id",
            tool_name="test_tool",
            tool_input_dict={},
            result="Tool result",
        )
        messages = [
            Message(
                content=[
                    MessageContent(
                        file=File(url="https://example.com/file.png"),
                        tool_call_result=tool_call,
                    ),
                ],
                role="user",
            ),
        ]
        result = _messages_list_preview(messages)
        assert result == "User: [[img:https://example.com/file.png]]"


class TestToolCallRequestPreview:
    def test_tool_call_request_preview(self):
        assert (
            _tool_call_request_preview([ToolCallRequest(tool_name="test_name", tool_input_dict={"arg": "value"})])
            == "Tool: test_name(arg: value)"
        )

    def test_tool_call_request_preview_multiple(self):
        assert (
            _tool_call_request_preview(
                [
                    ToolCallRequest(tool_name="test_name", tool_input_dict={"arg": "value"}),
                    ToolCallRequest(tool_name="test_name2", tool_input_dict={"arg": "value2"}),
                ],
            )
            == "Tools: [test_name(arg: value), test_name2(arg: value2)]"
        )


class TestInputPreview:
    def test_with_message_replies(self):
        messages = Message.with_text("Hello, world!", role="user")
        variables = {"value": "Hello, world!"}

        assert _input_preview(variables, [messages]) == 'value: "Hello, world!" | User: Hello, world!'

    def test_reply_empty_object(self):
        messages = Message.with_text("Hello, world!", role="user")
        variables = {"value": "Hello, world!"}

        assert _input_preview(variables, [messages]) == 'value: "Hello, world!" | User: Hello, world!'

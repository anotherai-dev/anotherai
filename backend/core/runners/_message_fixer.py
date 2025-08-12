from collections.abc import Sequence

from core.domain.exceptions import BadRequestError
from core.domain.message import Message, MessageContent
from core.domain.tool_call import ToolCallRequest, ToolCallResult


class MessageAutofixer:
    def __init__(self):
        # Final array of messages
        self._fixed_messages: list[Message] = []
        # Aggregated tool call ids to make sure there are no duplicates
        # The index is stored to have a better error message
        self._tool_request_ids: dict[str, int] = {}
        self._tool_result_ids: set[str] = set()
        # Current tool call turn, emptied out when the tool call turn is over
        self._current_tool_requests: dict[str, ToolCallRequest] = {}
        # A message containing the tool call result of the current tool call turn that is
        # appended to the fixed messages.
        self._current_tool_result_message: Message | None = None

    @classmethod
    def _message_str(cls, i: int, j: int) -> str:
        return f"messages[{i}].content[{j}]"

    def _validate_tool_call_request(self, i: int, j: int, message: Message, tool_call_request: ToolCallRequest):
        if not message.role == "assistant":
            raise ValueError(
                f"Only assistant messages can have tool calls. "
                f"{self._message_str(i, j)} has role {message.role} and should not contain a tool call request.",
            )
        if tool_call_request.id in self._tool_request_ids:
            raise ValueError(
                f"Tool call request {tool_call_request.id} ({self._message_str(i, j)}) already "
                "found in previous messages.",
            )
        self._current_tool_requests[tool_call_request.id] = tool_call_request
        self._tool_request_ids[tool_call_request.id] = i

    def _validate_tool_call_result(self, i: int, j: int, message: Message, tool_call_result: ToolCallResult):
        if tool_call_result.id in self._tool_result_ids:
            raise ValueError(
                f"Tool call result {tool_call_result.id} ({self._message_str(i, j)}) already "
                "found in previous messages.",
            )
        if not self._current_tool_requests:
            raise ValueError(
                f"Tool call result {tool_call_result.id} ({self._message_str(i, j)}) "
                "should immediately follow a tool call request or another tool call result in case "
                "of parallel tool calls.",
            )
        if not message.role == "user":
            raise ValueError(
                f"{message.role} messages cannot have tool call results. "
                f"{self._message_str(i, j)} should not contain a tool call result",
            )
        try:
            request = self._current_tool_requests.pop(tool_call_result.id)
        except KeyError:
            if tool_call_result.id in self._tool_result_ids:
                # This is likely never hit since we guard against in between content
                msg = f"Tool call result {tool_call_result.id} ({self._message_str(i, j)}) responds to a request "
                f"present in messages[{self._tool_request_ids[tool_call_result.id]}] but other content is present in between. "
                "Make sure that the tool call result is immediately after the tool call request."
            else:
                msg = f"Tool call result {tool_call_result.id} ({self._message_str(i, j)}) not found in previous messages."
            raise ValueError(msg) from None

        tool_call_result.tool_name = request.tool_name
        tool_call_result.tool_input_dict = request.tool_input_dict
        self._tool_result_ids.add(tool_call_result.id)
        if not self._current_tool_result_message:
            self._current_tool_result_message = Message(role="user", content=[])
            self._fixed_messages.append(self._current_tool_result_message)

        self._current_tool_result_message.content.append(MessageContent(tool_call_result=tool_call_result))

    def fix(self, messages: Sequence[Message]):
        """Unfulfilled tool call requests are not allowed"""
        for i, m in enumerate(messages):
            # We only accept tool call results for new messages as long as we have
            # unanswered tool call requests
            only_accept_tool_call_results = bool(self._current_tool_requests)

            for j, c in enumerate(m.content):
                if c.tool_call_result:
                    self._validate_tool_call_result(i, j, m, c.tool_call_result)
                    continue
                # Otherwise if we are in a tool call turn we just raise
                # This would mean that there is unwanted content after a tool call request
                if only_accept_tool_call_results:
                    raise ValueError(
                        f"Only tool call results are allowed in tool call turn. "
                        f"{self._message_str(i, j)} should not contain any content other than tool call results "
                        f"since requests ids `{'`,`'.join(self._current_tool_requests.keys())}` are still pending.",
                    )
                if c.tool_call_request:
                    self._validate_tool_call_request(i, j, m, c.tool_call_request)
                    continue

            # When we are currently processing tool call results, we assume that all content
            # are part of the tool call turn
            # This means that we disallow any content in between a tool call request and the entirety
            # of the tool call result
            if self._current_tool_result_message:
                if not self._current_tool_requests:
                    # All the tool call requests have been processed, we can clear the current tool result message here
                    # To go back to normal message processing
                    self._current_tool_result_message = None
            else:
                self._fixed_messages.append(m)

        if self._current_tool_requests:
            raise ValueError(
                f"Tool call requests `{'`,`'.join(self._current_tool_requests.keys())}` are still pending. "
                "Make sure that all tool call requests are fulfilled before sending the next message.",
            )

        return self._fixed_messages


def fix_messages(messages: Sequence[Message]) -> list[Message]:
    try:
        return MessageAutofixer().fix(messages)
    except ValueError as e:
        raise BadRequestError(msg=str(e)) from e

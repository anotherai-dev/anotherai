from collections.abc import Sequence
from typing import Any

from structlog import get_logger

from core.domain.agent_completion import AgentCompletion
from core.domain.agent_input import AgentInput
from core.domain.agent_output import AgentOutput
from core.domain.message import Message
from core.domain.tool_call import ToolCallRequest
from core.utils.previews import DEFAULT_PREVIEW_MAX_LEN, compute_preview

_log = get_logger(__name__)


def _last_assistant_message_idx(messages: Sequence[Message]) -> int | None:
    for i, m in enumerate(reversed(messages)):
        if m.role == "assistant":
            return len(messages) - i - 1
    return None


def _message_preview(message: Message, max_len: int, role: str):
    if not message.content:
        return None

    role = role.capitalize()

    content = message.content[0]
    if content.file:
        return f"{role}: {compute_preview(content.file, max_len=max_len)}"

    if content.text:
        return f"{role}: {compute_preview(content.text, max_len=max_len)}"

    if content.object:
        return f"{role}: {compute_preview(content.object, max_len=max_len)}"

    if content.tool_call_result:
        return f"Tool: {compute_preview(content.tool_call_result.result, max_len=max_len)}"

    if reqs := list(message.tool_call_request_iterator()):
        return _tool_call_request_preview(reqs)

    return None


def _tool_call_request_preview(tool_call_requests: Sequence[ToolCallRequest]):
    if len(tool_call_requests) == 1:
        return f"Tool: {tool_call_requests[0].preview}"

    return f"Tools: [{', '.join([t.preview for t in tool_call_requests])}]"


def _messages_list_preview(
    messages: Sequence[Message] | None,
    include_roles: set[str] | None = None,
    max_len: int = DEFAULT_PREVIEW_MAX_LEN,
):
    if not messages:
        return ""
    if not include_roles:
        include_roles = {"user"}

    # Trying to find the number of messages that were added
    # This means finding the number of messages after the last run that has a "run_id"

    first_response_idx = _last_assistant_message_idx(messages)
    first_msg_idx = 0 if first_response_idx is None else first_response_idx + 1

    first_message = next((m for m in messages[first_msg_idx:] if m.role in include_roles), messages[0])
    if preview := _message_preview(first_message, max_len, first_message.role):
        return f"{preview}"
    return None


def _input_preview(variables: dict[str, Any] | None, messages: Sequence[Message] | None):
    if variables:
        first_preview = compute_preview(variables)
        if len(first_preview) < DEFAULT_PREVIEW_MAX_LEN and (
            second_preview := _messages_list_preview(
                messages,
                include_roles={"user", "assistant"},
                max_len=DEFAULT_PREVIEW_MAX_LEN - len(first_preview),
            )
        ):
            first_preview += f" | {second_preview}"
        return first_preview
    return _messages_list_preview(messages) or ""


def _output_preview(output: AgentOutput):
    if output.messages:
        return _messages_list_preview(output.messages, {"assistant"})
    if output.error:
        return f"Error: {output.error.message}"
    # Should not happen
    _log.error("No output preview", output=output)
    return ""


def assign_input_preview(input: AgentInput):
    if not input.preview:
        input.preview = _input_preview(
            input.variables,
            input.messages,
        )


def assign_output_preview(output: AgentOutput):
    if not output.preview:
        output.preview = _output_preview(output) or ""


def assign_run_previews(completion: AgentCompletion):
    if not completion.agent_input.preview:
        assign_input_preview(completion.agent_input)
    if not completion.agent_output.preview:
        assign_output_preview(completion.agent_output)

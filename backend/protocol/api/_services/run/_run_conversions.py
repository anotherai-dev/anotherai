import contextlib
import json
import re
from collections.abc import Iterator
from typing import Any, Literal

import structlog

from core.domain.agent_completion import AgentCompletion
from core.domain.agent_output import AgentOutput
from core.domain.exceptions import BadRequestError
from core.domain.fallback_option import FallbackOption
from core.domain.file import File, FileKind
from core.domain.inference import LLMTrace, Trace
from core.domain.message import Message, MessageContent, MessageRole
from core.domain.models.model_data_mapping import get_model_id
from core.domain.reasoning_effort import ReasoningEffort
from core.domain.tenant_data import PublicOrganizationData
from core.domain.tool import HostedTool, Tool
from core.domain.tool_call import ToolCallRequest, ToolCallResult
from core.domain.tool_choice import ToolChoiceFunction
from core.domain.version import Version
from core.providers._base.provider_error import MissingModelError
from protocol.api._run_models import (
    OpenAIAudioInput,
    OpenAIProxyChatCompletionChoice,
    OpenAIProxyChatCompletionRequest,
    OpenAIProxyChatCompletionResponse,
    OpenAIProxyCompletionUsage,
    OpenAIProxyContent,
    OpenAIProxyFunctionCall,
    OpenAIProxyMessage,
    OpenAIProxyToolCall,
    OpenAIProxyToolCallDelta,
    OpenAIProxyToolChoice,
    OpenAIProxyToolChoiceFunction,
    OpenAIProxyToolDefinition,
)
from protocol.api._services._urls import completion_url

_log = structlog.get_logger(__name__)

# Role mapping from OpenAI to domain
_role_mapping: dict[str, MessageRole] = {
    "user": "user",
    "assistant": "assistant",
    "system": "system",
    "developer": "system",
    "tool": "user",
    "function": "user",
}


def audio_input_to_domain(audio_input: "OpenAIAudioInput") -> File:
    content_type = audio_input.format
    if "/" not in content_type:
        content_type = f"audio/{content_type}"
    if not audio_input.format or audio_input.data.startswith("https://"):
        # Special case for when the format is not provided or when the data is in fact a URL
        return File(url=audio_input.data, format=FileKind.AUDIO)
    return File(data=audio_input.data, content_type=content_type, format=FileKind.AUDIO)


def content_to_domain(content: "OpenAIProxyContent") -> MessageContent:
    """Convert OpenAI proxy content to domain MessageContent"""
    match content.type:
        case "text":
            if not content.text:
                raise BadRequestError("Text content is required")
            return MessageContent(text=content.text.strip())
        case "image_url":
            if not content.image_url:
                raise BadRequestError("Image URL content is required")
            return MessageContent(file=File(url=content.image_url.url, format=FileKind.IMAGE))
        case "input_audio":
            if not content.input_audio:
                raise BadRequestError("Input audio content is required")
            return MessageContent(file=audio_input_to_domain(content.input_audio))
        case _:
            raise BadRequestError(f"Unknown content type: {content.type}", capture=True)


def function_call_to_domain(function_call: "OpenAIProxyFunctionCall", call_id: str) -> ToolCallRequest:
    """Convert OpenAI proxy function call to domain ToolCallRequest"""
    return ToolCallRequest(
        id=call_id,
        tool_name=function_call.name,
        tool_input_dict=_safely_parsed_arguments(function_call.arguments),
    )


def function_call_from_domain(function_call: ToolCallRequest):
    """Convert domain ToolCallRequest to OpenAI proxy function call"""
    return OpenAIProxyFunctionCall(
        name=function_call.tool_name,
        arguments=json.dumps(function_call.tool_input_dict),
    )


def tool_definition_to_domain(tool_definition: "OpenAIProxyToolDefinition") -> Tool | HostedTool:
    """Convert OpenAI proxy tool definition to domain Tool or HostedTool"""
    if not tool_definition.parameters and not tool_definition.description and tool_definition.name.startswith("@"):
        with contextlib.suppress(ValueError):
            return HostedTool(tool_definition.name)
    return Tool(
        name=tool_definition.name,
        description=tool_definition.description,
        input_schema=tool_definition.parameters or {},
        output_schema={},
        strict=tool_definition.strict,
    )


def tool_call_to_domain(tool_call: "OpenAIProxyToolCall") -> ToolCallRequest:
    """Convert OpenAI proxy tool call to domain ToolCallRequest"""
    return function_call_to_domain(tool_call.function, tool_call.id)


def tool_call_from_domain(tool_call: ToolCallRequest):
    """Convert domain ToolCallRequest to OpenAI proxy tool call"""
    return OpenAIProxyToolCall(
        id=tool_call.id,
        function=function_call_from_domain(tool_call),
    )


def tool_call_delta_from_domain(tool_call: ToolCallRequest):
    return OpenAIProxyToolCallDelta(
        id=tool_call.id,
        index=tool_call.index,
        function=function_call_from_domain(tool_call),
    )


def tool_call_result_message_to_domain(message: "OpenAIProxyMessage") -> Message:
    """Convert tool call result message to domain Message"""
    if message.content is None:
        raise BadRequestError("Content is required when providing a tool call result", capture=True)
    if not message.tool_call_id:
        raise BadRequestError("tool_call_id is required when providing a tool call result", capture=True)
    return Message(
        content=[
            MessageContent(
                tool_call_result=ToolCallResult(
                    id=message.tool_call_id,
                    tool_name="",
                    tool_input_dict={},
                    result=message.content,
                ),
            ),
        ],
        role="user",
    )


def message_content_iterator(message: "OpenAIProxyMessage") -> Iterator[MessageContent]:
    """Iterate over all content in an OpenAI proxy message"""
    # When the role is tool we know that the message only contains the tool call result
    if message.content:
        if isinstance(message.content, str):
            yield MessageContent(text=message.content)
        else:
            for c in message.content:
                yield content_to_domain(c)

    if message.function_call:
        yield MessageContent(tool_call_request=function_call_to_domain(message.function_call, ""))
    if message.tool_calls:
        for t in message.tool_calls:
            yield MessageContent(tool_call_request=tool_call_to_domain(t))


def message_to_domain(message: "OpenAIProxyMessage") -> Message | None:
    """Convert OpenAI proxy message to domain Message"""
    # When the role is tool we know that the message only contains the tool call result
    if message.role == "tool" or message.role == "function":
        return tool_call_result_message_to_domain(message)

    if message.tool_call_id:
        raise BadRequestError("tool_call_id is only allowed when the role is tool", capture=True)

    content = list(message_content_iterator(message))
    if not content:
        # We just received a completely empty message
        # It would be better to raise an error here but OpenAI tolerates empty messages for some reason
        # so we need to accept them as well
        # For now we simply just completly ignore them. Some users used to send empty messages
        # to account for specificites of models/providers (e-g a provider always requiring a user message, etc.)
        # This is handled dynamically by each provider object in WorkflowAI so we should be able to safely skip them
        return None
    try:
        role = _role_mapping[message.role]
    except KeyError:
        raise BadRequestError(f"Unknown role: {message.role}", capture=True) from None

    return Message(content=content, role=role)


def _extract_completion_from_output(output: AgentOutput) -> tuple[str, list[ToolCallRequest] | None]:
    if output.error or not output.messages:
        # That should not happen we should have raised instead
        _log.warning("Error in output conversion", output=output)
        return ("", None)
    txt_content: list[str] = []
    tool_calls: list[ToolCallRequest] = []
    for m in output.messages:
        for c in m.content:
            if c.text:
                txt_content.append(c.text)
            elif c.object:
                txt_content.append(json.dumps(c.object))
            elif c.tool_call_request:
                tool_calls.append(c.tool_call_request)
    return "\n".join(txt_content), tool_calls


def message_from_run(
    run: AgentCompletion,
    deprecated_function: bool,
):
    txt_content, tool_calls = _extract_completion_from_output(run.agent_output)
    return OpenAIProxyMessage(
        role="assistant",
        content=txt_content,
        tool_calls=[tool_call_from_domain(t) for t in tool_calls] if tool_calls and not deprecated_function else None,
        function_call=function_call_from_domain(tool_calls[0]) if tool_calls and deprecated_function else None,
    )


def _safely_parsed_arguments(arguments: str | None) -> dict[str, Any]:
    """Safely parse JSON arguments from a string"""
    if not arguments:
        return {}
    try:
        return json.loads(arguments)
    except json.JSONDecodeError:
        _log.warning("Failed to parse arguments", arguments=arguments)
        return {"arguments": arguments}


def request_tool_choice_to_domain(request: OpenAIProxyChatCompletionRequest):
    tool_choice = request.tool_choice or request.function_call
    if not tool_choice:
        return None

    if isinstance(tool_choice, OpenAIProxyToolChoice):
        return ToolChoiceFunction(name=tool_choice.function.name)
    if isinstance(tool_choice, OpenAIProxyToolChoiceFunction):
        return ToolChoiceFunction(name=tool_choice.name)
    match tool_choice:
        case "auto":
            return "auto"
        case "none":
            return "none"
        case "required":
            return "required"
        case _:
            _log.warning("Received an unsupported tool choice", tool_choice=request.tool_choice)
    return None


def _request_first_system_content(request: OpenAIProxyChatCompletionRequest):
    if request.messages and request.messages[0].role == "system":
        return request.messages[0].first_string_content
    return None


def _request_raw_tool_iterator(request: OpenAIProxyChatCompletionRequest) -> Iterator[OpenAIProxyToolDefinition]:
    if request.tools:
        for t in request.tools:
            if t.type == "function":
                yield t.function
    if request.functions:
        yield from request.functions


_tool_handle_regex = re.compile(r"@[a-z0-9_-]+")


def _extract_tools_from_system_content(content: str):
    for match in _tool_handle_regex.finditer(content):
        handle = match.group(0)
        with contextlib.suppress(ValueError):
            yield HostedTool(handle)


def _request_tool_iterator(request: OpenAIProxyChatCompletionRequest):
    used_tool_names = set[str]()
    for t in _request_raw_tool_iterator(request):
        d = tool_definition_to_domain(t)
        if d.name in used_tool_names:
            raise BadRequestError(f"Tool {d.name} is defined multiple times", capture=True)
        used_tool_names.add(d.name)
        yield d

    if first_content := _request_first_system_content(request):
        for tool in _extract_tools_from_system_content(first_content):
            # Ignoring potential duplicates
            if tool.name in used_tool_names:
                continue
            used_tool_names.add(tool.name)
            yield tool


def request_tools_to_domain(request: OpenAIProxyChatCompletionRequest):
    return list(_request_tool_iterator(request)) or None


def request_messages_to_domain(request: OpenAIProxyChatCompletionRequest):
    previous_message: Message | None = None
    for m in request.messages:
        if m.role == "function":
            # When the message is a function, we are missing the tool call ID.
            # But there must be a tool call request in the previous message and we can just
            # re-use the id
            # So we first make sure that the previous message is an assistant message
            if not previous_message or not previous_message.role == "assistant":
                raise BadRequestError(
                    "Message with role 'function' must be preceded by an assistant message with a function call",
                )
            # That it has a name since we need to match by name
            if not m.name:
                raise BadRequestError("Message with role 'function' must have a name")
            # Then we find the tool call request in the previous message that matches the function name
            previous_request = next(
                (
                    c.tool_call_request
                    for c in previous_message.content
                    if c.tool_call_request and c.tool_call_request.tool_name == m.name
                ),
                None,
            )
            if not previous_request:
                raise BadRequestError(
                    "Message with role 'function' must be preceded by an assistant message with a function call "
                    f"for the function {m.name}",
                )
            # And then we assign the tool_call_id so that it is properly picked up
            # Here the tool_call_id will probably have been autogenerated when instantiating the
            # ToolCallRequestWithID. See ToolCallRequestWithID.post_validate
            m.tool_call_id = previous_request.id
        if converted := message_to_domain(m):
            yield converted
            previous_message = converted


def completion_usage_from_domain(traces: list[Trace]):
    if not traces:
        return None

    prompt_tokens: float = 0
    completion_tokens: float = 0

    for t in traces:
        if not isinstance(t, LLMTrace) or not t.usage:
            continue
        if tc := t.usage.prompt.text_token_count:
            prompt_tokens += tc
        if cc := t.usage.completion.text_token_count:
            completion_tokens += cc

    return OpenAIProxyCompletionUsage(
        completion_tokens=int(completion_tokens),
        prompt_tokens=int(prompt_tokens),
        total_tokens=int(completion_tokens + prompt_tokens),
    )


def completion_choice_from_domain(completion: AgentCompletion, deprecated_function: bool, org: PublicOrganizationData):
    message = message_from_run(completion, deprecated_function)
    if message.tool_calls:
        finish_reason = "tool_calls"
    elif message.function_call:
        finish_reason = "function_call"
    else:
        finish_reason = "stop"

    return OpenAIProxyChatCompletionChoice(
        index=0,
        message=message,
        finish_reason=finish_reason,
        duration_seconds=completion.duration_seconds,
        cost_usd=completion.cost_usd,
        url=completion_url(completion.id),
    )


def completion_response_from_domain(
    completion: AgentCompletion,
    deprecated_function: bool,
    org: PublicOrganizationData,
):
    return OpenAIProxyChatCompletionResponse(
        id=completion.id,
        choices=[completion_choice_from_domain(completion, deprecated_function, org)],
        created=int(completion.created_at.timestamp()),
        model=completion.final_model or "unknown",
        usage=completion_usage_from_domain(completion.traces),
        version_id=completion.version.id,
        metadata=completion.metadata,
    )


def request_apply_to_version(request: OpenAIProxyChatCompletionRequest, version: Version):  # noqa: C901
    if request.temperature is not None:
        version.temperature = request.temperature
    elif version.temperature is None:
        # If the model does not support temperature, we set it to 1
        # Since 1 is the default temperature for OAI
        version.temperature = 1

    if request.top_p is not None:
        version.top_p = request.top_p
    if request.frequency_penalty is not None:
        version.frequency_penalty = request.frequency_penalty
    if request.presence_penalty is not None:
        version.presence_penalty = request.presence_penalty
    if request.parallel_tool_calls is not None:
        version.parallel_tool_calls = request.parallel_tool_calls
    if request.workflowai_provider is not None:
        version.provider = request.workflowai_provider
    if tc := request_tool_choice_to_domain(request):
        version.tool_choice = tc
    if max_tokens := request.max_completion_tokens or request.max_tokens:
        version.max_output_tokens = max_tokens
    if tools := request_tools_to_domain(request):
        version.enabled_tools = tools
    if request.reasoning:
        version.reasoning_effort = request.reasoning.effort
        version.reasoning_budget = request.reasoning.budget
    elif request.reasoning_effort:
        try:
            version.reasoning_effort = ReasoningEffort(request.reasoning_effort)
        except ValueError:
            # Using the default reasoning effort
            # TODO: remove warning since it could be a customer issue
            # We should likely just reject the request
            _log.warning(
                "Client provided an invalid reasoning effort",
                reasoning_effort=request.reasoning_effort,
            )


def use_fallback_to_domain(use_fallback: Literal["auto", "never"] | list[str] | None) -> FallbackOption:
    if isinstance(use_fallback, list):
        try:
            return [get_model_id(m) for m in use_fallback]
        except ValueError as e:
            raise MissingModelError(msg=str(e), model=use_fallback) from None

    return use_fallback

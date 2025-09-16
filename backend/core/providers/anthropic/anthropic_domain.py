from typing import Any, Literal

from httpx import Response
from pydantic import BaseModel
from structlog import get_logger

from core.domain.exceptions import InternalError
from core.domain.file import File
from core.domain.message import MessageDeprecated
from core.domain.tool import Tool as DomainTool
from core.domain.tool_choice import ToolChoice, ToolChoiceFunction
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import (
    MaxTokensExceededError,
    ProviderBadRequestError,
    ProviderInternalError,
    ServerOverloadedError,
    UnknownProviderError,
)
from core.providers._base.streaming_context import ParsedResponse
from core.providers.google.google_provider_domain import (
    internal_tool_name_to_native_tool_call,
)
from core.runners.runner_output import ToolCallRequestDelta

_role_to_map: dict[MessageDeprecated.Role, Literal["user", "assistant"]] = {
    MessageDeprecated.Role.SYSTEM: "user",
    MessageDeprecated.Role.USER: "user",
    MessageDeprecated.Role.ASSISTANT: "assistant",
}

_log = get_logger(__name__)


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class FileSource(BaseModel):
    type: Literal["base64"]
    media_type: str
    data: str


class DocumentContent(BaseModel):
    type: Literal["document"]
    source: FileSource


class ImageContent(BaseModel):
    type: Literal["image"]
    source: FileSource


class ToolUseContent(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict[str, Any]


class ToolResultContent(BaseModel):
    type: Literal["tool_result"]
    tool_use_id: str
    content: str


class ThinkingContent(BaseModel):
    type: Literal["thinking"]
    thinking: str
    signature: str | None = None


class ErrorDetails(BaseModel):
    message: str | None = None
    code: str | None = None
    type: str | None = None

    def _invalid_request_error(self, response: Response | None):
        if not self.message:
            return None

        # By default we want all the fallback mechanic that is provided by UnknownProviderError
        # We can't instantiate a provider bad request error here
        error_cls = UnknownProviderError
        message = self.message
        capture = True

        match message.lower():
            case msg if "invalid base64 data" in msg:
                # We are still capturing this error, it should be caught upstream
                # and not sent to the provider
                error_cls = ProviderBadRequestError
            case msg if "image exceeds" in msg:
                # Not capturing since the umage is just too large
                capture = False
                message = "Image exceeds the maximum size"
                error_cls = ProviderBadRequestError
            case msg if "image does not match the provided media type" in msg:
                # Not capturing since the image is just too large
                capture = False
                message = "Image does not match the provided media type"
                error_cls = ProviderBadRequestError
            case msg if "prompt is too long" in msg:
                error_cls = MaxTokensExceededError
                capture = False
            case msg if "credit balance is too low" in msg:
                # Our Anthropic provider is running out of credits
                error_cls = ProviderInternalError
                capture = True
            case _:
                pass
        return error_cls(
            msg=message,
            response=response,
            capture=capture,
        )

    def to_domain(self, response: Response | None):
        match self.type:
            case "invalid_request_error":
                if e := self._invalid_request_error(response):
                    return e
            case "overloaded_error":
                return ServerOverloadedError(self.message or "unknown", response=response, retry_after=10)

            case _:
                pass
        return UnknownProviderError(self.message or "unknown", response=response)


class AnthropicMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: list[TextContent | DocumentContent | ImageContent | ToolUseContent | ToolResultContent | ThinkingContent]

    @classmethod
    def content_from_domain(cls, file: File):
        if file.data is None:
            raise InternalError("Data is always required for Anthropic", extras={"file": file.model_dump()})
        if file.is_pdf:
            return DocumentContent(
                type="document",
                source=FileSource(type="base64", media_type="application/pdf", data=file.data),
            )
        if file.is_image:
            if not file.content_type:
                raise ProviderBadRequestError(
                    "Content type is required for Anthropic",
                    extras={"file": file.model_dump()},
                    capture=True,
                )
            return ImageContent(
                type="image",
                source=FileSource(type="base64", media_type=file.content_type, data=file.data),
            )

        raise ProviderBadRequestError(
            f"Unsupported file type: {file.content_type}",
            extras={"file": file.model_dump(exclude={"data"})},
            capture=True,
        )

    @classmethod
    def from_domain(cls, message: MessageDeprecated):
        role = _role_to_map[message.role]

        content: list[
            TextContent | DocumentContent | ImageContent | ToolUseContent | ToolResultContent | ThinkingContent
        ] = []
        if message.content:
            content.append(TextContent(type="text", text=message.content))

        content.extend([cls.content_from_domain(file) for file in message.files or []])

        content.extend(
            [
                ToolUseContent(
                    type="tool_use",
                    id=tool.id,
                    name=internal_tool_name_to_native_tool_call(tool.tool_name),
                    input=tool.tool_input_dict,
                )
                for tool in message.tool_call_requests or []
            ],
        )

        content.extend(
            [
                ToolResultContent(
                    type="tool_result",
                    tool_use_id=tool.id,
                    content=str(tool.result) if tool.result else f"Error: {tool.error}",
                )
                for tool in message.tool_call_results or []
            ],
        )
        return cls(content=content, role=role)


class AntToolChoice(BaseModel):
    name: str | None = None  # required if type is tool
    type: Literal["tool", "none", "any", "auto"]
    # Not used yet
    # disable_parallel_tool_use: bool | None = None

    @classmethod
    def from_domain(cls, tool_choice: ToolChoice | None):
        if not tool_choice:
            return None
        if isinstance(tool_choice, ToolChoiceFunction):
            return cls(name=tool_choice.name, type="tool")
        if tool_choice == "required":
            return cls(type="any")
        return cls(type=tool_choice)


class CompletionRequest(BaseModel):
    # https://docs.anthropic.com/en/api/messages#body-messages
    messages: list[AnthropicMessage]
    model: str
    max_tokens: int
    temperature: float
    stream: bool
    tool_choice: AntToolChoice | None = None
    top_p: float | None = None

    # https://docs.anthropic.com/en/api/messages#body-system
    # System could be an object if needed
    system: str | None = None

    class Tool(BaseModel):
        name: str
        description: str | None = None
        input_schema: dict[str, Any]

        @classmethod
        def from_domain(cls, tool: DomainTool):
            # Anthropic does not support strict yet
            return cls(
                name=internal_tool_name_to_native_tool_call(tool.name),
                description=tool.description,
                # When sending an empty schema, anthropic rejects the request
                # It seems that Anthropic only accepts object tool schemas, not sure if
                # we should spend time trying to sanitize the schema or not
                # Anthropic does not validate the actual tool call input
                input_schema=tool.input_schema if tool.input_schema else {"type": "object"},
            )

    # https://docs.anthropic.com/en/api/messages#body-tools
    tools: list[Tool] | None = None

    class Thinking(BaseModel):
        type: Literal["enabled"] = "enabled"  # 'disabled' is never used
        budget_tokens: int

    thinking: Thinking | None = None


class Usage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None

    def to_domain(self) -> LLMUsage:
        return LLMUsage(
            prompt_token_count=self.input_tokens,
            completion_token_count=self.output_tokens,
        )


class ContentBlock(BaseModel):
    type: Literal["text"]
    text: str


class ThinkingBlock(BaseModel):
    type: Literal["thinking"]
    thinking: str
    signature: str | None = None


class CompletionResponse(BaseModel):
    content: list[ContentBlock | ToolUseContent | ThinkingContent]
    usage: Usage
    stop_reason: str | None = None


class TextDelta(BaseModel):
    type: Literal["text_delta"]
    text: str


class ThinkingDelta(BaseModel):
    type: Literal["thinking_delta"]
    thinking: str


class SignatureDelta(BaseModel):
    type: Literal["signature_delta"]
    signature: str


class ContentBlockDelta(BaseModel):
    type: Literal["content_block_delta"]
    index: int
    delta: TextDelta


class ContentBlockStart(BaseModel):
    type: Literal["content_block_start"]
    index: int
    content_block: ContentBlock


class ContentBlockStop(BaseModel):
    type: Literal["content_block_stop"]
    index: int


class MessageStart(BaseModel):
    type: Literal["message_start"]
    message: dict[str, Any]


class MessageDelta(BaseModel):
    type: Literal["message_delta"]
    delta: dict[str, Any]
    usage: Usage | None


class MessageStop(BaseModel):
    type: Literal["message_stop"]


class StopReasonDelta(BaseModel):
    type: Literal["stop_reason_delta"] = "stop_reason_delta"
    stop_reason: str | None = None
    stop_sequence: str | None = None


class ToolUse(BaseModel):
    type: Literal["tool_use"]
    id: str
    name: str
    input: dict[str, Any] | None = None


class InputJsonDelta(BaseModel):
    type: Literal["input_json_delta"]
    partial_json: str


class CompletionChunk(BaseModel):
    """Represents a streaming chunk response from Anthropic"""

    type: Literal[
        "message_start",
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
        "ping",
        "error",
    ]
    # For message_start
    message: dict[str, Any] | None = None
    # For content_block_start
    content_block: ContentBlock | ToolUse | ThinkingBlock | None = None
    # For content_block_delta
    delta: TextDelta | StopReasonDelta | InputJsonDelta | ThinkingDelta | SignatureDelta | None = None
    # For message_delta
    usage: Usage | None = None
    index: int | None = None

    error: ErrorDetails | None = None

    def _parsed_content_block(self) -> ParsedResponse | None:
        match self.content_block:
            case ToolUse():
                return ParsedResponse(
                    tool_call_requests=[
                        ToolCallRequestDelta(
                            id=self.content_block.id,
                            idx=self.index or 0,
                            tool_name=self.content_block.name,
                            arguments="",
                        ),
                    ],
                )
            case ThinkingBlock():
                return ParsedResponse(
                    reasoning=self.content_block.thinking,
                )
            case ContentBlock():
                return ParsedResponse(
                    delta=self.content_block.text,
                )
            case _:
                return None

    def _parsed_delta(self) -> ParsedResponse | None:
        match self.delta:
            case TextDelta():
                return ParsedResponse(
                    delta=self.delta.text,
                )
            case ThinkingDelta():
                return ParsedResponse(
                    reasoning=self.delta.thinking,
                )
            case SignatureDelta():
                return None
            case InputJsonDelta():
                if self.index is None:
                    _log.warning("Received input_json_delta without an index", chunk=self)
                    return None
                return ParsedResponse(
                    tool_call_requests=[
                        ToolCallRequestDelta(
                            id="",
                            idx=self.index,
                            tool_name="",
                            arguments=self.delta.partial_json,
                        ),
                    ],
                )

            case StopReasonDelta():
                if self.delta.stop_reason == "max_tokens":
                    return ParsedResponse(finish_reason="max_context")
                return None
            case None:
                return None

    def to_parsed_response(self) -> ParsedResponse:
        res = self._parsed_content_block()
        if not res:
            res = self._parsed_delta()
        usage = self.usage.to_domain() if self.usage else None
        if not res:
            return ParsedResponse(
                usage=usage,
            )
        return res._replace(usage=usage)


class AnthropicErrorResponse(BaseModel):
    type: Literal["error"]

    error: ErrorDetails | None = None

import json
from typing import Annotated, Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field

from core.domain.exceptions import (
    InternalError,
    UnpriceableRunError,
)
from core.domain.file import File
from core.domain.finish_reason import FinishReason
from core.domain.message import MessageDeprecated
from core.domain.models import Model
from core.domain.tool import Tool as DomainTool
from core.domain.tool_choice import ToolChoice, ToolChoiceFunction
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import FailedGenerationError, ModelDoesNotSupportModeError
from core.providers._base.streaming_context import ParsedResponse
from core.providers.google.google_provider_domain import (
    internal_tool_name_to_native_tool_call,
    native_tool_name_to_internal,
)
from core.runners.runner_output import ToolCallRequestDelta
from core.utils.dicts import TwoWayDict
from core.utils.json_utils import safe_extract_dict_from_json
from core.utils.token_utils import tokens_from_string

OpenAIRole = Literal["system", "user", "assistant"]

AUDIO_MIME_TO_FORMAT_MAP = TwoWayDict[str, str](
    ("audio/mpeg", "mp3"),
    ("audio/wav", "wav"),
    ("audio/wave", "wav"),
    ("audio/mp3", "mp3"),
    ("audio/x-wav", "wav"),
    ("audio/x-mpeg", "mp3"),
)


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImageContent(BaseModel):
    type: Literal["image_url"] = "image_url"

    class URL(BaseModel):
        url: str

    image_url: URL

    @classmethod
    def from_file(cls, file: File) -> Self:
        return cls(image_url=ImageContent.URL(url=file.to_url(default_content_type="image/*")))


class AudioContent(BaseModel):
    type: Literal["input_audio"] = "input_audio"

    class AudioData(BaseModel):
        data: str
        format: str | None

    input_audio: AudioData

    @classmethod
    def from_file(cls, file: File) -> Self:
        if not file.data:
            # NOTE: 'data' should be set upstream.
            raise InternalError("Audio file's data is required.", file=file)
        if not file.content_type:
            raise InternalError("Audio file's content type is required.", file=file)
        try:
            format = AUDIO_MIME_TO_FORMAT_MAP[file.content_type]
        except KeyError:
            raise FailedGenerationError(
                f"Unsupported audio format: {file.content_type}",
                file=file,
                code="unsupported_audio_format",
            ) from None
        return cls(
            input_audio=AudioContent.AudioData(
                data=file.data,
                format=format,
            ),
        )


def parse_tool_call_or_raise(arguments: str | None) -> dict[str, Any] | None:
    if not arguments or arguments == "{}":
        return None
    try:
        args_dict = safe_extract_dict_from_json(arguments)
        if args_dict is None:
            raise ValueError("Can't parse dictionary from tool call arguments")
        return args_dict
    except (ValueError, json.JSONDecodeError):
        raise FailedGenerationError(
            f"Failed to parse tool call arguments: {arguments}",
            code="failed_to_parse_tool_call_arguments",
        ) from None


role_to_openai_map: dict[MessageDeprecated.Role, OpenAIRole] = {
    MessageDeprecated.Role.SYSTEM: "system",
    MessageDeprecated.Role.USER: "user",
    MessageDeprecated.Role.ASSISTANT: "assistant",
}

openai_to_role_map: dict[OpenAIRole, Literal["system", "user", "assistant"] | None] = {
    "system": "system",
    "user": "user",
    "assistant": "assistant",
}


class ToolCallFunction(BaseModel):
    name: str
    arguments: str


class ToolCallResult(BaseModel):
    id: str
    type: Literal["function"]
    function: ToolCallFunction


class ToolFunction(BaseModel):
    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None
    strict: bool = False


class Tool(BaseModel):
    type: Literal["function"]
    function: ToolFunction

    @classmethod
    def from_domain(cls, tool: DomainTool) -> Self:
        return cls(
            type="function",
            function=ToolFunction(
                name=internal_tool_name_to_native_tool_call(tool.name),
                description=tool.description,
                parameters=tool.input_schema,
                strict=tool.strict is True,
            ),
        )


class OpenAIToolMessage(BaseModel):
    role: Literal["tool"]
    tool_call_id: str
    content: str

    @classmethod
    def from_domain(cls, message: MessageDeprecated) -> list[Self]:
        if not message.tool_call_results:
            return []

        return [
            cls(
                tool_call_id=result.id,
                # OpenAI expects a string or array of string here,
                # but we stringify everything to simplify and align bahaviour with other providers.
                # TODO: use stringified_result
                content=str(
                    result.result,
                ),
                role="tool",
            )
            for result in message.tool_call_results
        ]

    def token_count(self, model: Model) -> int:
        # Very basic implementation of the pricing of tool calls messages.
        # We'll need to double check the pricing rules for every provider
        # When working on https://linear.app/workflowai/issue/WOR-3730
        return tokens_from_string(self.content, model)


class OpenAIMessage(BaseModel):
    role: OpenAIRole | None = None
    content: str | list[TextContent | ImageContent | AudioContent]
    tool_calls: list[ToolCallResult] | None = None

    @classmethod
    def from_domain(cls, message: MessageDeprecated, is_system_allowed: bool):
        role = "user" if not is_system_allowed and message.role == "system" else role_to_openai_map[message.role]

        if not message.files and not message.tool_call_requests:
            return cls(content=message.content, role=role)

        content: list[TextContent | ImageContent | AudioContent] = []

        if message.content:
            content.append(TextContent(text=message.content))
        for file in message.files or []:
            if file.is_image is False and file.is_audio is False:
                raise ModelDoesNotSupportModeError("OpenAI only supports image and audio files in messages")
            if file.is_audio:
                content.append(AudioContent.from_file(file))
            else:
                content.append(ImageContent.from_file(file))

        tool_calls: list[ToolCallResult] | None = None
        if message.tool_call_requests:
            tool_calls = [
                ToolCallResult(
                    id=request.id,
                    type="function",
                    function=ToolCallFunction(
                        name=internal_tool_name_to_native_tool_call(request.tool_name),
                        arguments=json.dumps(request.tool_input_dict),
                    ),
                )
                for request in message.tool_call_requests
            ]
        return cls(content=content, role=role, tool_calls=tool_calls)

    def token_count(self, model: Model) -> int:
        token_count = 0

        if isinstance(self.content, str):
            return tokens_from_string(self.content, model)

        for block in self.content:
            if isinstance(block, TextContent):
                token_count += tokens_from_string(block.text, model)
            elif isinstance(block, AudioContent):
                # TODO: we should throw unpriceable run error here
                pass
            else:
                raise UnpriceableRunError("Token counting for files is not implemented")

        return token_count


class TextResponseFormat(BaseModel):
    type: Literal["text"] = "text"


class JSONResponseFormat(BaseModel):
    type: Literal["json_object"] = "json_object"


class OpenAISchema(BaseModel):
    strict: bool = True
    name: str
    json_schema: Annotated[dict[str, Any], Field(serialization_alias="schema")]


class JSONSchemaResponseFormat(BaseModel):
    type: Literal["json_schema"] = "json_schema"
    json_schema: OpenAISchema


class StreamOptions(BaseModel):
    include_usage: bool


ResponseFormat = Annotated[
    JSONResponseFormat | TextResponseFormat | JSONSchemaResponseFormat,
    Field(discriminator="type"),
]


class OAIToolFunctionChoice(BaseModel):
    type: Literal["function"]

    class Function(BaseModel):
        name: str

    function: Function


class CompletionRequest(BaseModel):
    temperature: float | None
    max_completion_tokens: int | None
    model: str
    messages: list[OpenAIMessage | OpenAIToolMessage]
    response_format: ResponseFormat = JSONResponseFormat()
    stream: bool
    stream_options: StreamOptions | None = None
    reasoning_effort: str | None = None
    metadata: dict[str, Any] | None = None
    tools: list[Tool] | None = None
    tool_choice: OAIToolFunctionChoice | Literal["auto", "required", "none"] | None = None
    top_p: float | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    parallel_tool_calls: bool | None = None

    @classmethod
    def tool_choice_from_domain(
        cls,
        tool_choice: ToolChoice | None,
    ) -> OAIToolFunctionChoice | Literal["auto", "required", "none"] | None:
        if isinstance(tool_choice, ToolChoiceFunction):
            return OAIToolFunctionChoice(
                type="function",
                function=OAIToolFunctionChoice.Function(name=tool_choice.name),
            )
        return tool_choice


class _BaseChoice(BaseModel):
    index: int | None = None
    finish_reason: str | None = None

    def parsed_finish_reason(self) -> FinishReason | None:
        if self.finish_reason == "length":
            return "max_context"
        return None


class ChoiceMessage(BaseModel):
    role: OpenAIRole | None = None
    content: None | str | list[TextContent | ImageContent] = None
    refusal: str | None = None
    finish_reason: str | None = None
    tool_calls: list[ToolCallResult] | None = None


class Choice(_BaseChoice):
    message: ChoiceMessage


class StreamedToolCallFunction(BaseModel):
    name: str | None = None
    arguments: str | None = None


class StreamedToolCall(BaseModel):
    index: int
    id: str | None = None
    type: Literal["function"] | None = None
    function: StreamedToolCallFunction

    def to_domain(self) -> ToolCallRequestDelta:
        return ToolCallRequestDelta(
            id=self.id or "",
            idx=self.index,
            tool_name=native_tool_name_to_internal(self.function.name) if self.function.name else "",
            arguments=self.function.arguments or "",
        )


class ChoiceDelta(_BaseChoice):
    class MessageDelta(BaseModel):
        content: str | None = None
        tool_calls: list[StreamedToolCall] | None = None

    delta: MessageDelta


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    class PromptTokensDetails(BaseModel):
        audio_tokens: int = 0
        cached_tokens: int = 0

    prompt_tokens_details: PromptTokensDetails | None = None

    class CompletionTokensDetails(BaseModel):
        audio_tokens: int = 0
        reasoning_tokens: int = 0

    completion_tokens_details: CompletionTokensDetails | None = None

    def to_domain(self) -> LLMUsage:
        return LLMUsage(
            prompt_token_count=self.prompt_tokens,
            prompt_token_count_cached=self.prompt_tokens_details.cached_tokens if self.prompt_tokens_details else None,
            prompt_audio_token_count=self.prompt_tokens_details.audio_tokens if self.prompt_tokens_details else None,
            completion_token_count=self.completion_tokens,
            reasoning_token_count=self.completion_tokens_details.reasoning_tokens
            if self.completion_tokens_details
            else None,
        )


class CompletionResponse(BaseModel):
    id: str | None = None
    choices: list[Choice] = Field(default_factory=list)
    usage: Usage | None = None


class StreamedResponse(BaseModel):
    id: str | None = None
    choices: list[ChoiceDelta] = Field(default_factory=list)
    usage: Usage | None = None

    def to_parsed_response(self) -> ParsedResponse:
        usage = self.usage.to_domain() if self.usage else None
        if not self.choices:
            return ParsedResponse(usage=usage)

        choice = self.choices[0]

        return ParsedResponse(
            delta=choice.delta.content,
            tool_call_requests=[tool_call.to_domain() for tool_call in choice.delta.tool_calls]
            if choice.delta.tool_calls
            else None,
            usage=usage,
            finish_reason=choice.parsed_finish_reason(),
        )


class OpenAIError(BaseModel):
    class Payload(BaseModel):
        code: str | None = None
        message: str
        type: str | None = None
        param: str | None = None

        model_config = ConfigDict(extra="allow")

    error: Payload

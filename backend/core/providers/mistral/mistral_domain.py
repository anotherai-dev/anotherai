import hashlib
import json
import re
from typing import Annotated, Any, Literal, Self

from pydantic import AliasChoices, BaseModel, BeforeValidator, ConfigDict, Field

from core.domain.exceptions import UnpriceableRunError
from core.domain.file import File
from core.domain.finish_reason import FinishReason
from core.domain.message import MessageDeprecated
from core.domain.models import Model
from core.domain.tool import Tool
from core.domain.tool_call import ToolCallRequest
from core.domain.tool_choice import ToolChoice, ToolChoiceFunction
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.streaming_context import ParsedResponse
from core.providers.google.google_provider_domain import (
    internal_tool_name_to_native_tool_call,
    native_tool_name_to_internal,
)
from core.runners.runner_output import ToolCallRequestDelta
from core.utils.json_utils import safe_extract_dict_from_json
from core.utils.token_utils import tokens_from_string


class ResponseFormat(BaseModel):
    type: Literal["json_object", "text"] = "json_object"


class MistralTool(BaseModel):
    type: Literal["function"]

    class Function(BaseModel):
        name: str
        description: str = ""
        parameters: dict[str, Any] = Field(default_factory=dict)
        strict: bool | None = None

    function: Function

    @classmethod
    def from_domain(cls, tool: Tool):
        return cls(
            type="function",
            function=cls.Function(
                name=internal_tool_name_to_native_tool_call(tool.name),
                description=tool.description or "",
                parameters=tool.input_schema,
                strict=tool.strict,
            ),
        )


class TextChunk(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImageURL(BaseModel):
    url: str


class ImageURLChunk(BaseModel):
    type: Literal["image_url"] = "image_url"
    image_url: ImageURL

    @classmethod
    def from_file(cls, file: File) -> Self:
        return cls(image_url=ImageURL(url=file.to_url(default_content_type="image/*")))


class DocumentURLChunk(BaseModel):
    type: Literal["document_url"] = "document_url"
    document_url: str


_role_to_map: dict[MessageDeprecated.Role, Literal["user", "assistant", "system"]] = {
    MessageDeprecated.Role.SYSTEM: "system",
    MessageDeprecated.Role.USER: "user",
    MessageDeprecated.Role.ASSISTANT: "assistant",
}


def _sanitize_tool_id(v: str | None) -> str | None:
    if not v:
        return None
    if re.match(r"^[a-zA-Z0-9_-]{9}$", v) is not None:
        return v
    # Otherwise we hash the tool call id as a hex and take the first 9 characters
    return hashlib.sha256(v.encode()).hexdigest()[:9]


MistralToolID = Annotated[str, BeforeValidator(_sanitize_tool_id)]


class MistralToolCall(BaseModel):
    id: MistralToolID | None = None
    type: Literal["function"] = "function"

    class Function(BaseModel):
        name: str
        arguments: dict[str, Any] | str

    function: Function
    index: int | None = None

    @classmethod
    def from_domain(cls, tool_call: ToolCallRequest):
        return cls(
            id=tool_call.id,
            function=cls.Function(
                name=internal_tool_name_to_native_tool_call(tool_call.tool_name),
                arguments=tool_call.tool_input_dict,
            ),
        )

    def to_delta(self) -> ToolCallRequestDelta:
        return ToolCallRequestDelta(
            id=self.id or "",
            idx=self.index or 0,
            tool_name=native_tool_name_to_internal(self.function.name) if self.function.name else "",
            arguments=self.function.arguments
            if isinstance(self.function.arguments, str)
            else json.dumps(self.function.arguments),
        )


class MistralAIMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str | list[TextChunk | ImageURLChunk | DocumentURLChunk]
    tool_calls: list[MistralToolCall] | None = None

    @classmethod
    def from_domain(cls, message: MessageDeprecated):
        # Since Mistral domain has not been converted to use native tools in messages yet.

        role = _role_to_map[message.role]
        if not message.files:
            content: str | list[TextChunk | ImageURLChunk | DocumentURLChunk] = message.content
        else:
            content = []
            if message.content:
                content.append(TextChunk(text=message.content))
            for file in message.files or []:
                if file.is_image:
                    content.append(ImageURLChunk.from_file(file))
                else:
                    content.append(DocumentURLChunk(document_url=file.to_url(default_content_type="application/pdf")))

        return cls(
            content=content,
            role=role,
            tool_calls=[MistralToolCall.from_domain(tool_call) for tool_call in message.tool_call_requests]
            if message.tool_call_requests
            else None,
        )

    def token_count(self, model: Model) -> int:
        token_count = 0

        if isinstance(self.content, str):
            return tokens_from_string(self.content, model)

        for block in self.content:
            if isinstance(block, TextChunk):
                token_count += tokens_from_string(block.text, model)
            else:
                raise UnpriceableRunError("Token counting for files is not implemented")

        return token_count


MistralToolChoiceEnum = Literal["auto", "none", "required", "any"]


class MistralToolChoice(BaseModel):
    type: Literal["function"] = "function"

    class FunctionName(BaseModel):
        name: str

    function: FunctionName


# TODO: merge with MistralMessage above
class MistralToolMessage(BaseModel):
    role: Literal["tool"]
    tool_call_id: MistralToolID
    name: str
    content: str

    @classmethod
    def from_domain(cls, message: MessageDeprecated) -> list[Self]:
        ret: list[Self] = []
        for tool in message.tool_call_results or []:
            result = safe_extract_dict_from_json(tool.result)
            if not result:
                result = {"result": tool.result}
            ret.append(
                cls(
                    role="tool",
                    tool_call_id=tool.id,
                    name=internal_tool_name_to_native_tool_call(tool.tool_name),
                    content=json.dumps(result),
                ),
            )
        return ret

    def token_count(self, model: Model) -> int:
        # Very basic implementation of the pricing of tool calls messages.
        # We'll need to double check the pricing rules for every provider
        # When working on https://linear.app/workflowai/issue/WOR-3730
        return tokens_from_string(self.content, model)


# https://docs.mistral.ai/api/#tag/chat/operation/chat_completion_v1_chat_completions_post
class CompletionRequest(BaseModel):
    model: str
    temperature: float = 0.3
    top_p: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    stop: str | None = None
    random_seed: int | None = None
    messages: list[MistralAIMessage | MistralToolMessage]
    response_format: ResponseFormat = Field(default_factory=ResponseFormat)
    tools: list[MistralTool] | None = None
    tool_choice: MistralToolChoiceEnum | MistralToolChoice | None = None
    safe_prompt: bool | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None
    parallel_tool_calls: bool | None = None

    @classmethod
    def tool_choice_from_domain(
        cls,
        tool_choice: ToolChoice | None,
    ) -> MistralToolChoiceEnum | MistralToolChoice | None:
        if not tool_choice:
            return None
        if isinstance(tool_choice, ToolChoiceFunction):
            return MistralToolChoice(type="function", function=MistralToolChoice.FunctionName(name=tool_choice.name))
        return tool_choice


class _ThinkingContent(BaseModel):
    text: str | None = None


class _AssistantMessageContent(BaseModel):
    thinking: list[_ThinkingContent] | None = None
    text: str | None = None


class _WithContentMixin(BaseModel):
    content: str | list[_AssistantMessageContent] | None = None

    def thinking_iter(self):
        if not isinstance(self.content, list):
            return
        for c in self.content:
            if c.thinking:
                for t in c.thinking:
                    if t.text:
                        yield t.text

    def text_iter(self):
        if not self.content:
            return
        if isinstance(self.content, str):
            yield self.content
            return
        for c in self.content:
            if c.text:
                yield c.text

    def text_joined(self):
        val = list(self.text_iter())
        return "\n".join(val) if val else None

    def thinking_joined(self):
        val = list(self.thinking_iter())
        return "\n".join(val) if val else None


class AssistantMessage(_WithContentMixin):
    tool_calls: list[MistralToolCall] | None = None
    # prefix: bool = False
    # role: Literal["assistant"] = "assistant"


FinishReasonEnum = Literal["stop", "length", "model_length", "error", "tool_calls"]


class ChatCompletionChoice(BaseModel):
    # index: int
    message: AssistantMessage
    finish_reason: str | FinishReasonEnum | None = None


class Usage(BaseModel):
    # Values are supposedly not optional, just adding None to be safe
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    def to_domain(self):
        return LLMUsage(
            prompt_token_count=self.prompt_tokens,
            completion_token_count=self.completion_tokens,
        )


class CompletionResponse(BaseModel):
    # Since we validate the response, not adding fields we do not use
    # id: str
    # object: str
    # model: str
    usage: Usage
    created: int
    choices: list[ChatCompletionChoice]


class MistralError(BaseModel):
    # loc: list[str | int] | None = None
    message: str | None = Field(default=None, validation_alias=AliasChoices("message", "msg"))
    type: str | None = None
    # param: str | None = None
    # code: str | None = None

    class _Detail(BaseModel):
        type: str | None = None
        msg: str | None = None

    # Sometimes we get a list of details instead of having the
    # message and type at the root
    detail: list[_Detail] | None = None

    model_config = ConfigDict(extra="allow")

    @property
    def actual_type(self) -> str | None:
        if self.detail:
            return self.detail[0].type
        return self.type

    @property
    def actual_message(self) -> str | None:
        if self.detail:
            return self.detail[0].msg
        return self.message


class DeltaMessage(_WithContentMixin):
    role: str | None = None

    tool_calls: list[MistralToolCall] | None = None


class CompletionResponseStreamChoice(BaseModel):
    # index: int
    delta: DeltaMessage | None = None
    finish_reason: FinishReasonEnum | str | None = None

    def parsed_finish_reason(self) -> FinishReason | None:
        if self.finish_reason == "length":
            return "max_context"
        return None


class CompletionChunk(BaseModel):
    # id: str
    # object: str
    # created: int
    # model: str
    usage: Usage | None = None
    choices: list[CompletionResponseStreamChoice] | None = None

    def to_parsed_response(self) -> ParsedResponse:
        usage = self.usage.to_domain() if self.usage else None
        if not self.choices:
            return ParsedResponse(usage=usage)

        choice = self.choices[0]
        if not choice.delta:
            return ParsedResponse(usage=usage)

        return ParsedResponse(
            delta=choice.delta.text_joined(),
            tool_call_requests=[tool_call.to_delta() for tool_call in choice.delta.tool_calls]
            if choice.delta.tool_calls
            else None,
            usage=usage,
            finish_reason=choice.parsed_finish_reason(),
            reasoning=choice.delta.thinking_joined(),
        )

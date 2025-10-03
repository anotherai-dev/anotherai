from collections.abc import Mapping

# Import conversion functions
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel, to_pascal
from structlog import get_logger

# For the remaining types that may be circular imports, use TYPE_CHECKING
from core.domain.cache_usage import CacheUsage
from core.domain.consts import METADATA_KEY_INTEGRATION
from core.domain.models.providers import Provider
from core.domain.reasoning_effort import ReasoningEffort

# Goal of these models is to be as flexible as possible
# We definitely do not want to reject calls without being sure
# for example if OpenAI decides to change their API or we missed some param in the request
#
# Also all models have extra allowed so we can track extra values that we may have missed

_log = get_logger(__name__)

CHAT_COMPLETION_REQUEST_UNSUPPORTED_FIELDS = {
    "logit_bias",
    "logprobs",
    "modalities",
    "prediction",
    "seed",
    "stop",
    "top_logprobs",
    "web_search_options",
}


class OpenAIAudioInput(BaseModel):
    data: str
    format: str


class OpenAIProxyImageURL(BaseModel):
    url: str
    detail: Literal["low", "high", "auto"] | None = None


class OpenAIProxyFile(BaseModel):
    file_data: str


class OpenAIProxyContent(BaseModel):
    type: str
    text: str | None = None
    image_url: OpenAIProxyImageURL | None = None
    input_audio: OpenAIAudioInput | None = None
    file: OpenAIProxyFile | None = None


class OpenAIProxyFunctionCall(BaseModel):
    name: str
    arguments: str | None = None


class OpenAIProxyToolDefinition(BaseModel):
    description: str | None = None
    name: str = Field(
        description="The name of the tool. A tool can also reference a hosted WorkflowAI tool. Hosted "
        "WorkflowAI tools should always have a name that starts with `@` and have no description or parameters.",
    )
    parameters: dict[str, Any] | None = None
    strict: bool | None = None

    model_config = ConfigDict(extra="allow")


class OpenAIProxyTool(BaseModel):
    type: Literal["function"]
    function: OpenAIProxyToolDefinition

    model_config = ConfigDict(extra="allow")


class OpenAIProxyToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: OpenAIProxyFunctionCall  # Reusing FunctionCall structure for name/arguments


class OpenAIProxyToolCallDelta(OpenAIProxyToolCall):
    index: int


class OpenAIProxyMessage(BaseModel):
    content: list[OpenAIProxyContent] | str | None = None
    name: str | None = None
    role: str

    tool_calls: list[OpenAIProxyToolCall] | None = None
    function_call: OpenAIProxyFunctionCall | None = None  # Deprecated
    tool_call_id: str | None = None

    @property
    def first_string_content(self) -> str | None:
        if isinstance(self.content, str):
            return self.content
        if self.content and self.content[0].type == "text":
            return self.content[0].text
        return None


class OpenAIProxyResponseFormat(BaseModel):
    type: str

    class JsonSchema(BaseModel):
        schema_: dict[str, Any] = Field(alias="schema")

    json_schema: JsonSchema | None = None

    model_config = ConfigDict(extra="allow")


class OpenAIProxyStreamOptions(BaseModel):
    include_usage: bool | None = None

    valid_json_chunks: bool | None = Field(
        default=None,
        description="Whether to only send valid JSON chunks when streaming. When set to true, the delta aggregation "
        "is performed by WorkflowAI and only valid aggregated JSON strings are sent in place of the content delta. "
        "valid_json_chunks is only relevant when using a json based response format (either `json_object` or "
        "`json_schema`).",
    )

    model_config = ConfigDict(extra="allow")


class OpenAIProxyToolChoiceFunction(BaseModel):
    name: str


class OpenAIProxyToolChoice(BaseModel):
    type: Literal["function"]
    function: OpenAIProxyToolChoiceFunction


class OpenAIProxyPredicatedOutput(BaseModel):
    content: str | list[OpenAIProxyContent]
    type: str


class OpenAIProxyWebSearchOptions(BaseModel):
    search_context_size: str

    # TODO:
    user_location: dict[str, Any] | None = None


def _alias_generator(field_name: str):
    aliases = {field_name, to_pascal(field_name), to_camel(field_name)}
    aliases.remove(field_name)
    return AliasChoices(field_name, *aliases)


class _OpenAIProxyExtraFields(BaseModel):
    input: dict[str, Any] | None = Field(
        default=None,
        description="An input to template the messages with.This field is not defined by the default OpenAI api."
        "When provided, an input schema is generated and the messages are used as a template.",
        validation_alias=_alias_generator("input"),
    )

    provider: str | None = Field(
        default=None,
        description="A specific provider to use for the request. When provided, multi provider fallback is disabled."
        "The attribute is ignored if the provider is not supported.",
        validation_alias=_alias_generator("provider"),
    )

    agent_id: str | None = Field(
        default=None,
        description="The id of the agent to use for the request. If not provided, the default agent is used.",
        validation_alias=_alias_generator("agent_id"),
    )

    use_cache: CacheUsage | None = Field(
        default=None,
        validation_alias=_alias_generator("use_cache"),
    )

    use_fallback: Literal["auto", "never"] | list[str] | None = Field(
        default=None,
        description="A way to configure the fallback behavior",
        validation_alias=_alias_generator("use_fallback"),
    )

    conversation_id: str | None = Field(
        default=None,
        description="The conversation id to associate with the run. If not provided, WorkflowAI will attempt to "
        "match the message history to an existing conversation. If no conversation is found, a new "
        "conversation will be created.",
        validation_alias=_alias_generator("conversation_id"),
    )

    deployment_id: str | None = Field(
        default=None,
        # TODO: describe if the values in the code override the deployment or if the deployment is the priority
        # We could also have the deployment id in the model: `deployments/<deployment_id>` which would clarify
        # that the deployment is a priority
        description="The deployment id to use for the request",
    )


class OpenAIProxyReasoning(BaseModel):
    """A custom reasoning object that allows setting an effort or a budget"""

    effort: ReasoningEffort | None = None
    budget: int | None = None

    @model_validator(mode="after")
    def validate_effort_or_budget(self):
        if self.effort is None and self.budget is None:
            raise ValueError("Either effort or budget must be set")
        return self


class OpenAIProxyChatCompletionRequest(_OpenAIProxyExtraFields):
    messages: list[OpenAIProxyMessage] = Field(default_factory=list)
    model: str
    frequency_penalty: float | None = None
    function_call: str | OpenAIProxyToolChoiceFunction | None = None
    functions: list[OpenAIProxyToolDefinition] | None = None

    logit_bias: dict[str, float] | None = None
    logprobs: bool | None = None

    max_completion_tokens: int | None = None
    max_tokens: int | None = None
    metadata: dict[str, Any] | None = None
    modalities: list[Literal["text", "audio"]] | None = None
    n: int | None = None
    parallel_tool_calls: bool | None = None
    prediction: OpenAIProxyPredicatedOutput | None = None
    presence_penalty: float | None = None
    reasoning_effort: str | None = None
    response_format: OpenAIProxyResponseFormat | None = None

    seed: int | None = None
    service_tier: str | None = None
    stop: str | list[str] | None = None
    store: bool | None = None
    stream: bool | None = None
    stream_options: OpenAIProxyStreamOptions | None = None
    temperature: float | None = None  # default OAI temperature differs from own default
    tool_choice: str | OpenAIProxyToolChoice | None = None
    tools: list[OpenAIProxyTool] | None = None
    top_logprobs: int | None = None
    top_p: float | None = None
    user: str | None = None
    web_search_options: OpenAIProxyWebSearchOptions | None = None

    reasoning: OpenAIProxyReasoning | None = None

    model_config = ConfigDict(extra="allow")

    def register_metadata(self, d: dict[str, Any]):
        if self.metadata:
            self.metadata = {**self.metadata, **d}
        else:
            self.metadata = d

    def full_metadata(self, headers: Mapping[str, Any]) -> dict[str, Any] | None:
        base = self.metadata or {}
        base[METADATA_KEY_INTEGRATION] = "openai_chat_completions"
        if self.user:
            base["user"] = self.user
        if browser_agent := headers.get("user-agent"):
            base["user-agent"] = browser_agent
        return base

    @property
    def workflowai_provider(self) -> Provider | None:
        if self.provider:
            try:
                return Provider(self.provider)
            except ValueError:
                # Logging for now just in case
                _log.warning("Received an unsupported provider", extra={"provider": self.provider})
                return None
        return None


# --- Response Models ---


class OpenAIProxyCompletionUsage(BaseModel):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int


class _ExtraChoiceAttributes(BaseModel):
    cost_usd: float | None = Field(description="The cost of the completion in USD, WorkflowAI specific")
    duration_seconds: float | None = Field(description="The duration of the completion in seconds, WorkflowAI specific")
    url: str = Field(description="The URL of the run")


type FinishReason = Literal["stop", "length", "tool_calls", "content_filter", "function_call"]


class OpenAIProxyChatCompletionChoice(_ExtraChoiceAttributes):
    finish_reason: FinishReason
    index: int
    message: OpenAIProxyMessage


class OpenAIProxyChatCompletionResponse(BaseModel):
    id: str
    choices: list[OpenAIProxyChatCompletionChoice]
    created: int  # Unix timestamp
    model: str
    system_fingerprint: str | None = None
    object: Literal["chat.completion"] = "chat.completion"
    usage: OpenAIProxyCompletionUsage | None = None

    version_id: str = Field(description="The version id of the completion, WorkflowAI specific")
    metadata: dict[str, Any] | None = Field(description="Metadata about the completion, WorkflowAI specific")


class OpenAIProxyChatCompletionChunkDelta(BaseModel):
    content: str | None
    function_call: OpenAIProxyFunctionCall | None  # Deprecated
    tool_calls: list[OpenAIProxyToolCallDelta] | None
    role: Literal["user", "assistant", "system", "tool"] | None


class OpenAIProxyChatCompletionChunkChoice(BaseModel):
    delta: OpenAIProxyChatCompletionChunkDelta
    index: int


class OpenAIProxyChatCompletionChunkChoiceFinal(OpenAIProxyChatCompletionChunkChoice, _ExtraChoiceAttributes):
    usage: OpenAIProxyCompletionUsage | None
    finish_reason: FinishReason | None


class OpenAIProxyChatCompletionChunk(BaseModel):
    id: str
    choices: list[OpenAIProxyChatCompletionChunkChoice | OpenAIProxyChatCompletionChunkChoiceFinal]
    created: int
    model: str
    system_fingerprint: str | None = None
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    usage: OpenAIProxyCompletionUsage | None = None

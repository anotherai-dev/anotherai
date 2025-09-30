import re
from collections.abc import AsyncIterator
from typing import Any, cast, override

import httpx
from pydantic import BaseModel
from structlog import get_logger

from core.domain.file import File
from core.domain.message import MessageDeprecated
from core.domain.models import Model, Provider
from core.domain.models.utils import get_model_data
from core.domain.tool import Tool
from core.domain.tool_call import ToolCallRequest
from core.providers._base.httpx_provider import HTTPXProvider
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import (
    MaxTokensExceededError,
    ModelDoesNotSupportModeError,
    ProviderBadRequestError,
    ProviderInternalError,
    UnknownProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers._base.streaming_context import ParsedResponse
from core.providers.amazon_bedrock.amazon_bedrock_config import AmazonBedrockConfig
from core.providers.amazon_bedrock.amazon_bedrock_domain import (
    AmazonBedrockMessage,
    AmazonBedrockSystemMessage,
    BedrockError,
    BedrockToolConfig,
    CompletionRequest,
    CompletionResponse,
    StreamedResponse,
    message_or_system,
)
from core.providers.google.google_provider_domain import (
    native_tool_name_to_internal,
)

_log = get_logger(__name__)


# The models below do not support streaming when tools are enabled
_NON_STREAMING_WITH_TOOLS_MODELS = {
    Model.MISTRAL_LARGE_2_2407,
}

DEFAULT_MAX_TOKENS_BUFFER = 8192


class AmazonBedrockProvider(HTTPXProvider[AmazonBedrockConfig, CompletionResponse]):
    @override
    def _build_request(self, messages: list[MessageDeprecated], options: ProviderOptions, stream: bool) -> BaseModel:
        system_message: AmazonBedrockSystemMessage | None = None
        user_messages: list[AmazonBedrockMessage] = []

        for message in messages:
            if message.role == MessageDeprecated.Role.USER:
                user_messages.append(AmazonBedrockMessage.from_domain(message))
            if message.role == MessageDeprecated.Role.ASSISTANT:
                user_messages.append(AmazonBedrockMessage.from_domain(message))
            if message.role == MessageDeprecated.Role.SYSTEM:
                if system_message is not None:
                    _log.warning(
                        "Only one system message is allowed in Amazon Bedrock",
                        system_message=system_message.text,
                        new_system_message=message.content,
                    )
                    system_message.text += message.content
                system_message = AmazonBedrockSystemMessage.from_domain(message)

        model_data = get_model_data(options.model)
        thinking_budget = options.final_reasoning_budget(model_data.reasoning)
        thinking_config = (
            None
            if thinking_budget is None
            else CompletionRequest.AdditionalModelRequestFields(
                thinking=CompletionRequest.AdditionalModelRequestFields.Thinking(
                    type="enabled",
                    budget_tokens=thinking_budget,
                ),
            )
        )

        max_tokens = None
        if options.max_tokens:
            max_tokens = options.max_tokens + (thinking_budget or 0)

            if model_data.max_tokens_data.max_output_tokens:
                # Make sure we never exceed the model's max output tokens
                max_tokens = min(max_tokens, model_data.max_tokens_data.max_output_tokens)

        elif thinking_budget:
            # If no max_tokens is provided in the options but we have a thinking budget, we need to set a max_tokens that is higher than the thinking budget.s
            if model_data.max_tokens_data.max_output_tokens:
                max_tokens = min(
                    thinking_budget + DEFAULT_MAX_TOKENS_BUFFER,
                    model_data.max_tokens_data.max_output_tokens,
                )
            else:
                max_tokens = thinking_budget + DEFAULT_MAX_TOKENS_BUFFER

        return CompletionRequest(
            system=[system_message] if system_message else [],
            messages=user_messages,
            inferenceConfig=CompletionRequest.InferenceConfig(
                temperature=options.temperature,
                maxTokens=max_tokens,
                topP=options.top_p,
                # Presence and frequency penalties are not yet supported by Amazon Bedrock
            ),
            toolConfig=BedrockToolConfig.from_domain(options.enabled_tools, options.tool_choice),
            additionalModelRequestFields=thinking_config,
        )

    @classmethod
    @override
    def requires_downloading_file(cls, file: File, model: Model) -> bool:
        return True

    def _raw_prompt(self, request_json: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract the raw prompt from the request JSON"""
        return request_json["system"] + request_json["messages"]

    @override
    async def _request_headers(self, request: dict[str, Any], url: str, model: Model) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.api_key}",
        }

    @override
    def _request_url(self, model: Model, stream: bool) -> str:
        suffix = "converse-stream" if stream else "converse"
        region = self._config.region_for_model(model)
        url_model = self._config.id_for_model(model)

        return f"https://bedrock-runtime.{region}.amazonaws.com/model/{url_model}/{suffix}"

    @override
    def _response_model_cls(self) -> type[CompletionResponse]:
        return CompletionResponse

    @override
    def _extract_content_str(self, response: CompletionResponse) -> str:
        has_tool_use = False
        for content in response.output.message.content:
            if content.toolUse:
                has_tool_use = True
            if content.text:
                return content.text

        if not has_tool_use:
            self.logger.warning("Empty content found in response", extra={"response": response.model_dump()})

        return ""

    @override
    def _extract_usage(self, response: CompletionResponse) -> LLMUsage | None:
        return response.usage.to_domain()

    @override
    def _extract_reasoning_steps(self, response: CompletionResponse) -> str | None:
        """Extract reasoning steps from thinking content blocks in the response"""
        return (
            "\n\n".join(
                (content.thinking.thinking for content in response.output.message.content if content.thinking),
            )
            or None
        )

    @override
    @classmethod
    def required_env_vars(cls) -> list[str]:
        return ["AWS_BEDROCK_API_KEY"]

    @override
    @classmethod
    def name(cls) -> Provider:
        return Provider.AMAZON_BEDROCK

    @override
    @classmethod
    def _default_config(cls, index: int) -> AmazonBedrockConfig:
        return AmazonBedrockConfig.from_env(index)

    def _raise_for_message_if_needed(self, raw: str, response: httpx.Response | None = None):
        try:
            bedrock_error = BedrockError.model_validate_json(raw)
        except Exception:  # noqa: BLE001
            _log.warning("Failed to validate Bedrock error", raw=raw, exc_info=True)
            return

        if not bedrock_error.message:
            return

        lower_msg = bedrock_error.message.lower()

        capture: bool | None = None
        match lower_msg:
            case lower_msg if "input is too long for requested model" in lower_msg or re.search(
                r"too large for model with \d+ maximum context length",
                lower_msg,
            ):
                error_cls = MaxTokensExceededError

            case lower_msg if "bedrock is unable to process your request" in lower_msg:
                error_cls = ProviderInternalError
            case lower_msg if "unexpected error" in lower_msg:
                error_cls = ProviderInternalError
            case lower_msg if "image exceeds max pixels allowed" in lower_msg:
                error_cls = ProviderBadRequestError
            case lower_msg if "provided image does not match the specified image format" in lower_msg:
                error_cls = ProviderBadRequestError
                # Capturing for now, this could happen if we do not properly detect the image format
                capture = True
            case lower_msg if "too many images and documents" in lower_msg:
                error_cls = ProviderBadRequestError
            case lower_msg if re.search(r"model does( not|n't) support tool use", lower_msg):
                error_cls = ModelDoesNotSupportModeError
                capture = True
            case _:
                return
        prefix = "The model returned the following errors: "
        raise error_cls(msg=bedrock_error.message.removeprefix(prefix), response=response, capture=capture)

    @override
    async def wrap_sse(self, raw: AsyncIterator[bytes], termination_chars: bytes = b"") -> AsyncIterator[bytes]:
        from botocore.eventstream import EventStreamBuffer  # pyright: ignore [reportMissingTypeStubs]

        event_stream_buffer = EventStreamBuffer()
        async for chunk in raw:
            event_stream_buffer.add_data(chunk)  # pyright: ignore [reportUnknownMemberType]
            for event in event_stream_buffer:
                payload = cast(bytes, event.payload)
                if header := event.headers.get(":exception-type", None):  # pyright: ignore [reportUnknownMemberType, reportUnknownVariableType]
                    raw_msg = payload.decode("utf-8")
                    self._raise_for_message_if_needed(raw_msg)
                    raise UnknownProviderError(msg=raw_msg, extra={"header": header})
                yield payload

    @override
    def _extract_stream_delta(self, sse_event: bytes) -> ParsedResponse:
        raw = StreamedResponse.model_validate_json(sse_event)
        return raw.to_parsed_response()

    def supports_model(self, model: Model) -> bool:
        try:
            # Can vary based on the models declared in 'AWS_BEDROCK_MODEL_REGION_MAP
            return model in self._config.available_model_x_region_map
        except ValueError:
            return False

    @override
    def _unknown_error_message(self, response: httpx.Response):
        return response.text

    def _handle_error_status_code(self, response: httpx.Response):
        self._raise_for_message_if_needed(response.text, response)

        super()._handle_error_status_code(response)

    def _compute_prompt_token_count(
        self,
        messages: list[dict[str, Any]],
        model: Model,
    ) -> float:
        # TODO: Double check the truthfulness of those boilerplates token counts
        # Those are based on OpenAI's ones
        # See: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        boilerplate_tokens: int = 3
        per_message_boilerplate_tokens: int = 4

        token_count: int = boilerplate_tokens

        for message in messages:
            token_count += per_message_boilerplate_tokens

            domain_message = message_or_system(message)
            message_token_count = domain_message.token_count(model)
            token_count += message_token_count

        return token_count

    @override
    async def _compute_prompt_audio_token_count(
        self,
        messages: list[dict[str, Any]],
    ):
        return 0, None

    @classmethod
    def _extract_native_tool_calls(cls, response: CompletionResponse) -> list[ToolCallRequest]:
        choice = response.output.message

        tool_calls: list[ToolCallRequest] = [
            ToolCallRequest(
                id=content.toolUse.toolUseId,
                tool_name=native_tool_name_to_internal(content.toolUse.name),
                tool_input_dict=content.toolUse.input,
            )
            for content in choice.content or []
            if content.toolUse
        ]
        return tool_calls

    def is_streamable(self, model: Model, enabled_tools: list[Tool] | None = None) -> bool:
        return not (enabled_tools and model in _NON_STREAMING_WITH_TOOLS_MODELS)

    # Bedrock does not expose rate limits

    @override
    def default_model(self) -> Model:
        default_model = Model.CLAUDE_3_7_SONNET_20250219
        if default_model not in self._config.resource_id_x_model_map:
            try:
                return next(m for m in self._config.resource_id_x_model_map)
            except StopIteration:
                return Model.CLAUDE_3_5_SONNET_20240620
        return default_model

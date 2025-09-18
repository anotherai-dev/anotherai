import copy
from typing import Any, Literal, override

from httpx import Response
from pydantic import BaseModel, ValidationError

from core.domain.file import File
from core.domain.message import MessageDeprecated
from core.domain.models import Model, Provider
from core.domain.models.model_data import ModelData
from core.domain.models.utils import get_model_data
from core.domain.tool_call import ToolCallRequest
from core.providers._base.httpx_provider import HTTPXProvider
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import (
    FailedGenerationError,
    InvalidGenerationError,
    MaxTokensExceededError,
    MissingModelError,
    UnknownProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers._base.streaming_context import ParsedResponse
from core.providers._base.utils import get_provider_config_env
from core.providers.fireworks.fireworks_domain import (
    CompletionRequest,
    CompletionResponse,
    FireworksAIError,
    FireworksMessage,
    FireworksTool,
    FireworksToolFunction,
    FireworksToolMessage,
    JSONResponseFormat,
    StreamedResponse,
    TextResponseFormat,
)
from core.providers.google.google_provider_domain import (
    internal_tool_name_to_native_tool_call,
    native_tool_name_to_internal,
)
from core.providers.openai.openai_domain import parse_tool_call_or_raise

_NAME_OVERRIDE_MAP = {
    Model.LLAMA_3_3_70B: "accounts/fireworks/models/llama-v3p3-70b-instruct",
    Model.LLAMA_3_2_3B_PREVIEW: "accounts/fireworks/models/llama-v3p2-3b-instruct",
    Model.LLAMA_3_2_3B: "accounts/fireworks/models/llama-v3p2-3b-instruct",
    Model.LLAMA_3_2_11B_VISION: "accounts/fireworks/models/llama-v3p2-11b-vision-instruct",
    Model.LLAMA_3_2_90B_VISION_PREVIEW: "accounts/fireworks/models/llama-v3p2-90b-vision-instruct",
    Model.LLAMA_3_1_8B: "accounts/fireworks/models/llama-v3p1-8b-instruct",
    Model.QWEN_QWQ_32B_PREVIEW: "accounts/fireworks/models/qwen-qwq-32b-preview",
    Model.QWEN3_235B_A22B: "accounts/fireworks/models/qwen3-235b-a22b",
    Model.QWEN3_30B_A3B: "accounts/fireworks/models/qwen3-30b-a3b",
    Model.MIXTRAL_8X7B_32768: "accounts/fireworks/models/mixtral-8x7b-instruct",
    Model.LLAMA3_70B_8192: "accounts/fireworks/models/llama-v3-70b-instruct",
    Model.LLAMA3_8B_8192: "accounts/fireworks/models/llama-v3-8b-instruct",
    Model.LLAMA_3_1_8B: "accounts/fireworks/models/llama-v3p1-8b-instruct",
    Model.LLAMA_3_1_70B: "accounts/fireworks/models/llama-v3p1-70b-instruct",
    Model.LLAMA_3_1_405B: "accounts/fireworks/models/llama-v3p1-405b-instruct",
    Model.DEEPSEEK_V3_2412: "accounts/fireworks/models/deepseek-v3",
    Model.DEEPSEEK_V3_0324: "accounts/fireworks/models/deepseek-v3-0324",
    Model.DEEPSEEK_R1_2501: "accounts/fireworks/models/deepseek-r1",
    Model.DEEPSEEK_R1_0528: "accounts/fireworks/models/deepseek-r1-0528",
    Model.DEEPSEEK_R1_2501_BASIC: "accounts/fireworks/models/deepseek-r1-basic",
    Model.LLAMA_4_MAVERICK_BASIC: "accounts/fireworks/models/llama4-maverick-instruct-basic",
    Model.LLAMA_4_SCOUT_BASIC: "accounts/fireworks/models/llama4-scout-instruct-basic",
    # For now just using as fallback
    Model.LLAMA_4_MAVERICK_FAST: "accounts/fireworks/models/llama4-maverick-instruct-basic",
    Model.LLAMA_4_SCOUT_FAST: "accounts/fireworks/models/llama4-scout-instruct-basic",
    Model.QWEN_QWQ_32B: "accounts/fireworks/models/qwq-32b",
    Model.GPT_OSS_20B: "accounts/fireworks/models/gpt-oss-20b",
    Model.GPT_OSS_120B: "accounts/fireworks/models/gpt-oss-120b",
    Model.KIMI_K2_INSTRUCT: "accounts/fireworks/models/kimi-k2-instruct",
}


class FireworksConfig(BaseModel):
    provider: Literal[Provider.FIREWORKS] = Provider.FIREWORKS

    url: str = "https://api.fireworks.ai/inference/v1/chat/completions"
    api_key: str

    def __str__(self):
        return f"FireworksConfig(url={self.url}, api_key={self.api_key[:4]}****)"


class FireworksAIProvider(HTTPXProvider[FireworksConfig, CompletionResponse]):
    def _response_format(self, options: ProviderOptions, model_data: ModelData):
        if options.enabled_tools:
            # We disable structured generation if tools are enabled
            # since fireworks does not support providing both tool calls and structured output
            # Fireworks responds with "You cannot specify response format and function call at the same time"
            # Meaning that even TextResponseFormat is not supported
            return None
        if not options.output_schema:
            return TextResponseFormat()
        if not model_data.supports_structured_output:
            # Structured gen is deactivated for some models like R1
            # Since it breaks the thinking part
            return None
        schema = copy.deepcopy(options.output_schema)
        return JSONResponseFormat(json_schema=schema)

    def model_str(self, model: Model) -> str:
        return _NAME_OVERRIDE_MAP.get(model, model.value)

    @override
    def _build_request(self, messages: list[MessageDeprecated], options: ProviderOptions, stream: bool) -> BaseModel:
        # Clearing the buffer before building the request
        domain_messages: list[FireworksMessage | FireworksToolMessage] = []
        for m in messages:
            if m.tool_call_results:
                domain_messages.extend(FireworksToolMessage.from_domain(m))
            else:
                domain_messages.append(FireworksMessage.from_domain(m))

        data = get_model_data(options.model)

        request = CompletionRequest(
            messages=domain_messages,
            model=self.model_str(Model(options.model)),
            temperature=options.temperature,
            # Setting the max generation tokens to the max possible value
            # Setting the context length exceeded behavior to truncate will ensure that no error
            # is raised when prompt token + max_tokens > model context window
            #
            # We fallback to the full context window if no max_output_tokens is set since some models do not have
            # an explicit generation limit
            max_tokens=options.max_tokens or data.max_tokens_data.max_output_tokens or data.max_tokens_data.max_tokens,
            context_length_exceeded_behavior="truncate",
            stream=stream,
            response_format=self._response_format(options, data),
            frequency_penalty=options.frequency_penalty,
            presence_penalty=options.presence_penalty,
            top_p=options.top_p,
        )

        # Add native tool calls if enabled
        if options.enabled_tools:
            request.tools = [
                FireworksTool(
                    type="function",
                    function=FireworksToolFunction(
                        name=internal_tool_name_to_native_tool_call(tool.name),
                        description=tool.description,
                        parameters=tool.input_schema,
                    ),
                )
                for tool in options.enabled_tools
            ]
        return request

    @override
    def _response_model_cls(self) -> type[CompletionResponse]:
        return CompletionResponse

    @classmethod
    def fireworks_message_or_tool_message(cls, messag_dict: dict[str, Any]) -> FireworksToolMessage | FireworksMessage:
        try:
            return FireworksToolMessage.model_validate(messag_dict)
        except ValidationError:
            return FireworksMessage.model_validate(messag_dict)

    @override
    async def _request_headers(self, request: dict[str, Any], url: str, model: Model) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._config.api_key}",
        }

    @override
    def _request_url(self, model: Model, stream: bool) -> str:
        return self._config.url

    @override
    def _extract_reasoning_steps(self, response: CompletionResponse) -> str | None:
        response_text = response.choices[0].message.content
        if response_text and "<think>" in response_text and isinstance(response_text, str):
            if "</think>" in response_text:
                return response_text[response_text.index("<think>") + len("<think>") : response_text.index("</think>")]

            raise InvalidGenerationError(
                msg="Model returned a response without a closing THINK tag, meaning the model failed to complete "
                "generation.",
                raw_completion=str(response.choices),
            )
        return None

    @override
    def _extract_content_str(self, response: CompletionResponse) -> str:  # noqa: C901
        message = response.choices[0].message
        content = message.content
        for choice in response.choices:
            if choice.finish_reason == "length":
                raise MaxTokensExceededError(
                    msg="Model returned a response with a LENGTH finish reason, meaning the maximum number of tokens was exceeded.",
                    raw_completion=str(response.choices),
                )

        if content is None:
            if not message.tool_calls:
                raise FailedGenerationError(
                    msg="Model did not generate a response content",
                    capture=True,
                )
            return ""

        if isinstance(content, str):
            if "<think>" in content:
                if "</think>" in content:
                    return content[content.index("</think>") + len("</think>") :]
                raise InvalidGenerationError(
                    msg="Model returned a response without a closing THINK tag, meaning the model failed to complete generation.",
                    raw_completion=str(response.choices),
                )
            return content
        if len(content) > 1:
            self.logger.warning("Multiple content items found in response", extra={"response": response.model_dump()})
        for item in content:
            if item.type == "text":
                return item.text
        self.logger.warning("No content found in response", extra={"response": response.model_dump()})
        return ""

    @override
    def _extract_usage(self, response: CompletionResponse) -> LLMUsage | None:
        return response.usage.to_domain()

    def _invalid_request_error(self, payload: FireworksAIError, response: Response):
        if not payload.error.message:
            return None
        lower_msg = payload.error.message.lower()
        if "prompt is too long" in lower_msg:
            return MaxTokensExceededError(
                msg=payload.error.message,
                response=response,
            )
        if "model not found, inaccessible, and/or not deployed" in lower_msg:
            return MissingModelError(
                msg=payload.error.message,
                response=response,
            )
        return False

    @override
    def _unknown_error(self, response: Response):
        try:
            payload = FireworksAIError.model_validate_json(response.text)
        except Exception:
            self.logger.exception("failed to parse Fireworks AI error response", extra={"response": response.text})
            return UnknownProviderError(
                msg=f"Unknown error status {response.status_code}",
                response=response,
            )

        error_cls = UnknownProviderError
        match payload.error.code:
            case "string_above_max_length" | "context_length_exceeded":
                # In this case we do not want to store the task run because it is a request error that
                # does not incur cost
                # We still bin with max tokens exceeded since it is related
                error_cls = MaxTokensExceededError

            case None:
                if err := self._invalid_request_error(payload, response):
                    return err

            case _:
                pass

        return error_cls(
            msg=payload.error.message or "Unknown error",
            response=response,
        )

    @override
    def _unknown_error_message(self, response: Response):
        try:
            payload = FireworksAIError.model_validate_json(response.text)
            return payload.error.message or "Unknown error"
        except Exception:
            self.logger.exception("failed to parse Fireworks AI error response", extra={"response": response.text})
            return super()._unknown_error_message(response)

    @override
    @classmethod
    def requires_downloading_file(cls, file: File, model: Model) -> bool:
        return True

    @override
    @classmethod
    def required_env_vars(cls) -> list[str]:
        return ["FIREWORKS_API_KEY"]

    @override
    @classmethod
    def name(cls) -> Provider:
        return Provider.FIREWORKS

    @override
    @classmethod
    def _default_config(cls, index: int) -> FireworksConfig:
        return FireworksConfig(
            api_key=get_provider_config_env("FIREWORKS_API_KEY", index),
            url=get_provider_config_env(
                "FIREWORKS_URL",
                index,
                "https://api.fireworks.ai/inference/v1/chat/completions",
            ),
        )

    @property
    def is_structured_generation_supported(self) -> bool:
        return True

    @override
    def _extract_stream_delta(self, sse_event: bytes):
        if sse_event == b"[DONE]":
            return ParsedResponse()

        raw = StreamedResponse.model_validate_json(sse_event)
        return raw.to_parsed_response()

    def _compute_prompt_token_count(
        self,
        messages: list[dict[str, Any]],
        model: Model,
    ) -> float:
        # NOTE: FireworksAI similar to OpenAI
        fireworks_boilerplate_tokens = 3
        fireworks_message_boilerplate_tokens = 4

        num_tokens = fireworks_boilerplate_tokens

        for message in messages:
            domain_message = FireworksMessage.model_validate(message)
            num_tokens += domain_message.token_count(model)
            num_tokens += fireworks_message_boilerplate_tokens

        return num_tokens

    @override
    async def _compute_prompt_audio_token_count(
        self,
        messages: list[dict[str, Any]],
    ):
        return 0, None

    @override
    def sanitize_model_data(self, model_data: ModelData):
        model_data.supports_input_image = True
        model_data.supports_input_pdf = True

    @classmethod
    def _extract_native_tool_calls(cls, response: CompletionResponse) -> list[ToolCallRequest]:
        choice = response.choices[0]

        tool_calls: list[ToolCallRequest] = [
            ToolCallRequest(
                id=tool_call.id,
                tool_name=native_tool_name_to_internal(tool_call.function.name),
                # Fireworks returns the tool call arguments as a string, so we need to parse it
                tool_input_dict=parse_tool_call_or_raise(tool_call.function.arguments) or {},
            )
            for tool_call in choice.message.tool_calls or []
        ]
        return tool_calls

    @override
    async def _extract_and_log_rate_limits(self, response: Response, options: ProviderOptions):
        await self._log_rate_limit_remaining(
            "requests",
            remaining=response.headers.get("x-ratelimit-remaining-requests"),
            total=response.headers.get("x-ratelimit-limit-requests"),
            options=options,
        )
        await self._log_rate_limit_remaining(
            "input_tokens",
            remaining=response.headers.get("x-ratelimit-remaining-tokens-prompt"),
            total=response.headers.get("x-ratelimit-limit-tokens-prompt"),
            options=options,
        )
        await self._log_rate_limit_remaining(
            "output_tokens",
            remaining=response.headers.get("x-ratelimit-remaining-tokens-generated"),
            total=response.headers.get("x-ratelimit-limit-tokens-generated"),
            options=options,
        )

    @override
    def default_model(self) -> Model:
        return Model.LLAMA_4_SCOUT_BASIC

import copy
from abc import abstractmethod
from json import JSONDecodeError
from typing import Any, Protocol, override

from httpx import Response
from pydantic import BaseModel, ValidationError

from core.domain.file import File
from core.domain.message import MessageDeprecated
from core.domain.models import Model
from core.domain.models.model_data_supports import ModelDataSupports
from core.domain.models.utils import get_model_data
from core.domain.tool_call import ToolCallRequest
from core.providers._base.abstract_provider import ProviderConfigInterface
from core.providers._base.httpx_provider import HTTPXProvider
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import (
    ContentModerationError,
    FailedGenerationError,
    MaxTokensExceededError,
    ModelDoesNotSupportModeError,
    ProviderBadRequestError,
    ProviderInvalidFileError,
    StructuredGenerationError,
    UnknownProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers._base.streaming_context import ParsedResponse
from core.providers.google.google_provider_domain import (
    native_tool_name_to_internal,
)
from core.providers.openai._openai_utils import get_openai_json_schema_name, prepare_openai_json_schema

from .openai_domain import (
    CompletionRequest,
    CompletionResponse,
    JSONResponseFormat,
    JSONSchemaResponseFormat,
    OpenAIError,
    OpenAIMessage,
    OpenAISchema,
    OpenAIToolMessage,
    StreamedResponse,
    StreamOptions,
    TextResponseFormat,
    Tool,
    parse_tool_call_or_raise,
)


class OpenAIProviderBaseConfig(ProviderConfigInterface, Protocol):
    pass


class OpenAIProviderBase[OpenAIConfigVar: OpenAIProviderBaseConfig](HTTPXProvider[OpenAIConfigVar, CompletionResponse]):
    def _build_request(self, messages: list[MessageDeprecated], options: ProviderOptions, stream: bool) -> BaseModel:
        model_name = options.model
        model_data = get_model_data(options.model)

        message: list[OpenAIMessage | OpenAIToolMessage] = []
        for m in messages:
            if m.tool_call_results:
                message.extend(OpenAIToolMessage.from_domain(m))
            else:
                message.append(OpenAIMessage.from_domain(m, is_system_allowed=model_data.supports_system_messages))

        completion_request = CompletionRequest(
            messages=message,
            model=model_name,
            temperature=options.temperature if model_data.supports_temperature else None,
            max_completion_tokens=options.max_tokens,
            stream=stream,
            stream_options=StreamOptions(include_usage=True) if stream else None,
            # store=True,
            response_format=self._response_format(options, supports=model_data),
            reasoning_effort=options.final_reasoning_effort(model_data.reasoning),
            tool_choice=CompletionRequest.tool_choice_from_domain(options.tool_choice),
            top_p=options.top_p if model_data.supports_top_p else None,
            presence_penalty=options.presence_penalty if model_data.supports_presence_penalty else None,
            frequency_penalty=options.frequency_penalty if model_data.supports_frequency_penalty else None,
            parallel_tool_calls=options.parallel_tool_calls if model_data.supports_parallel_tool_calls else None,
        )

        if options.enabled_tools is not None and options.enabled_tools != []:
            completion_request.tools = [Tool.from_domain(tool) for tool in options.enabled_tools]

        return completion_request

    def _response_format(
        self,
        options: ProviderOptions,
        supports: ModelDataSupports,
    ) -> TextResponseFormat | JSONResponseFormat | JSONSchemaResponseFormat:
        if options.output_schema is None or (
            not supports.supports_json_mode and not supports.supports_structured_output
        ):
            return TextResponseFormat()

        if not supports.supports_structured_output or not options.output_schema or not options.structured_generation:
            return JSONResponseFormat()

        task_name = options.task_name or ""

        schema = copy.deepcopy(options.output_schema)
        return JSONSchemaResponseFormat(
            json_schema=OpenAISchema(
                name=get_openai_json_schema_name(task_name, schema),
                json_schema=prepare_openai_json_schema(schema),
            ),
        )

    @abstractmethod
    def _request_url(self, model: Model, stream: bool) -> str:
        pass

    @abstractmethod
    async def _request_headers(self, request: dict[str, Any], url: str, model: Model) -> dict[str, str]:
        pass

    @classmethod
    def open_ai_message_or_tool_message(cls, messag_dict: dict[str, Any]) -> OpenAIMessage | OpenAIToolMessage:
        try:
            return OpenAIToolMessage.model_validate(messag_dict)
        except ValidationError:
            return OpenAIMessage.model_validate(messag_dict)

    def _response_model_cls(self) -> type[CompletionResponse]:
        return CompletionResponse

    def _extract_content_str(self, response: CompletionResponse) -> str:
        for choice in response.choices:
            if choice.finish_reason == "length":
                raise MaxTokensExceededError(
                    msg="Model returned a response with a length finish reason, meaning the maximum number of tokens was exceeded.",
                    raw_completion=response,
                )
        message = response.choices[0].message
        content = message.content
        if content is None:
            if message.refusal:
                # TODO: track metric for refusals
                raise ContentModerationError(
                    msg=f"Model refused to generate a response: {message.refusal}",
                )
            if not message.tool_calls:
                raise FailedGenerationError(
                    msg="Model did not generate a response content",
                    capture=True,
                )
            return ""
        if isinstance(content, str):
            return content
        if len(content) > 1:
            self.logger.warning("Multiple content items found in response", extra={"response": response.model_dump()})
        # TODO: we should check if it is possible to have multiple text content items
        for item in content:
            if item.type == "text":
                return item.text
        self.logger.warning("No content found in response", extra={"response": response.model_dump()})
        return ""

    def _extract_usage(self, response: CompletionResponse) -> LLMUsage | None:
        return response.usage.to_domain() if response.usage else None

    def _unsupported_parameter_error(self, payload: OpenAIError, response: Response):
        if payload.error.param == "tools":
            # Capturing here, it should be caught by the model data setting
            return ModelDoesNotSupportModeError(msg=payload.error.message, response=response, capture=True)
        return None

    def _invalid_request_error(self, payload: OpenAIError, response: Response):
        if payload.error.param == "response_format" and "Invalid schema" in payload.error.message:
            return StructuredGenerationError(
                msg=payload.error.message,
                response=response,
            )
        # Azure started returning an error with very little information about
        # a model not supporting structured generation
        if "response_format" in payload.error.message and "json_schema" in payload.error.message:
            return StructuredGenerationError(
                msg=payload.error.message,
                response=response,
            )
        if "tools is not supported in this model" in payload.error.message:
            return ModelDoesNotSupportModeError(
                msg=payload.error.message,
                response=response,
                capture=True,
            )
        if "Too many images in request" in payload.error.message:
            return ProviderInvalidFileError(msg=payload.error.message, response=response)
        if "does not support file content types." in payload.error.message:
            return ModelDoesNotSupportModeError(msg=payload.error.message, response=response)

        return None

    def _invalid_value_error(self, payload: OpenAIError, response: Response):
        if payload.error.param == "model":
            return ModelDoesNotSupportModeError(
                msg=payload.error.message,
                response=response,
                # Capturing for now
                capture=True,
            )
        return None

    def _unknown_error(self, response: Response):  # noqa: C901
        try:
            payload = OpenAIError.model_validate_json(response.text)

            match payload.error.code:
                case "string_above_max_length":
                    # In this case we do not want to store the task run because it is a request error that
                    # does not incur cost
                    # We still bin with max tokens exceeded since it is related
                    return MaxTokensExceededError(msg=payload.error.message, response=response)
                case "invalid_prompt":
                    if "violating our usage policy" in payload.error.message:
                        return ContentModerationError(msg=payload.error.message, response=response)
                case "content_filter":
                    return ContentModerationError(msg=payload.error.message, response=response)
                case "unsupported_parameter":
                    if error := self._unsupported_parameter_error(payload, response):
                        return error
                case "invalid_value":
                    if error := self._invalid_value_error(payload, response):
                        return error
                case "invalid_image_format":
                    return ProviderBadRequestError(msg=payload.error.message, response=response)
                case "invalid_image_url":
                    return ProviderBadRequestError(msg=payload.error.message, response=response)
                case "invalid_base64":
                    return ProviderInvalidFileError(msg="Base64 data is not valid")
                case "BadRequest":
                    # Capturing for now
                    return ProviderBadRequestError(msg=payload.error.message, response=response, capture=True)
                case _:
                    pass
            if payload.error.type == "invalid_request_error" and (
                error := self._invalid_request_error(payload, response)
            ):
                return error
            return UnknownProviderError(msg=payload.error.message, response=response)
        except Exception:
            self.logger.exception("failed to parse OpenAI error response", extra={"response": response.text})
            return UnknownProviderError(msg=f"Unknown error status {response.status_code}", response=response)

    def _unknown_error_message(self, response: Response):
        try:
            payload = OpenAIError.model_validate_json(response.text)
            return payload.error.message
        except Exception:
            self.logger.exception("failed to parse OpenAI error response", extra={"response": response.text})
            return super()._unknown_error_message(response)

    @classmethod
    def requires_downloading_file(cls, file: File, model: Model) -> bool:
        # OpenAI requires downloading files for non-image files
        return not file.is_image

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
        """Return the number of tokens used by a list of messages.

        Simplified version of https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
        """
        openai_boilerplate_tokens = 3
        openai_message_boilerplate_tokens = 4

        num_tokens = openai_boilerplate_tokens

        for message in messages:
            domain_message = self.open_ai_message_or_tool_message(message)
            num_tokens += domain_message.token_count(model)
            num_tokens += openai_message_boilerplate_tokens

        return num_tokens

    def _handle_error_status_code(self, response: Response):
        try:
            response_json = response.json()
        except JSONDecodeError:
            super()._handle_error_status_code(response)
            return

        if (
            response_json.get("error")
            and response_json["error"].get("code")
            and response_json["error"]["code"] == "context_length_exceeded"
        ):
            raise MaxTokensExceededError(response_json["error"].get("message", "Max tokens exceeded"))

        if (
            response_json.get("error")
            and response_json["error"].get("message")
            and "content management policy" in response_json["error"]["message"]
        ):
            raise ContentModerationError(response_json["error"].get("message", "Content moderation error"))

        super()._handle_error_status_code(response)

    async def _compute_prompt_audio_token_count(
        self,
        messages: list[dict[str, Any]],
    ):
        return 0, None

    @classmethod
    def _extract_native_tool_calls(cls, response: CompletionResponse) -> list[ToolCallRequest]:
        choice = response.choices[0]

        tool_calls: list[ToolCallRequest] = [
            ToolCallRequest(
                id=tool_call.id,
                tool_name=native_tool_name_to_internal(tool_call.function.name),
                # OpenAI returns the tool call arguments as a string, so we need to parse it
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
            "tokens",
            remaining=response.headers.get("x-ratelimit-remaining-tokens"),
            total=response.headers.get("x-ratelimit-limit-tokens"),
            options=options,
        )

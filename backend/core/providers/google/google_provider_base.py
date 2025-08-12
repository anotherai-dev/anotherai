import asyncio
from abc import abstractmethod
from collections.abc import AsyncIterator
from json import JSONDecodeError
from typing import Any, Protocol, override

import httpx
from pydantic import BaseModel

from core.domain.file import File
from core.domain.message import MessageDeprecated
from core.domain.models import Model
from core.domain.models.utils import get_model_data
from core.domain.tool_call import ToolCallRequest
from core.providers._base.abstract_provider import ProviderConfigInterface
from core.providers._base.httpx_provider import HTTPXProvider
from core.providers._base.llm_usage import LLMCompletionUsage, LLMUsage
from core.providers._base.models import RawCompletion
from core.providers._base.provider_error import (
    ContentModerationError,
    FailedGenerationError,
    InvalidGenerationError,
    MaxTokensExceededError,
    MissingModelError,
    ModelDoesNotSupportModeError,
    ProviderBadRequestError,
    ProviderError,
    ProviderInvalidFileError,
    ProviderRateLimitError,
    UnknownProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers._base.streaming_context import ParsedResponse, ToolCallRequestBuffer
from core.providers.google.google_provider_domain import (
    BLOCK_THRESHOLD,
    Candidate,
    CompletionRequest,
    CompletionResponse,
    GoogleMessage,
    GoogleSystemMessage,
    HarmCategory,
    Part,
    StreamedResponse,
    message_or_system_message,
    native_tool_name_to_internal,
)
from core.providers.google.google_provider_utils import prepare_google_response_schema

MODELS_THAT_REQUIRE_DOWNLOADING_FILES = {
    Model.GEMINI_2_0_FLASH_THINKING_EXP_1219,
    Model.GEMINI_2_0_FLASH_EXP,
    Model.GEMINI_EXP_1206,
    Model.GEMINI_2_0_FLASH_THINKING_EXP_0121,
}

_MODEL_MAPPING = {
    Model.GEMINI_2_5_FLASH_THINKING_PREVIEW_0417: Model.GEMINI_2_5_FLASH_PREVIEW_0417,
    Model.GEMINI_2_5_FLASH_THINKING_PREVIEW_0520: Model.GEMINI_2_5_FLASH_PREVIEW_0520,
}


class GoogleProviderBaseConfig(ProviderConfigInterface, Protocol):
    @property
    def default_block_threshold(self) -> BLOCK_THRESHOLD | None: ...


class GoogleProviderBase[GoogleConfigVar: GoogleProviderBaseConfig](HTTPXProvider[GoogleConfigVar, CompletionResponse]):
    def _model_url_str(self, model: Model) -> str:
        return _MODEL_MAPPING.get(model, model).value

    def _safety_settings(self) -> list[CompletionRequest.SafetySettings] | None:
        if self._config.default_block_threshold is None:
            return None

        return [
            CompletionRequest.SafetySettings(
                category=cat,
                threshold=self._config.default_block_threshold,
            )
            for cat in HarmCategory
        ]

    def _add_native_tools(self, options: ProviderOptions, completion_request: CompletionRequest):
        if options.enabled_tools not in (None, []):
            tools: CompletionRequest.Tool | None = None
            tool_config: CompletionRequest.ToolConfig | None = None

            tools = CompletionRequest.Tool(
                functionDeclarations=[],
            )

            tool_config = CompletionRequest.ToolConfig(
                functionCallingConfig=CompletionRequest.ToolConfig.FunctionCallingConfig.from_domain(
                    options.tool_choice,
                ),
            )

            for tool in options.enabled_tools:
                tools.functionDeclarations.append(
                    CompletionRequest.Tool.FunctionDeclaration.from_tool(tool),
                )

            completion_request.tools = tools
            completion_request.toolConfig = tool_config

    @classmethod
    def _convert_messages(
        cls,
        messages: list[MessageDeprecated],
        supports_system_messages: bool,
    ) -> tuple[list[GoogleMessage], GoogleSystemMessage | None]:
        user_messages: list[GoogleMessage] = []
        system_message: GoogleSystemMessage | None = None

        if not supports_system_messages:
            # TODO: This feels really weird. We should not need to do this.
            # For now it's only activated on gemini flash 2.0
            merged_message = _merge_messages(messages, role=MessageDeprecated.Role.USER)
            user_messages = [GoogleMessage.from_domain(merged_message)]
            return user_messages, None

        if messages[0].role == MessageDeprecated.Role.SYSTEM:
            system_message = GoogleSystemMessage.from_domain(messages[0])
            messages = messages[1:]
        else:
            system_message = None

        user_messages = (
            [GoogleMessage.from_domain(message) for message in messages]
            if messages
            else [GoogleMessage(role="user", parts=[Part(text="-")])]
        )

        return user_messages, system_message

    @property
    def response_schema_allowed_string_formats(self) -> set[str] | None:
        # By default, allow all string formats in the response schemas
        return None

    @override
    def _build_request(self, messages: list[MessageDeprecated], options: ProviderOptions, stream: bool) -> BaseModel:
        model_data = get_model_data(model=options.model)

        user_messages, system_message = self._convert_messages(messages, model_data.supports_system_messages)

        # See https://ai.google.dev/gemini-api/docs/thinking
        # Thinking is enabled by default on thinking models so we just need to "turn off" thinking

        budget = options.final_reasoning_budget(model_data.reasoning)

        thinking_config = (
            None
            if budget is None
            else CompletionRequest.GenerationConfig.ThinkingConfig(
                thinkingBudget=budget,
            )
        )

        generation_config = CompletionRequest.GenerationConfig(
            temperature=options.temperature,
            maxOutputTokens=options.max_tokens,
            responseMimeType="application/json"
            if (model_data.supports_json_mode and not options.enabled_tools and options.output_schema)
            # Google does not allow setting the response mime type at all when using tools.
            else "text/plain",
            thinking_config=thinking_config,
            presencePenalty=options.presence_penalty,
            frequencyPenalty=options.frequency_penalty,
            topP=options.top_p,
        )

        if (
            self.is_structured_generation_supported
            and options.structured_generation
            and options.output_schema
            and model_data.supports_structured_output
        ):
            try:
                generation_config.responseSchema = prepare_google_response_schema(
                    options.output_schema,
                    self.response_schema_allowed_string_formats,
                )
            except Exception as e:  # noqa: BLE001
                # What is in 'options.output_schema' can have a lot of different shapes, hence the generic error handling
                # Failure to prepare the schema does not prevent the generation from starting, we can just fallback to non-controlled generation
                self.logger.error("Failed to prepare Google controlled generation schema", extra={"error": e})

        # TODO:
        # if messages[0].image_options and messages[0].image_options.image_count:
        #     generation_config.responseModalities = ["IMAGE", "TEXT"]

        #     # We also inline the image options in the last user message
        #     user_messages[-1].parts.append(Part(text=str(messages[0].image_options)))

        completion_request = CompletionRequest(
            systemInstruction=system_message,
            contents=user_messages,
            generationConfig=generation_config,
            safetySettings=self._safety_settings(),
        )

        self._add_native_tools(options, completion_request)

        return completion_request

    @property
    def is_structured_generation_supported(self) -> bool:
        return True

    def _raw_prompt(self, request_json: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract the raw prompt from the request JSON"""

        raw_messages: list[dict[str, Any]] = []

        if request_json.get("systemInstruction"):
            raw_messages.append(request_json["systemInstruction"])

        for message in request_json["contents"]:
            # TODO: fix noqa
            raw_messages.append(message)  # noqa: PERF402

        return raw_messages

    async def wrap_sse(self, raw: AsyncIterator[bytes], termination_chars: bytes = b"\r\n\r\n"):
        async for data in super().wrap_sse(raw, termination_chars):
            yield data

    @abstractmethod
    def _request_url(self, model: Model, stream: bool) -> str:
        pass

    @override
    def _response_model_cls(self) -> type[CompletionResponse]:
        return CompletionResponse

    @override
    def _extract_reasoning_steps(self, response: CompletionResponse):
        if not response.candidates:
            return None
        if response.candidates[0].content and len(response.candidates[0].content.parts) > 1:
            # More than one part means the model has returned a reasoning step
            index = 0 if response.candidates[0].content.parts[0].thought else 1
            return response.candidates[0].content.parts[index].text or ""

        return None

    @classmethod
    def _check_finish_reason(cls, candidates: list[Candidate]):
        for candidate in candidates:
            match candidate.finishReason:
                case "MAX_TOKENS":
                    raise MaxTokensExceededError(
                        msg="Model returned a MAX_TOKENS finish reason. The max number of tokens as specified in the request was reached.",
                    )
                case "MALFORMED_FUNCTION_CALL":
                    raise InvalidGenerationError(
                        msg="Model returned a malformed function call finish reason",
                        # Capturing so we can see why this happens
                        capture=True,
                    )
                case _:
                    pass

    @override
    def _extract_content_str(self, response: CompletionResponse) -> str:
        # No need to check for errors, it will be handled upstream in httpx provider
        if not response.candidates:
            if response.promptFeedback and response.promptFeedback.blockReason:
                raise ContentModerationError(
                    f"The model blocked the generation with reason '{response.promptFeedback.blockReason}'",
                )
            # Otherwise not sure what's going on
            self.logger.warning(
                "No candidates found in response",
                extra={"response": response.model_dump()},
            )
            raise UnknownProviderError("No candidates found in response")

        # Check if we have a finish
        self._check_finish_reason(response.candidates)

        content = response.candidates[0].content
        if not content:
            self.logger.warning("No content found in first candidate", extra={"response": response.model_dump()})
            return ""
        parts = content.parts
        if not parts:
            self.logger.warning("No parts found in first candidate", extra={"response": response.model_dump()})
            return ""
        index = 0
        if len(parts) > 1 and parts[0].thought:
            # More than one part means the model has returned a reasoning step
            index = 1
        return parts[index].text or ""

    @override
    def _extract_files(self, response: CompletionResponse) -> list[File] | None:
        if not response.candidates:
            return None
        candidate = response.candidates[0]
        if not candidate.content:
            return None

        files = [
            File(
                content_type=part.inlineData.mimeType,
                data=part.inlineData.data,
            )
            for part in candidate.content.parts
            if part.inlineData
        ]

        return files or None

    @override
    def _extract_usage(self, response: CompletionResponse) -> LLMUsage | None:
        return response.usageMetadata.to_domain() if response.usageMetadata else None

    @classmethod
    def _extract_native_tool_calls(cls, response: CompletionResponse) -> list[ToolCallRequest]:
        if not response.candidates:
            return []
        candidate = response.candidates[0]
        if candidate.content and len(candidate.content.parts) > 0:
            return [
                ToolCallRequest(
                    tool_name=native_tool_name_to_internal(part.functionCall.name)
                    or "missing tool name",  # Will raise an error to pass back to the model models in the runner
                    tool_input_dict=part.functionCall.args or {},
                )
                for part in candidate.content.parts
                if part.functionCall
            ]
        return []

    @override
    def _provider_rate_limit_error(self, response: httpx.Response):
        return ProviderRateLimitError(
            retry=True,
            max_attempt_count=3,
            msg="Rate limit exceeded in region",
            response=response,
        )

    def _failed_generation_error(self, response: httpx.Response):
        return FailedGenerationError(
            msg=response.text,
            raw_completion=response.text,
            usage=LLMCompletionUsage(),
        )

    @override
    @classmethod
    def requires_downloading_file(cls, file: File, model: Model) -> bool:
        if model in MODELS_THAT_REQUIRE_DOWNLOADING_FILES:
            # Experimental models only support files passed by GCP URLs or base64 encoded strings
            return True
        # We download audio files for now
        # Since we will need it for pricing anyway
        if file.is_audio is True:
            return True
        # Google requires a content type to be set for files
        # We can guess the content type when not provided by downloading the file
        # Guessing the content type based on the URL should have happened upstream
        return not file.content_type

    @override
    def _unknown_error_message(self, response: httpx.Response):
        return response.text

    # If the error message contains these, we raise an invalid file error and pass the message as is
    _INVALID_FILE_SEARCH_STRINGS: list[str] = [
        "the document has no pages",
        "unable to process input image",
        "url_unreachable-unreachable_5xx",
        "url_rejected",
        "url_roboted",
        "please ensure the url is valid and accessible",
        "submit request because it has a mimetype parameter with value",
    ]

    @classmethod
    def _handle_invalid_argument(cls, message: str, response: httpx.Response):  # noqa: C901
        error_cls: type[ProviderError] = ProviderBadRequestError
        error_msg = message
        capture = False
        match message.lower():
            case lower_msg if any(
                m in lower_msg
                for m in [
                    "educe the input token count and try again",
                    "exceeds the maximum number of tokens allowed",
                ]
            ):
                error_cls = MaxTokensExceededError
            case lower_msg if any(
                m in lower_msg
                for m in [
                    "number of function response parts should be equal to number of function call parts",
                    "request payload size exceeds the limit",
                ]
            ):
                pass
            case lower_msg if "non-leading vision input which the model does not support" in lower_msg:
                # Capturing since we should have the data in the model data
                capture = True
                error_cls = ModelDoesNotSupportModeError
            case lower_msg if "url_error-error_not_found" in lower_msg:
                error_msg = "Provider could not retrieve file: URL returned a 404 error"
                error_cls = ProviderInvalidFileError
            case lower_msg if "url_timeout-timeout_fetchproxy" in lower_msg:
                error_msg = "Provider could not retrieve file: URL timed out"
                error_cls = ProviderInvalidFileError
            case lower_msg if "url_unreachable-unreachable_no_response" in lower_msg:
                error_msg = "Provider could not retrieve file: No response"
                error_cls = ProviderInvalidFileError
            case lower_msg if "url_rejected-rejected_rpc_app_error" in lower_msg:
                error_msg = "Provider could not retrieve file: Rejected"
                error_cls = ProviderInvalidFileError
            case lower_msg if "base64 decoding failed" in lower_msg:
                error_msg = "Provider could not decode base64 data"
                error_cls = ProviderInvalidFileError
            case lower_msg if any(m in lower_msg for m in cls._INVALID_FILE_SEARCH_STRINGS):
                error_cls = ProviderInvalidFileError
            case lower_msg if "you can only include" in lower_msg:
                error_cls = ModelDoesNotSupportModeError
            case lower_msg if "does not support the requested response modalities" in lower_msg:
                error_cls = ModelDoesNotSupportModeError
            case lower_msg if "multi-modal output is not supported" in lower_msg:
                error_cls = ModelDoesNotSupportModeError
            case lower_msg if "violated google's responsible ai practices" in lower_msg:
                error_cls = ContentModerationError
            case _:
                return
        raise error_cls(error_msg, response=response, capture=capture)

    def _handle_not_found(self, message: str, response: httpx.Response):
        if "models" in message:
            raise MissingModelError(message, capture=not self.is_custom_config, response=response)

    def _handle_unknown_error(self, payload: dict[str, Any], response: httpx.Response):
        error = payload.get("error")
        if error is None:
            return
        message = error.get("message")
        if not message:
            return

        match error.get("status"):
            case "INVALID_ARGUMENT":
                self._handle_invalid_argument(message, response)
            case "NOT_FOUND":
                self._handle_not_found(message, response)
            case _:
                return

    @override
    def _handle_error_status_code(self, response: httpx.Response):
        try:
            response_json = response.json()
        except JSONDecodeError:
            super()._handle_error_status_code(response)
            return

        # Will raise an error if the error is known
        self._handle_unknown_error(response_json, response)
        # Call upstream to handle the error
        super()._handle_error_status_code(response)

    async def _compute_prompt_audio_seconds(
        self,
        messages: list[dict[str, Any]],
    ) -> float:
        coroutines = [message_or_system_message(message).audio_duration_seconds() for message in messages]
        durations = await asyncio.gather(*coroutines)
        return sum(durations)

    @override
    async def _compute_prompt_audio_token_count(
        self,
        messages: list[dict[str, Any]],
    ):
        # 32 tokens per second https://ai.google.dev/gemini-api/docs/tokens?lang=python#multimodal-tokens
        duration = await self._compute_prompt_audio_seconds(messages)
        return int(duration * 32), duration

    @override
    def _get_prompt_text_token_count(self, llm_usage: LLMUsage):
        # audio tokens are included in the prompt token count
        if not llm_usage.prompt_audio_token_count or not llm_usage.prompt_token_count:
            return llm_usage.prompt_token_count
        return llm_usage.prompt_token_count - llm_usage.prompt_audio_token_count

    @override
    def _extract_stream_delta(
        self,
        sse_event: bytes,
        raw_completion: RawCompletion,
        tool_call_request_buffer: dict[int, ToolCallRequestBuffer],
    ):
        raw = StreamedResponse.model_validate_json(sse_event)

        if (
            raw.usageMetadata is not None
            and raw.usageMetadata.promptTokenCount is not None
            and raw.usageMetadata.candidatesTokenCount is not None
        ):
            raw_completion.usage = raw.usageMetadata.to_domain()

        if not raw.candidates:
            # No candidates so we can just skip
            return ParsedResponse("")

        if raw.candidates[0].finishReason == "RECITATION":
            raise FailedGenerationError(
                msg="Gemini API returned a RECITATION finish reason, see https://issuetracker.google.com/issues/331677495",
            )

        self._check_finish_reason(raw.candidates)

        if not raw.candidates or not raw.candidates[0] or not raw.candidates[0].content:
            return ParsedResponse("")

        thoughts = ""
        response = ""

        native_tool_calls: list[ToolCallRequest] = []
        for part in raw.candidates[0].content.parts:
            if part.thought:
                thoughts += part.text or ""
            else:
                response += part.text or ""

            if part.functionCall:
                native_tool_calls.append(
                    ToolCallRequest(
                        id="",
                        tool_name=native_tool_name_to_internal(part.functionCall.name),
                        tool_input_dict=part.functionCall.args or {},
                    ),
                )

        return ParsedResponse(
            response,
            thoughts,
            native_tool_calls,
        )


def _merge_messages(messages: list[MessageDeprecated], role: MessageDeprecated.Role):
    """
    Merges message content and images from a list of messages

    """

    contents: list[str] = []
    files: list[File] = []

    for message in messages:
        contents.append(message.content)
        if message.files:
            files.extend(message.files)

    return MessageDeprecated(
        content="\n\n".join(contents),
        files=files if files else None,
        role=role,
    )

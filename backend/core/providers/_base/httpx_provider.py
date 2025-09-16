from abc import abstractmethod
from collections.abc import AsyncGenerator, AsyncIterator
from json import JSONDecodeError
from typing import Any, override

from httpx import Response
from pydantic import BaseModel, ValidationError

from core.domain.exceptions import (
    JSONSchemaValidationError,
)
from core.domain.message import Message, MessageDeprecated
from core.domain.models import Model
from core.domain.tool_call import ToolCallRequest
from core.providers._base.abstract_provider import ProviderConfigInterface, RawCompletion
from core.providers._base.httpx_provider_base import HTTPXProviderBase
from core.providers._base.llm_completion import LLMCompletion
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import ProviderError, ProviderInternalError
from core.providers._base.provider_options import ProviderOptions
from core.providers._base.streaming_context import ParsedResponse, StreamingContext
from core.runners.output_factory import OutputFactory
from core.runners.runner_output import RunnerOutput, RunnerOutputChunk
from core.utils.background import add_background_task
from core.utils.streams import standard_wrap_sse


class HTTPXProvider[ProviderConfigVar: ProviderConfigInterface, ResponseModel: BaseModel](
    HTTPXProviderBase[ProviderConfigVar, dict[str, Any]],
):
    # TODO: use list[Message]
    @abstractmethod
    def _build_request(self, messages: list[MessageDeprecated], options: ProviderOptions, stream: bool) -> BaseModel:
        pass

    @abstractmethod
    async def _request_headers(self, request: dict[str, Any], url: str, model: Model) -> dict[str, str]:
        pass

    @abstractmethod
    def _request_url(self, model: Model, stream: bool) -> str:
        pass

    @abstractmethod
    def _response_model_cls(self) -> type[ResponseModel]:
        pass

    @abstractmethod
    def _extract_content_str(self, response: ResponseModel) -> str:
        pass

    def _extract_reasoning_steps(self, response: ResponseModel) -> str | None:
        return None

    def _extract_usage(self, response: ResponseModel) -> LLMUsage | None:
        return None

    @classmethod
    def _extract_native_tool_calls(cls, response: ResponseModel) -> list[ToolCallRequest]:
        # Method is overriden in subclasses that support native tool calls
        return []

    @abstractmethod
    def _extract_stream_delta(self, sse_event: bytes) -> ParsedResponse:
        pass

    @override
    def _parse_response(
        self,
        response: Response,
        output_factory: OutputFactory,
        raw_completion: RawCompletion,
        request: dict[str, Any],
    ) -> RunnerOutput:
        # Attempt to parse the response as JSON
        try:
            raw = response.json()
        except JSONDecodeError as e:
            raw_completion.response = response.text
            res = self._unknown_error(response)
            res.set_response(response)
            raise res from e
        # Validate using the provider's response model
        try:
            response_model = self._response_model_cls().model_validate(raw)
        except ValidationError as e:
            # That should not happen. It means that there is a discrepancy between the response model and
            # whatever the provider sent
            # However here, we want to trigger provider and model fallback since from experience
            # sometimes models return weird unexpected values and falling back is better than
            # returning a 500
            raise ProviderInternalError(
                "Model returned an unexpected response payload",
                extras={
                    "raw": raw,
                },
                capture=True,
            ) from e

        # Initialize content_str with the response text so that
        # if we raise an error, we have the original response text

        native_tool_calls = self._extract_native_tool_calls(response_model)
        reasoning_steps = self._extract_reasoning_steps(response_model)
        raised_exception: Exception | None = None

        content_str = ""
        try:
            content_str = self._extract_content_str(response_model)
        except ProviderError as e:
            e.set_response(response)
            raise e
        except Exception as e:
            self.logger.exception("Error extracting content", extra={"response": response.text})
            raised_exception = e
        finally:
            usage = self._extract_usage(response_model)
            raw_completion.response = content_str
            if usage:
                raw_completion.usage = usage

        if (raised_exception or not content_str) and not native_tool_calls:
            raise self._invalid_json_error(
                response,
                raised_exception,
                raw_completion=content_str,
                error_msg="Generation returned an empty response",
                retry=True,
            ) from raised_exception

        return self._build_structured_output(
            output_factory,
            content_str,
            reasoning_steps,
            native_tools_calls=native_tool_calls,
        )

    @override
    async def _prepare_completion(self, messages: list[Message], options: ProviderOptions, stream: bool):
        request = self._build_request([m.to_deprecated() for m in messages], options, stream=stream)
        body = request.model_dump(mode="json", exclude_none=True, by_alias=True)

        raw = LLMCompletion(
            usage=self._initial_usage(messages),
            provider=self.name(),
            model=options.model,
            config_id=self._config_id,
            preserve_credits=self._preserve_credits,
            error=None,
            provider_request_incurs_cost=None,
        )

        return body, raw

    @override
    async def _execute_request(self, request: dict[str, Any], options: ProviderOptions) -> Response:
        url = self._request_url(model=options.model, stream=False)
        headers = await self._request_headers(request, url, options.model)

        async with self._open_client(url) as client:
            response = await client.post(
                url,
                json=request,
                headers=headers,
                timeout=self.timeout_or_default(options.timeout),
            )
            response.raise_for_status()
            return response

    async def wrap_sse(self, raw: AsyncIterator[bytes], termination_chars: bytes = b"\n\n") -> AsyncIterator[bytes]:
        async for chunk in standard_wrap_sse(raw, termination_chars, self.logger):
            yield chunk

    @classmethod
    def _build_structured_output(
        cls,
        output_factory: OutputFactory,
        raw: str,
        reasoning: str | None = None,
        native_tools_calls: list[ToolCallRequest] | None = None,
    ):
        try:
            parsed_output = output_factory(raw)
        except (JSONDecodeError, JSONSchemaValidationError) as e:
            if not native_tools_calls:
                raise cls._invalid_json_error(
                    response=None,
                    exception=e,
                    raw_completion=raw,
                    error_msg=str(e)
                    if isinstance(e, JSONSchemaValidationError)
                    else "Model failed to generate a valid json",
                    retry=True,
                ) from e
            # When there is a native tool call, we can afford having a JSONSchemaValidationError,
            # ex: when the models returns a raw "Let me use the @search-google tool to answer the question"
            # in the completion. This happens quite often with Claude models.
            parsed_output = None

        return RunnerOutput(
            agent_output=parsed_output,
            reasoning=reasoning,
            tool_call_requests=native_tools_calls or None,
        )

    def _streaming_context(self, raw_completion: RawCompletion) -> StreamingContext:
        return StreamingContext(raw_completion)

    @override
    async def _single_stream(
        self,
        request: dict[str, Any],
        output_factory: OutputFactory,
        raw_completion: RawCompletion,
        options: ProviderOptions,
    ) -> AsyncGenerator[RunnerOutputChunk]:
        streaming_context: StreamingContext | None = None

        def _finally():
            if streaming_context:
                # TODO: this is no longer used. We should remove it
                raw_completion.response = streaming_context.aggregated_output()
                raw_completion.usage = streaming_context.usage

        with self._wrap_errors(options=options, raw_completion=raw_completion, finally_block=_finally):
            url = self._request_url(model=options.model, stream=True)
            headers = await self._request_headers(request=request, url=url, model=options.model)
            async with (
                self._open_client(url) as client,
                client.stream(
                    "POST",
                    url,
                    json=request,
                    headers=headers,
                    timeout=self.timeout_or_default(options.timeout),
                ) as response,
            ):
                add_background_task(self._extract_and_log_rate_limits(response, options))
                if not response.is_success:
                    # We need to read the response to get the error message
                    await response.aread()
                    response.raise_for_status()

                streaming_context = self._streaming_context(raw_completion)
                async for chunk in self.wrap_sse(response.aiter_bytes()):
                    delta = self._extract_stream_delta(chunk)
                    c = streaming_context.add_chunk(delta)
                    if c.is_empty():
                        continue
                    yield c

                # Always yield the final output
                # This is the output that will be needed to save the run
                yield streaming_context.complete(
                    lambda raw, reasoning, tool_calls: self._build_structured_output(
                        output_factory,
                        raw,
                        reasoning,
                        tool_calls,
                    ),
                )

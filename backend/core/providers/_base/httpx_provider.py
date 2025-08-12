from abc import abstractmethod
from collections.abc import AsyncGenerator, AsyncIterator, Callable
from json import JSONDecodeError
from typing import Any, override

from httpx import Response
from pydantic import BaseModel, ValidationError

from core.domain.exceptions import (
    InternalError,
    JSONSchemaValidationError,
)
from core.domain.file import File
from core.domain.message import Message, MessageDeprecated
from core.domain.models import Model
from core.domain.tool_call import ToolCallRequest
from core.providers._base.abstract_provider import ProviderConfigInterface, RawCompletion
from core.providers._base.httpx_provider_base import HTTPXProviderBase
from core.providers._base.llm_completion import LLMCompletion
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.provider_error import ProviderError, ProviderInternalError
from core.providers._base.provider_options import ProviderOptions
from core.providers._base.provider_output import ProviderOutput
from core.providers._base.streaming_context import ParsedResponse, StreamingContext, ToolCallRequestBuffer
from core.utils.background import add_background_task
from core.utils.dicts import InvalidKeyPathError, set_at_keypath_str
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

    def _extract_files(self, response: ResponseModel) -> list[File] | None:
        return None

    def _extract_reasoning_steps(self, response: ResponseModel) -> str | None:
        return None

    def _extract_usage(self, response: ResponseModel) -> LLMUsage | None:
        return None

    @classmethod
    def _extract_native_tool_calls(cls, response: ResponseModel) -> list[ToolCallRequest]:
        # Method is overriden in subclasses that support native tool calls
        return []

    @abstractmethod
    def _extract_stream_delta(
        self,
        sse_event: bytes,
        raw_completion: RawCompletion,
        tool_call_request_buffer: dict[int, ToolCallRequestBuffer],
    ) -> ParsedResponse:
        pass

    def _raw_prompt(self, request_json: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract the raw prompt from the request JSON"""
        return request_json["messages"]

    def _safe_extract[T](
        self,
        log: str,
        response_model: ResponseModel,
        extractor: Callable[[ResponseModel], T],
    ) -> T | None:
        try:
            return extractor(response_model)
        except Exception:
            self.logger.exception(f"Error extracting {log}")  # noqa: G004
            return None

    @override
    def _parse_response(
        self,
        response: Response,
        output_factory: Callable[[str, bool], ProviderOutput],
        raw_completion: RawCompletion,
        request: dict[str, Any],
    ) -> ProviderOutput:
        try:
            raw = response.json()
        except JSONDecodeError as e:
            raw_completion.response = response.text
            res = self._unknown_error(response)
            res.set_response(response)
            raise res from e
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
        content_str = response.text
        native_tool_calls = self._safe_extract("native tool calls", response_model, self._extract_native_tool_calls)
        reasoning_steps = self._safe_extract("reasoning steps", response_model, self._extract_reasoning_steps)
        files = self._safe_extract("files", response_model, self._extract_files)
        raised_exception: Exception | None = None

        try:
            content_str = self._extract_content_str(response_model)
        except ProviderError as e:
            # If the error is already a provider error, we just re-raise it
            raw_completion.response = content_str
            e.set_response(response)
            raise e
        except Exception as e:
            self.logger.exception("Error extracting content", extra={"response": response.text})
            raw_completion.response = content_str
            raised_exception = e
        finally:
            usage = self._extract_usage(response_model)
            raw_completion.response = content_str
            if usage:
                raw_completion.usage = usage

        if (raised_exception or not content_str) and not native_tool_calls and not files:
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
            files=files,
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
    def _partial_structured_output(
        cls,
        partial_output_factory: Callable[[Any], ProviderOutput],
        context: StreamingContext,
        options: ProviderOptions,
    ):
        if options.stream_deltas:
            if not context.last_chunk:
                cls._get_logger().warning("No last chunk found in streaming context")
                return partial_output_factory("")
            raw = ProviderOutput(output=None, delta=context.last_chunk.content, final=False)
            if context.last_chunk.tool_calls:
                raw = raw._replace(tool_calls=context.last_chunk.tool_calls)
            if context.last_chunk.reasoning:
                raw = raw._replace(reasoning_steps=context.last_chunk.reasoning)
            return raw

        # TODO: we should not test here but instead handle the update directly in the streamer
        partial = partial_output_factory(context.agg_output if context.json else context.streamer.raw_completion)
        if context.reasoning:
            partial = partial._replace(reasoning=context.reasoning)

        # TODO: looks like we are not streaming tool calls ?
        # if context.tool_calls:
        #     partial = partial._replace(tool_calls=context.tool_calls)
        return partial._replace(final=False)

    @classmethod
    def _build_structured_output(
        cls,
        output_factory: Callable[[str, bool], ProviderOutput],
        raw: str,
        reasoning: str | None = None,
        native_tools_calls: list[ToolCallRequest] | None = None,
        files: list[File] | None = None,
    ):
        try:
            output = output_factory(raw, False)  # noqa: FBT003
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
            output = ProviderOutput(output=None)
        if reasoning:
            output = output._replace(reasoning=reasoning)
        if native_tools_calls:
            output = output._replace(tool_calls=native_tools_calls + (output.tool_calls or []))
        if files:
            output = output._replace(files=files)
        return output._replace(final=True)

    def _handle_chunk_output(self, context: StreamingContext, content: str) -> bool:
        updates = context.streamer.process_chunk(content)
        if updates is None:
            return False

        for keypath, value in updates:
            try:
                set_at_keypath_str(context.agg_output, keypath, value)
            except InvalidKeyPathError as e:
                raise InternalError(
                    f"Invalid keypath in stream: {e}",
                    extras={
                        "aggregate": context.streamer.aggregate,
                        "output": context.agg_output,
                        "keypath": keypath,
                        "value": value,
                    },
                ) from e
        return True

    def _handle_chunk_reasoning_steps(self, context: StreamingContext, extracted: str | None) -> bool:
        if not extracted:
            return False

        if not context.reasoning:
            context.reasoning = extracted
        else:
            context.reasoning += extracted
        return True

    def _handle_chunk_tool_calls(
        self,
        context: StreamingContext,
        extracted: list[ToolCallRequest] | None,
    ) -> bool:
        if extracted:
            if not context.tool_calls:
                context.tool_calls = []
            context.tool_calls.extend(extracted)
        # Tool calls are only yielded once the stream is done
        return False

    def _handle_chunk(self, context: StreamingContext, chunk: bytes) -> bool:
        """Handles a chunk and returns true if there was an update"""
        delta = self._extract_stream_delta(chunk, context.raw_completion, context.tool_call_request_buffer)
        context.last_chunk = delta
        if not delta:
            return False

        should_yield = self._handle_chunk_output(context, delta.content)
        should_yield |= self._handle_chunk_reasoning_steps(context, delta.reasoning)
        should_yield |= self._handle_chunk_tool_calls(context, delta.tool_calls)
        return should_yield or bool(context.stream_deltas and delta.content)

    @override
    async def _single_stream(
        self,
        request: dict[str, Any],
        output_factory: Callable[[str, bool], ProviderOutput],
        partial_output_factory: Callable[[Any], ProviderOutput],
        raw_completion: RawCompletion,
        options: ProviderOptions,
    ) -> AsyncGenerator[ProviderOutput]:
        streaming_context: StreamingContext | None = None

        def _finally():
            raw_completion.response = streaming_context.streamer.raw_completion if streaming_context else None

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

                streaming_context = StreamingContext(
                    raw_completion,
                    json=options.output_schema is not None,
                    stream_deltas=options.stream_deltas,
                )
                async for chunk in self.wrap_sse(response.aiter_bytes()):
                    should_yield = self._handle_chunk(streaming_context, chunk)

                    if should_yield:
                        yield self._partial_structured_output(
                            partial_output_factory,
                            streaming_context,
                            options,
                        )

                # Always yield the final output
                # This is the output that will be needed to save the run
                yield self._build_structured_output(
                    output_factory,
                    streaming_context.streamer.raw_completion,
                    streaming_context.reasoning,
                    streaming_context.tool_calls,
                )

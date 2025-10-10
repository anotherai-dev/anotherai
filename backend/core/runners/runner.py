import json
import re
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from structlog import get_logger

from core.domain.agent import Agent
from core.domain.agent_completion import AgentCompletion
from core.domain.agent_input import AgentInput
from core.domain.cache_usage import CacheUsage
from core.domain.exceptions import JSONSchemaValidationError
from core.domain.fallback_option import FallbackOption
from core.domain.message import Message, MessageContent
from core.domain.metrics import send_counter
from core.domain.models.model_data import FinalModelData
from core.domain.tenant_data import ProviderSettings
from core.domain.tool import HostedTool, Tool
from core.domain.tool_call import ToolCallRequest
from core.domain.typology import IOTypology, Typology
from core.domain.version import Version
from core.providers._base.abstract_provider import AbstractProvider
from core.providers._base.builder_context import builder_context
from core.providers._base.provider_error import (
    InvalidGenerationError,
    MaxToolCallIterationError,
    ModelDoesNotSupportModeError,
    ProviderError,
)
from core.providers._base.provider_options import ProviderOptions
from core.providers.factory.abstract_provider_factory import AbstractProviderFactory
from core.runners._message_fixer import fix_messages
from core.runners._message_renderer import MessageRenderer
from core.runners._runner_file_handler import RunnerFileHandler
from core.runners.agent_completion_builder import AgentCompletionBuilder
from core.runners.provider_pipeline import ProviderPipeline
from core.runners.runner_output import RunnerOutput, RunnerOutputChunk
from core.runners.utils import cleanup_provider_json
from core.utils.json_utils import parse_tolerant_json
from core.utils.schemas import clean_json_string
from core.utils.templates import TemplateManager

_log = get_logger(__name__)
_template_manager = TemplateManager()

_json_schema_regexp = re.compile(r"json[ _-]?schema", re.IGNORECASE)


class Runner:
    def __init__(
        self,
        agent: Agent,
        tenant_slug: str,
        custom_configs: list[ProviderSettings] | None,
        version: Version,
        metadata: dict[str, Any] | None,
        metric_tags: dict[str, Any] | None,
        provider_factory: AbstractProviderFactory,
        timeout: float,
        use_fallback: FallbackOption,
        max_tool_call_iterations: int = 10,
    ):
        self._agent: Agent = agent
        self._version: Version = version

        self._metadata: dict[str, Any] | None = metadata
        self._custom_configs: list[ProviderSettings] | None = custom_configs
        self._tenant_slug: str = tenant_slug
        self._metric_tags: dict[str, Any] = {
            "tenant": tenant_slug,
            "agent_id": self._agent.id,
            "model": self._version.model,
            **(metric_tags or {}),
        }
        self._provider_factory: AbstractProviderFactory = provider_factory
        self._timeout: float = timeout
        self._use_fallback: FallbackOption = use_fallback
        self._max_tool_call_iterations: int = max_tool_call_iterations

    @property
    def _run_id(self) -> str | None:
        if ctx := builder_context.get():
            return ctx.id
        return None

    def _enabled_tools(self) -> list[Tool] | None:
        # TODO: add support for hosted tools
        return (
            [tool for tool in self._version.enabled_tools if isinstance(tool, Tool)]
            if self._version.enabled_tools
            else None
        )

    def _merge_metadata(self, metadata: dict[str, Any] | None) -> dict[str, Any]:
        if metadata is None:
            return self._metadata or {}
        if self._metadata is None:
            return metadata
        return {**self._metadata, **metadata}

    async def prepare_completion(
        self,
        agent_input: AgentInput,
        start_time: float,
        completion_id: UUID,
        metadata: dict[str, Any] | None = None,
        conversation_id: str | None = None,
        stream: bool = False,
    ) -> AgentCompletionBuilder:
        """Construct a task run builder for the given input and properties"""

        messages = await self._build_messages(agent_input)

        return AgentCompletionBuilder(
            id=completion_id,
            agent=self._agent,
            agent_input=agent_input,
            version=self._version,
            metadata=self._merge_metadata(metadata),
            start_time=start_time,
            conversation_id=conversation_id,
            messages=messages,
            stream=stream,
        )

    def _should_use_cache(self, cache: CacheUsage) -> bool:
        match cache:
            case CacheUsage.NEVER:
                return False
            case CacheUsage.ALWAYS:
                return True
            case CacheUsage.AUTO:
                return self._version.temperature == 0 and not self._version.enabled_tools

    @asynccontextmanager
    async def _wrap_for_metric(self):
        status = "success"
        try:
            yield
        except ProviderError as e:
            status = e.code
            raise e
        except Exception as e:
            status = "workflowai_internal_error"
            raise e
        finally:
            send_counter(
                "workflowai_inference",
                status=status,
                **self._metric_tags,
            )

    async def run(
        self,
        builder: AgentCompletionBuilder,
    ) -> AgentCompletion:
        """
        The main runner function that is called when an input is provided
        """
        _ = builder_context.set(builder)  # pyright: ignore [reportArgumentType]

        async with self._wrap_for_metric():
            try:
                output = await self._build_output(builder)
                return builder.build(output)
            except ProviderError as e:
                # Building the run to store it
                _ = builder.build(
                    output=RunnerOutput(None),
                    error=e.serialized(),
                )
                raise e

    async def stream(self, builder: AgentCompletionBuilder) -> AsyncIterator[RunnerOutputChunk]:
        _ = builder_context.set(builder)  # pyright: ignore [reportArgumentType]

        async with self._wrap_for_metric():
            async for o in self._stream_output(builder):
                # Making sure the chunk is built
                if final := o.final_chunk:
                    if builder.completion:
                        _log.warning("Task run already built. Likely had multiple final chunks")
                    # Forcing here, just in case we are in a case where we had multiple final chunks
                    builder.build(final, force=True)
                    yield o
                    break
                yield o

    def _build_provider_data(
        self,
        provider: AbstractProvider[Any, Any],
        model_data: FinalModelData,
        is_structured_generation_enabled: bool,
    ) -> tuple[AbstractProvider[Any, Any], ProviderOptions, FinalModelData]:
        provider_options = ProviderOptions(
            model=model_data.model,
            temperature=self._version.temperature or 0,
            max_tokens=self._version.max_output_tokens,
            output_schema=self._version.output_schema.json_schema if self._version.output_schema else None,
            task_name=self._agent.id,
            structured_generation=is_structured_generation_enabled,
            tenant=self._tenant_slug,
            top_p=self._version.top_p,
            presence_penalty=self._version.presence_penalty,
            frequency_penalty=self._version.frequency_penalty,
            parallel_tool_calls=self._version.parallel_tool_calls,
            enabled_tools=self._enabled_tools(),
            tool_choice=self._version.tool_choice,
            timeout=self._timeout,
            reasoning_effort=self._version.reasoning_effort,
            reasoning_budget=self._version.reasoning_budget,
        )

        model_data_copy = model_data.model_copy()
        provider.sanitize_model_data(model_data_copy)
        # TODO: this should move to the provider pipeline
        if provider_options.enabled_tools:
            self._check_tool_calling_support(model_data)

        # Overriding the structured generation flag if the model does not support it
        # Post provider override
        if not model_data_copy.supports_structured_output:
            provider_options.structured_generation = False

        return provider, provider_options, model_data_copy

    def _check_tool_calling_support(self, model_data: FinalModelData):
        if not model_data.supports_tool_calling:
            raise ModelDoesNotSupportModeError(
                model=model_data.model,
                msg=f"{model_data.model.value} does not support tool calling",
            )

    def _build_pipeline(self, builder: AgentCompletionBuilder):
        pipeline = ProviderPipeline(
            agent_id=self._agent.id,
            version=self._version,
            custom_configs=self._custom_configs,
            factory=self._provider_factory,
            builder=self._build_provider_data,
            typology=IOTypology(input=builder.agent_input.typology, output=Typology()),
            use_fallback=self._use_fallback,
        )

        return pipeline

    async def _build_messages(self, agent_input: AgentInput):
        base = await MessageRenderer.render(_template_manager, agent_input.variables, self._version.prompt)
        if agent_input.messages:
            for m in agent_input.messages:
                for f in m.file_iterator():
                    f.sanitize()
            base.extend(agent_input.messages)

        return base

    async def _build_output(self, builder: AgentCompletionBuilder) -> RunnerOutput:
        """
        The function that does the actual input -> output conversion, should
        be overriden in each subclass but not called directly.
        """
        pipeline = self._build_pipeline(builder)

        # TODO: model_data
        for provider, options, _ in pipeline.provider_iterator(raise_at_end=True):
            with pipeline.wrap_provider_call(provider):
                return await self._build_output_from_messages(provider, options, builder.messages)

        # Will never be reached since raise_at_end is True
        # Returning for type safety
        return pipeline.raise_on_end()

    async def _prepare_messages(
        self,
        messages: Sequence[Message],
        provider: AbstractProvider[Any, Any],
        options: ProviderOptions,
    ) -> list[Message]:
        # First handle all files as needed
        file_handler = RunnerFileHandler(options.model, provider, self._record_file_download_seconds)
        await file_handler.handle_files_in_messages(messages)

        messages = fix_messages(messages)

        if options.structured_generation or options.output_schema is None:
            return messages

        # Otherwise we append the output format to the first system message
        try:
            system_message = next(m for m in messages if m.role in ("system", "developer"))
        except StopIteration:
            system_message = Message(role="system", content=[MessageContent(text="")])
            messages.insert(0, system_message)

        try:
            text_content = next(m for m in system_message.content if m.text is not None)
        except StopIteration:
            text_content = MessageContent(text="")
            system_message.content.append(text_content)

        if not options.output_schema and text_content.text and _json_schema_regexp.search(text_content.text):
            # options.output_schema is an empty dict. Meaning that the user has simply requested JSON mode
            # + the system message already contains the word "JSON" so we can safely return
            return messages

        # Otherwise we need to request a JSON file or inline the output schema

        tool_call_str = "either tool call(s) or " if options.enabled_tools else ""
        schema_str = (
            f""" enforcing the following schema:
```json
{json.dumps(options.output_schema, indent=2)}
```"""
            if options.output_schema
            else ""
        )
        suffix = f"Return {tool_call_str}a single JSON object{schema_str}"
        prefix = f"{text_content.text}\n\n" if text_content.text else ""
        text_content.text = f"{prefix}{suffix}"
        return messages

    async def _build_output_from_messages(
        self,
        provider: AbstractProvider[Any, Any],
        options: ProviderOptions,
        messages: list[Message],
    ) -> RunnerOutput:
        iteration_count = 0
        current_messages = await self._prepare_messages(messages, provider, options)

        while iteration_count < self._max_tool_call_iterations:
            iteration_count += 1

            provider_output = await provider.complete(
                current_messages,
                options,
                self.output_factory,
            )
            internal_tools, external_tools = self._split_tools(provider_output.tool_call_requests)

            # TODO: external_tools
            if internal_tools:
                raise NotImplementedError("Internal tools are not supported yet")

            return RunnerOutput(
                agent_output=provider_output.agent_output,
                reasoning=provider_output.reasoning,
                tool_call_requests=external_tools,
            )

        raise MaxToolCallIterationError(
            f"Tool calls failed to converge after {self._max_tool_call_iterations} iterations",
        )

    async def _stream_task_output_from_messages(
        self,
        provider: AbstractProvider[Any, Any],
        options: ProviderOptions,
        messages: list[Message],
    ) -> AsyncIterator[RunnerOutputChunk]:
        if not provider.is_streamable(options.model, options.enabled_tools):
            yield (await self._build_output_from_messages(provider, options, messages)).as_chunk()
            return

        iteration_count = 0

        while iteration_count < self._max_tool_call_iterations:
            iteration_count += 1

            chunk: RunnerOutputChunk | None = None
            final_output: RunnerOutput | None = None
            async for chunk in provider.stream(
                messages,
                options,
                output_factory=self.output_factory,
            ):
                final_output = chunk.final_chunk
                if final_output:
                    # We will stream the final output after the end of the stream.
                    # This way the provider has time to perform any operation on the context if needed
                    continue
                yield chunk

            if not final_output:
                # We never had any output, we can stop the stream
                _log.error("No output from provider")
                return

            internal_tools, _ = self._split_tools(final_output.tool_call_requests)

            if not internal_tools:
                if chunk:
                    yield chunk
                return

            # TODO:
            raise NotImplementedError("Internal tools are not supported yet")

            # # We add the returned tool calls to the external tool cache
            # # TODO:
            # # await self._external_tool_cache.ingest(external_tools)

            # try:
            #     tool_results = await self._run_tool_calls(output.tool_calls, messages)
            # except ToolCallRecursionError:
            #     # If all tool calls have already been called with the same arguments, we stop the iteration
            #     # and return the output as is
            #     if output.output:
            #         yield await self._final_run_output(output, include_tool_calls=False)
            #         return
            #     raise MaxToolCallIterationError(
            #         f"Tool calls failed to converge after {iteration_count} iterations",
            #         capture=True,
            #     )
            # messages = self._append_tool_call_requests_to_messages(messages, output.tool_calls)
            # messages = self.append_tool_result_to_messages(messages, tool_results)

        raise MaxToolCallIterationError(
            f"Tool calls failed to converge after {self._max_tool_call_iterations} iterations",
        )

    async def _stream_output(self, builder: AgentCompletionBuilder) -> AsyncIterator[RunnerOutputChunk]:
        pipeline = self._build_pipeline(builder)
        for provider, options, _ in pipeline.provider_iterator():
            with pipeline.wrap_provider_call(provider):
                messages = await self._build_messages(builder.agent_input)
                async for o in self._stream_task_output_from_messages(
                    provider,
                    options,
                    messages,
                ):
                    yield o
                return

        pipeline.raise_on_end()

    def output_factory(self, raw: str) -> Any:
        """Builds an output from a raw string.
        Output can either be a string or a structured output
        """
        if self._version.output_schema is None:
            return raw

        json_str = raw.replace("\t", "\\t")
        # Acting on the string is probably unefficient, we do multiple decodes and encode
        # On the payload. Instead we should probably retrieve bytes for the output
        # and act on that.
        json_str = clean_json_string(json_str)

        try:
            json_dict = json.loads(json_str)
        except json.JSONDecodeError:
            _log.info(
                "Attempting to build output from invalid json",
                run_id=self._run_id,
                exc_info=True,
            )
            # When the normal json parsing fails, we try and decode it with a tolerant stream handler
            json_dict = parse_tolerant_json(json_str)
        json_dict = cleanup_provider_json(json_dict)

        try:
            return self._version.validate_output(json_dict)
        except (ValidationError, JSONSchemaValidationError) as e:
            raise InvalidGenerationError(msg=str(e), partial_output=raw) from e

    def _split_tools(
        self,
        tool_calls: Sequence[ToolCallRequest] | None,
    ) -> tuple[Sequence[ToolCallRequest] | None, Sequence[ToolCallRequest] | None]:
        """Split tools into internal and external tools"""
        if not tool_calls:
            return None, None

        # First assigning tool call indices
        for i, tool_call in enumerate(tool_calls):
            tool_call.index = i

        internal_tools: list[ToolCallRequest] = []
        external_tools: list[ToolCallRequest] = []
        for tool_call in tool_calls:
            arr = internal_tools if tool_call.tool_name in HostedTool else external_tools
            arr.append(tool_call)
        return internal_tools or None, external_tools or None

    def _record_file_download_seconds(self, val: float):
        if ctx := builder_context.get():
            ctx.record_file_download_seconds(val)

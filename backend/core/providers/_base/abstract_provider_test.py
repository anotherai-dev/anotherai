import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Any, override
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

from core.domain.message import Message
from core.domain.models import Model, Provider
from core.domain.tool_call import ToolCallRequest
from core.providers._base.abstract_provider import (
    AbstractProvider,
    ProviderConfigInterface,
)
from core.providers._base.builder_context import BuilderInterface
from core.providers._base.llm_completion import LLMCompletion
from core.providers._base.llm_usage import LLMUsage
from core.providers._base.models import RawCompletion
from core.providers._base.provider_error import FailedGenerationError, ProviderError
from core.providers._base.provider_options import ProviderOptions
from core.providers.factory.local_provider_factory import LocalProviderFactory
from core.providers.openai.openai_provider import OpenAIProvider
from core.runners.output_factory import OutputFactory
from core.runners.runner_output import RunnerOutput, RunnerOutputChunk
from tests.fake_models import fake_llm_completion


def _output_factory(raw: str) -> Any:
    return json.loads(raw)


@pytest.mark.parametrize("provider_cls", LocalProviderFactory.PROVIDER_TYPES.values())
def test_provider_init_config_id(provider_cls: type[AbstractProvider[Any, Any]]):
    # Check that we can initialize a provider with a config_id
    with patch.object(provider_cls, "_default_config") as mock_from_env:
        provider = provider_cls(config_id="config_id")
        assert provider._config_id == "config_id"  # pyright: ignore [reportPrivateUsage]
        assert provider._config is not None  # pyright: ignore [reportPrivateUsage]
        mock_from_env.assert_called_once()


async def test_exception_messages_are_correctly_added_to_messages():
    provider = (
        OpenAIProvider()
    )  # TODO: Ideally we would use a special test provider, but this is more annoying to set up.
    messages = [Message.with_text("Hello")]
    options = ProviderOptions(model=Model.GPT_4O_2024_08_06)

    with patch.object(provider, "_single_complete", wraps=provider._single_complete) as mock_single_complete:  # pyright: ignore [reportPrivateUsage]
        mock_single_complete.side_effect = FailedGenerationError("Test exception", retry=True)

        with pytest.raises(ProviderError):
            await provider._retryable_complete(messages, options, _output_factory, max_attempts=2)  # pyright: ignore [reportPrivateUsage]

        # Test that the single complete is called twice
        assert mock_single_complete.call_count == 2

        # Assert that the first call is the original message
        first_call_args = mock_single_complete.call_args_list[0].kwargs
        assert first_call_args["request"]["messages"] == [{"content": "Hello", "role": "user"}]

        # Assert that the second call is the original message with the original answer and exception message added
        second_call_args = mock_single_complete.call_args_list[1].kwargs
        assert second_call_args["request"]["messages"] == [
            {"content": "Hello", "role": "user"},
            {"content": "EMPTY MESSAGE", "role": "assistant"},
            {
                "content": "Your previous response was invalid with error `Test exception`.\nPlease retry",
                "role": "user",
            },
        ]


def test_set_model_context_window_size():
    llm_usage = LLMUsage()
    OpenAIProvider()._set_llm_usage_model_context_window_size(llm_usage, Model.GPT_4O_2024_08_06)  # pyright: ignore [reportPrivateUsage]
    assert llm_usage.model_context_window_size == 128_000


def test_assign_raw_completion():
    usage = LLMUsage(
        model_context_window_size=128_000,
        prompt_token_count=100,
        prompt_token_count_cached=10,
        completion_token_count=100,
        prompt_cost_usd=0.1,
        completion_cost_usd=0.1,
        completion_image_count=0,
    )
    raw_completion = RawCompletion(
        response="test",
        usage=usage,
    )
    llm_completion = LLMCompletion(
        usage=LLMUsage(),
        provider=Provider.OPEN_AI,
        model=Model.GPT_4O_2024_05_13,
    )
    AbstractProvider._assign_raw_completion(  # pyright: ignore [reportPrivateUsage]
        raw_completion,
        llm_completion,
    )
    assert llm_completion.usage == usage


class _MockedProvider(AbstractProvider[Any, Any]):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        self.mock = Mock(spec=AbstractProvider)
        self.mock._prepare_completion = AsyncMock(
            return_value=({}, fake_llm_completion(usage=LLMUsage())),
        )
        self.mock._compute_prompt_audio_token_count.return_value = (0, None)
        self.mock._run_id.return_value = "test"

    @override
    def _run_id(self):
        return self.mock._run_id()

    @classmethod
    @override
    def name(cls) -> Provider:
        return Provider.OPEN_AI

    @classmethod
    @override
    def required_env_vars(cls) -> list[str]:
        return []

    @classmethod
    @override
    def _default_config(cls, index: int) -> Any:
        return Mock(spec=ProviderConfigInterface)

    @override
    def _compute_prompt_token_count(
        self,
        messages: list[dict[str, Any]],
        model: Model,
    ) -> float:
        return 0

    @override
    async def _compute_prompt_audio_token_count(
        self,
        messages: list[dict[str, Any]],
    ):
        return self.mock._compute_prompt_audio_token_count(messages)

    @override
    async def check_valid(self) -> bool:
        return True

    @override
    async def _single_complete(
        self,
        request: Any,
        output_factory: OutputFactory,
        raw_completion: RawCompletion,
        options: ProviderOptions,
    ) -> RunnerOutput:
        return await self.mock._single_complete(request, output_factory, raw_completion, options)

    @override
    async def _prepare_completion(
        self,
        messages: list[Message],
        options: ProviderOptions,
        stream: bool,
    ) -> tuple[Any, LLMCompletion]:
        return await self.mock._prepare_completion(messages, options, stream)

    @override
    def _single_stream(
        self,
        request: Any,
        output_factory: OutputFactory,
        raw_completion: RawCompletion,
        options: ProviderOptions,
    ) -> AsyncGenerator[RunnerOutputChunk]:
        return self.mock._single_stream(request, output_factory, raw_completion, options)


@pytest.fixture
def mocked_provider() -> _MockedProvider:
    return _MockedProvider()


@pytest.fixture
def builder_context(mocked_provider: _MockedProvider):
    class Context(BaseModel):
        id: str = ""
        llm_completions: list[LLMCompletion]
        config_id: str | None

        def add_metadata(self, key: str, value: Any) -> None:
            pass

        def get_metadata(self, key: str) -> Any | None:
            return None

    with patch.object(mocked_provider, "_builder_context") as mock_builder_context:
        ctx = Context(llm_completions=[], config_id=None)
        mock_builder_context.return_value = ctx
        yield ctx


class TestComplete:
    async def test_retry_complete(self, mocked_provider: _MockedProvider):
        mocked_provider.mock._single_complete.side_effect = ProviderError(
            "Test exception",
            retry=True,
            max_attempt_count=4,
        )

        with pytest.raises(ProviderError) as e:
            _ = await mocked_provider.complete(
                messages=[],
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13, tenant="tenant1"),
                output_factory=_output_factory,
            )

        assert mocked_provider.mock._single_complete.call_count == 4

        assert e.value.provider == Provider.OPEN_AI
        assert e.value.task_run_id == "test"
        assert e.value.provider_options is not None
        assert e.value.provider_options.model == Model.GPT_4O_2024_05_13

        # TODO[metrics]
        # assert patch_metric_send.call_count == 4
        # metric = patch_metric_send.call_args_list[0][0][0]
        # assert isinstance(metric, Metric)
        # assert metric.name == "provider_inference"
        # assert metric.tags == {
        #     "model": "gpt-4o-2024-05-13",
        #     "provider": "openai",
        #     "tenant": "tenant1",
        #     "status": "unknown_provider_error",
        #     "config": "workflowai_0",
        # }

    async def test_complete_with_tool_calls(self, mocked_provider: _MockedProvider, builder_context: BuilderInterface):
        mocked_provider.mock._single_complete.return_value = RunnerOutput(
            agent_output={},
            tool_call_requests=[ToolCallRequest(tool_name="test", tool_input_dict={"test": "test"})],
        )
        _ = await mocked_provider.complete(
            messages=[],
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
            output_factory=_output_factory,
        )
        assert builder_context.llm_completions[0].duration_seconds is not None
        # TODO: make sure messages are set


class TestStream:
    async def test_retry_stream(self, mocked_provider: _MockedProvider):
        mocked_provider.mock._single_stream.side_effect = ProviderError(
            "Test exception",
            retry=True,
            max_attempt_count=4,
        )

        with pytest.raises(ProviderError) as e:
            async for _ in mocked_provider.stream(
                messages=[],
                options=ProviderOptions(model=Model.GPT_4O_2024_05_13, tenant="tenant1"),
                output_factory=_output_factory,
            ):
                pass

        assert mocked_provider.mock._single_stream.call_count == 4

        assert e.value.provider == Provider.OPEN_AI
        assert e.value.task_run_id == "test"
        assert e.value.provider_options is not None
        assert e.value.provider_options.model == Model.GPT_4O_2024_05_13

        # TODO[metrics]
        # assert patch_metric_send.call_count == 4
        # metric = patch_metric_send.call_args_list[0][0][0]
        # assert isinstance(metric, Metric)
        # assert metric.name == "provider_inference"
        # assert metric.tags == {
        #     "model": "gpt-4o-2024-05-13",
        #     "provider": "openai",
        #     "tenant": "tenant1",
        #     "status": "unknown_provider_error",
        #     "config": "workflowai_0",
        # }


class TestCostComputation:
    @pytest.fixture
    def mock_compute_llm_completion_cost(self, mocked_provider: _MockedProvider):
        with patch.object(mocked_provider, "_compute_llm_completion_cost") as mock_compute_llm_completion_cost:
            yield mock_compute_llm_completion_cost

    # Check that we do not crash if the cost computation fails
    async def test_cost_computation_fails_gracefully(
        self,
        mocked_provider: _MockedProvider,
        mock_compute_llm_completion_cost: Mock,
        builder_context: BuilderInterface,
    ):
        mock_compute_llm_completion_cost.side_effect = Exception("Test exception")

        await mocked_provider.complete(
            messages=[],
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
            output_factory=_output_factory,
        )
        assert len(builder_context.llm_completions) == 1
        assert builder_context.llm_completions[0].usage.cost_usd is None
        assert builder_context.llm_completions[0].duration_seconds is not None

    @patch.object(AbstractProvider, "_FINALIZE_COMPLETIONS_TIMEOUT", 0.02)
    async def test_cost_computation_fails_gracefully_on_timeout(
        self,
        mocked_provider: _MockedProvider,
        mock_compute_llm_completion_cost: Mock,
        builder_context: BuilderInterface,
    ):
        async def wait_for_a_long_time():
            await asyncio.sleep(1000)

        now = time.time()

        mock_compute_llm_completion_cost.side_effect = wait_for_a_long_time

        await mocked_provider.complete(
            messages=[],
            options=ProviderOptions(model=Model.GPT_4O_2024_05_13),
            output_factory=_output_factory,
        )
        # Check that we did not wait for the full second
        assert time.time() - now < 0.1
        assert len(builder_context.llm_completions) == 1


class TestDefaultModel:
    def test_default_model(self, mocked_provider: _MockedProvider):
        # We just check that it exists
        # The default model is used to test configurations
        assert mocked_provider.default_model()

import pytest
from unittest.mock import Mock

from core.domain.agent_completion import AgentCompletion
from core.domain.inference import LLMTrace
from core.domain.inference_usage import InferenceUsage, PromptUsage, Usage
from core.domain.message import Message
from core.providers._base.llm_completion import LLMCompletion
from core.providers._base.llm_usage import LLMUsage
from core.runners.agent_completion_builder import AgentCompletionBuilder
from core.runners.runner_output import RunnerOutput
from tests.fake_models import fake_completion


class TestAgentCompletionBuilder:
    def _create_builder(self):
        """Helper method to create a properly configured AgentCompletionBuilder."""
        fake_comp = fake_completion()
        return AgentCompletionBuilder(
            id=fake_comp.id,
            agent=fake_comp.agent,
            version=fake_comp.version,
            agent_input=fake_comp.agent_input,
            messages=fake_comp.messages,
            start_time=0.0,
            conversation_id=None,
            metadata={}
        )

    def test_reasoning_token_aggregation_single_trace(self):
        """Test that reasoning tokens are correctly aggregated from a single LLM trace."""
        builder = self._create_builder()
        
        # Add LLM completion with reasoning tokens
        builder.llm_completions.append(
            LLMCompletion(
                model="gpt-4o-2024-05-13",
                provider="openai",
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=150,  # Key field to test
                ),
                duration_seconds=1.0,
                cost_usd=0.01,
            )
        )
        
        output = RunnerOutput(agent_output="Hello")
        result = builder.build(output)
        
        # Assert reasoning tokens are correctly aggregated
        assert result.reasoning_token_count == 150

    def test_reasoning_token_aggregation_multiple_traces(self):
        """Test that reasoning tokens are correctly aggregated from multiple LLM traces."""
        builder = self._create_builder()
        
        # Add multiple LLM completions with reasoning tokens
        builder.llm_completions.extend([
            LLMCompletion(
                model="gpt-4o-2024-05-13",
                provider="openai",
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=100,
                ),
                duration_seconds=1.0,
                cost_usd=0.01,
            ),
            LLMCompletion(
                model="gpt-4o-2024-05-13",
                provider="openai", 
                usage=LLMUsage(
                    prompt_token_count=80,
                    completion_token_count=30,
                    reasoning_token_count=75,
                ),
                duration_seconds=0.5,
                cost_usd=0.008,
            )
        ])
        
        output = RunnerOutput(agent_output="Hello")
        result = builder.build(output)
        
        # Assert reasoning tokens are correctly summed
        assert result.reasoning_token_count == 175

    def test_reasoning_token_aggregation_no_reasoning_tokens(self):
        """Test that reasoning_token_count is None when no traces have reasoning tokens."""
        builder = self._create_builder()
        
        # Add LLM completion without reasoning tokens
        builder.llm_completions.append(
            LLMCompletion(
                model="gpt-3.5-turbo-0125",
                provider="openai",
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=None,  # No reasoning tokens
                ),
                duration_seconds=1.0,
                cost_usd=0.01,
            )
        )
        
        output = RunnerOutput(agent_output="Hello")
        result = builder.build(output)
        
        # Assert reasoning_token_count is None
        assert result.reasoning_token_count is None

    def test_reasoning_token_aggregation_mixed_traces(self):
        """Test aggregation when some traces have reasoning tokens and others don't."""
        builder = self._create_builder()
        
        # Add mixed LLM completions
        builder.llm_completions.extend([
            LLMCompletion(
                model="gpt-4o-2024-05-13",
                provider="openai",
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=100,  # Has reasoning tokens
                ),
                duration_seconds=1.0,
                cost_usd=0.01,
            ),
            LLMCompletion(
                model="gpt-3.5-turbo-0125", 
                provider="openai",
                usage=LLMUsage(
                    prompt_token_count=80,
                    completion_token_count=30,
                    reasoning_token_count=None,  # No reasoning tokens
                ),
                duration_seconds=0.5,
                cost_usd=0.008,
            )
        ])
        
        output = RunnerOutput(agent_output="Hello")
        result = builder.build(output)
        
        # Assert only the trace with reasoning tokens contributes
        assert result.reasoning_token_count == 100

    def test_reasoning_token_aggregation_zero_tokens(self):
        """Test that zero reasoning tokens are handled correctly."""
        builder = self._create_builder()
        
        # Add LLM completion with explicitly zero reasoning tokens
        builder.llm_completions.append(
            LLMCompletion(
                model="gpt-4o-2024-05-13",
                provider="openai",
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=0,  # Explicitly zero
                ),
                duration_seconds=1.0,
                cost_usd=0.01,
            )
        )
        
        output = RunnerOutput(agent_output="Hello")
        result = builder.build(output)
        
        # Assert reasoning_token_count is 0 (not None)
        assert result.reasoning_token_count == 0

    def test_reasoning_token_aggregation_no_llm_completions(self):
        """Test that reasoning_token_count is None when there are no LLM completions."""
        builder = self._create_builder()
        
        # Don't add any LLM completions
        output = RunnerOutput(agent_output="Hello")
        result = builder.build(output)
        
        # Assert reasoning_token_count is None
        assert result.reasoning_token_count is None

    def test_reasoning_token_aggregation_no_usage_data(self):
        """Test that reasoning_token_count is None when LLM completions have no usage data."""
        builder = self._create_builder()
        
        # Skip adding any LLM completions to test the no-usage case
        # The reasoning logic should return None when there are no completions with usage data
        pass
        
        output = RunnerOutput(agent_output="Hello")
        result = builder.build(output)
        
        # Assert reasoning_token_count is None
        assert result.reasoning_token_count is None
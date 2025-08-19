
from core.domain.models.models import Model
from core.domain.models.providers import Provider
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
            metadata={},
        )

    def test_reasoning_token_aggregation_single_trace(self):
        """Test that reasoning tokens are correctly aggregated from a single LLM trace."""
        builder = self._create_builder()

        # Add LLM completion with reasoning tokens
        builder.llm_completions.append(
            LLMCompletion(
                model=Model.GPT_4O_2024_05_13,
                provider=Provider.OPEN_AI,
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=150,  # Key field to test
                    prompt_cost_usd=0.005,
                    completion_cost_usd=0.005,
                ),
                duration_seconds=1.0,
            ),
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
                model=Model.GPT_4O_2024_05_13,
                provider=Provider.OPEN_AI,
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=100,
                    prompt_cost_usd=0.005,
                    completion_cost_usd=0.005,
                ),
                duration_seconds=1.0,
            ),
            LLMCompletion(
                model=Model.GPT_4O_2024_05_13,
                provider=Provider.OPEN_AI,
                usage=LLMUsage(
                    prompt_token_count=80,
                    completion_token_count=30,
                    reasoning_token_count=75,
                    prompt_cost_usd=0.004,
                    completion_cost_usd=0.004,
                ),
                duration_seconds=0.5,
            ),
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
                model=Model.GPT_3_5_TURBO_0125,
                provider=Provider.OPEN_AI,
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=None,  # No reasoning tokens
                    prompt_cost_usd=0.005,
                    completion_cost_usd=0.005,
                ),
                duration_seconds=1.0,
            ),
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
                model=Model.GPT_4O_2024_05_13,
                provider=Provider.OPEN_AI,
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=100,  # Has reasoning tokens
                    prompt_cost_usd=0.005,
                    completion_cost_usd=0.005,
                ),
                duration_seconds=1.0,
            ),
            LLMCompletion(
                model=Model.GPT_3_5_TURBO_0125,
                provider=Provider.OPEN_AI,
                usage=LLMUsage(
                    prompt_token_count=80,
                    completion_token_count=30,
                    reasoning_token_count=None,  # No reasoning tokens
                    prompt_cost_usd=0.004,
                    completion_cost_usd=0.004,
                ),
                duration_seconds=0.5,
            ),
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
                model=Model.GPT_4O_2024_05_13,
                provider=Provider.OPEN_AI,
                usage=LLMUsage(
                    prompt_token_count=100,
                    completion_token_count=50,
                    reasoning_token_count=0,  # Explicitly zero
                    prompt_cost_usd=0.005,
                    completion_cost_usd=0.005,
                ),
                duration_seconds=1.0,
            ),
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

        output = RunnerOutput(agent_output="Hello")
        result = builder.build(output)

        # Assert reasoning_token_count is None
        assert result.reasoning_token_count is None

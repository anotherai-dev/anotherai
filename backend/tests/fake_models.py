import uuid
from datetime import UTC, date, datetime
from typing import Any

from core.domain.agent import Agent
from core.domain.agent_completion import AgentCompletion
from core.domain.agent_input import AgentInput
from core.domain.agent_output import AgentOutput
from core.domain.annotation import Annotation
from core.domain.deployment import Deployment
from core.domain.experiment import Experiment
from core.domain.inference_usage import CompletionUsage, InferenceUsage, TokenUsage
from core.domain.message import Message
from core.domain.models._displayed_provider import DisplayedProvider
from core.domain.models.model_data import MaxTokensData, ModelData, QualityData, SpeedData, SpeedIndex
from core.domain.models.models import Model
from core.domain.models.providers import Provider
from core.domain.tenant_data import TenantData
from core.domain.trace import LLMTrace
from core.domain.version import Version
from core.domain.view import Graph, View, ViewFolder
from core.providers._base.llm_completion import LLMCompletion
from core.providers._base.llm_usage import LLMUsage
from core.utils.uuid import uuid7


def fake_version(**kwargs: Any):
    version = Version(
        model="gpt-4o-mini",
        provider="openai",
        temperature=0.5,
        max_output_tokens=100,
        use_structured_generation=False,
        tool_choice=None,
        prompt=[Message.with_text("Your name is {{name}}", role="system")],
    )
    # Using model_validate to force validation and recompute the id
    return version.model_validate(
        {
            **version.model_dump(exclude={"id"}),
            **kwargs,
        },
    )


def fake_input(**kwargs: Any):
    base = AgentInput(
        variables={
            "name": "John",
        },
    )
    return base.model_validate(
        {
            **base.model_dump(exclude={"id"}),
            **kwargs,
        },
    )


def fake_completion(agent: Agent | None = None, id_rand: int = 1, **kwargs: Any):
    base = AgentCompletion(
        agent=agent or Agent(uid=1, id="hello", name="hello", created_at=datetime(2025, 1, 1, 1, 1, 1, tzinfo=UTC)),
        id=uuid7(ms=lambda: 0, rand=lambda: id_rand),
        duration_seconds=1.0,
        cost_usd=1.0,
        traces=[
            LLMTrace(
                model="gpt-4o-mini",
                provider="openai",
                duration_seconds=1.0,
                cost_usd=3.0,
                usage=InferenceUsage(
                    prompt=TokenUsage(
                        cost_usd=1.0,
                    ),
                    completion=CompletionUsage(
                        cached_token_count=100,
                        reasoning_token_count=100,
                        text_token_count=100,
                        cost_usd=2.0,
                    ),
                ),
            ),
        ],
        from_cache=False,
        metadata={
            "user_id": "user_123",
            "int_value": 1,
            "float_value": 1.0,
            "bool_value": True,
            "string_value": "hello",
            "array_value": [1, 2, 3],
            "object_value": {"key": "value"},
        },
        source="api",
        agent_input=AgentInput(
            preview="hello",
            variables={
                "name": "John",
            },
            messages=[Message.with_text("hello, who are you?")],
        ),
        agent_output=AgentOutput(
            preview="hello",
            messages=[Message.with_text("Hello my name is John", role="assistant")],
            error=None,
        ),
        messages=[
            Message.with_text("Your name is John", role="system"),
            Message.with_text("hello, who are you?", role="user"),
        ],
        version=fake_version(),
    )

    return base.model_copy(update=kwargs)


def fake_llm_completion(**kwargs: Any):
    completion = LLMCompletion(
        model=Model.GPT_4O_2024_05_13,
        provider=Provider.OPEN_AI,
        usage=LLMUsage(
            prompt_token_count=100,
            completion_token_count=100,
        ),
    )
    return completion.model_copy(update=kwargs)


def fake_model_data(**kwargs: Any):
    return ModelData(
        display_name="Llama 3.1 (70B)",
        supports_json_mode=True,
        supports_input_image=False,
        supports_input_pdf=False,
        supports_input_audio=False,
        max_tokens_data=MaxTokensData(
            max_tokens=128000,
            source="https://github.com/meta-llama/llama-models/blob/main/models/llama3_1/MODEL_CARD.md",
        ),
        icon_url="https://workflowai.blob.core.windows.net/workflowai-public/meta.svg",
        release_date=date(2024, 7, 23),
        quality_data=QualityData(mmlu=86, gpqa=48),
        speed_data=SpeedData(index=SpeedIndex(value=500)),
        provider_name=DisplayedProvider.FIREWORKS.value,
        supports_tool_calling=True,
        fallback=None,
    ).model_copy(update=kwargs)


def fake_tool():
    """Create a fake tool for testing purposes"""
    return {"name": "test_tool", "description": "A test tool"}


def fake_experiment(**kwargs: Any):
    base = Experiment(
        id="test-experiment",
        author_name="Test Author",
        title="Test Experiment",
        description="A test experiment",
        result=None,
        agent_id="test-agent",
        run_ids=[],
        metadata={"key": "value"},
    )
    return Experiment.model_validate(
        {
            **base.model_dump(),
            **kwargs,
        },
    )


def fake_annotation(**kwargs: Any):
    return Annotation(
        id="test-annotation",
        author_name="Test Author",
        target=Annotation.Target(
            completion_id=uuid7(ms=lambda: 0, rand=lambda: 1),
            experiment_id="test-experiment",
            key_path="response.message",
        ),
        context=Annotation.Context(experiment_id="test-experiment"),
        text="This is a test annotation",
        metric=Annotation.Metric(name="quality", value=8.5),
        metadata={"key": "value"},
    ).model_copy(update=kwargs)


def fake_graph(**kwargs: Any):
    return Graph(type="line", attributes={"x": {"field": "created_at"}, "y": [{"field": "count"}]})


def fake_view(**kwargs: Any):
    """Create a fake dashboard view for testing purposes"""
    return View(
        id=f"test-view-{uuid.uuid4().hex[:8]}",
        title="Test View",
        query="SELECT COUNT(*) FROM users",
        graph=fake_graph(),
    ).model_copy(update=kwargs)


def fake_view_folder(**kwargs: Any):
    """Create a fake dashboard for testing purposes"""
    return ViewFolder(
        id=f"test-view-folder-{uuid.uuid4().hex[:8]}",
        name="Test View Folder",
        views=[fake_view()],
    )


def fake_deployment(**kwargs: Any):
    base = Deployment(
        id="test-deployment",
        agent_id="test-agent",
        version=fake_version(),
        created_by="test-user",
        created_at=datetime.now(UTC),
        metadata=None,
    )
    return base.model_copy(update=kwargs)


def fake_tenant(**kwargs: Any):
    base = TenantData(
        uid=1,
        slug="test-tenant",
        org_id="test-org",
        owner_id="test-owner",
    )
    return TenantData.model_validate(
        {
            **base.model_dump(),
            **kwargs,
        },
    )

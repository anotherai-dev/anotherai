import uuid
from asyncio import gather

import pytest

from core.domain.agent import Agent
from core.domain.annotation import Annotation
from core.domain.experiment import Experiment
from core.storage.annotation_storage import ContextFilter, TargetFilter
from core.storage.psql.psql_agent_storage import PsqlAgentsStorage
from core.storage.psql.psql_annotation_storage import PsqlAnnotationStorage
from core.storage.psql.psql_experiment_storage import PsqlExperimentStorage
from core.utils.uuid import uuid7
from tests.fake_models import fake_annotation, fake_experiment


@pytest.fixture
async def test_agent(agent_storage: PsqlAgentsStorage):
    agent = Agent(uid=0, id=f"test-agent-{uuid.uuid4().hex[:8]}", name="Test Agent")
    await agent_storage.store_agent(agent)
    return agent


@pytest.fixture
async def test_experiment(experiment_storage: PsqlExperimentStorage, test_agent: Agent):
    experiment = fake_experiment(
        id=f"test-experiment-{uuid.uuid4().hex[:8]}",
        agent_id=test_agent.id,
        run_ids=["00000000-0000-0007-0000-000000000001"],
    )
    await experiment_storage.create(experiment)
    return experiment


@pytest.fixture
def sample_annotation(test_experiment: Experiment):
    return fake_annotation(
        id=f"test-annotation-{uuid.uuid4().hex[:8]}",
        target=Annotation.Target(
            completion_id=uuid7(ms=lambda: 0, rand=lambda: 1),
            experiment_id=test_experiment.id,
            key_path="response.message",
        ),
        context=Annotation.Context(experiment_id=test_experiment.id),
    )


class TestCreate:
    async def test_create_single_annotation(
        self,
        annotation_storage: PsqlAnnotationStorage,
        sample_annotation: Annotation,
    ):
        await annotation_storage.create(sample_annotation)

        # Verify the annotation was created by listing it
        annotations = await annotation_storage.list(None, None, None, 10)
        created_annotation = next((a for a in annotations if a.id == sample_annotation.id), None)
        assert created_annotation is not None
        assert created_annotation.id == sample_annotation.id
        assert created_annotation.author_name == sample_annotation.author_name
        assert created_annotation.text == sample_annotation.text
        assert created_annotation.target == sample_annotation.target
        assert created_annotation.context == sample_annotation.context
        assert created_annotation.metric == sample_annotation.metric
        assert created_annotation.metadata == sample_annotation.metadata

    async def test_create_annotation_without_optional_fields(
        self,
        annotation_storage: PsqlAnnotationStorage,
        test_agent: Agent,
    ):
        # Create a minimal annotation with just agent reference
        minimal_annotation = Annotation(
            id=f"minimal-annotation-{uuid.uuid4().hex[:8]}",
            author_name="Test Author",
            target=None,
            context=None,
            text=None,
            metric=None,
            metadata=None,
        )

        await annotation_storage.create(minimal_annotation)

        # Verify the annotation was created
        annotations = await annotation_storage.list(None, None, None, 10)
        created = next((a for a in annotations if a.id == minimal_annotation.id), None)
        assert created is not None
        assert created.author_name == "Test Author"
        assert created.target is None
        assert created.context is None
        assert created.text is None
        assert created.metric is None
        assert created.metadata is None


@pytest.fixture
async def inserted_annotations(
    annotation_storage: PsqlAnnotationStorage,
    test_experiment: Experiment,
    test_agent: Agent,
):
    annotations = [
        # run target, no context
        fake_annotation(
            id="1",
            target=Annotation.Target(completion_id=uuid7(ms=lambda: 0, rand=lambda: 1)),
            context=None,
        ),
        # run target, experiment context
        fake_annotation(
            id="2",
            target=Annotation.Target(completion_id=uuid7(ms=lambda: 0, rand=lambda: 1)),
            context=Annotation.Context(experiment_id=test_experiment.id, agent_id=test_agent.id),
        ),
        # experiment target
        fake_annotation(
            id="3",
            target=Annotation.Target(experiment_id=test_experiment.id),
            context=None,
        ),
        # Another run
        fake_annotation(
            id="4",
            target=Annotation.Target(completion_id=uuid7(ms=lambda: 0, rand=lambda: 2)),
            context=None,
        ),
    ]
    _ = await gather(*[annotation_storage.create(a) for a in annotations])
    return annotations


class TestList:
    async def test_no_filter(
        self,
        annotation_storage: PsqlAnnotationStorage,
        inserted_annotations: list[Annotation],
    ):
        retrieved = await annotation_storage.list(None, None, None, 10)

        # Should have at least our 3 annotations
        assert len(retrieved) == len(inserted_annotations)

    async def test_target_experiment(
        self,
        annotation_storage: PsqlAnnotationStorage,
        inserted_annotations: list[Annotation],
        test_experiment: Experiment,
    ):
        retrieved = await annotation_storage.list(TargetFilter(experiment_id={test_experiment.id}), None, None, 10)
        assert len(retrieved) == 1
        assert retrieved[0].id == "3"

    async def test_target_run_no_experiment(
        self,
        annotation_storage: PsqlAnnotationStorage,
        inserted_annotations: list[Annotation],
    ):
        retrieved = await annotation_storage.list(
            TargetFilter(completion_id={uuid7(ms=lambda: 0, rand=lambda: 1)}),
            ContextFilter(experiment_id=set()),
            None,
            10,
        )
        assert len(retrieved) == 1
        assert retrieved[0].id == "1"

    async def test_target_run_any_experiment(
        self,
        annotation_storage: PsqlAnnotationStorage,
        inserted_annotations: list[Annotation],
    ):
        retrieved = await annotation_storage.list(
            TargetFilter(completion_id={uuid7(ms=lambda: 0, rand=lambda: 1)}),
            None,
            None,
            10,
        )
        assert len(retrieved) == 2
        assert {a.id for a in retrieved} == {"1", "2"}

    async def test_target_run_and_experiment(
        self,
        annotation_storage: PsqlAnnotationStorage,
        inserted_annotations: list[Annotation],
        test_experiment: Experiment,
    ):
        retrieved = await annotation_storage.list(
            TargetFilter(completion_id={uuid7(ms=lambda: 0, rand=lambda: 1)}),
            ContextFilter(experiment_id={test_experiment.id}),
            None,
            10,
        )
        assert len(retrieved) == 1
        assert retrieved[0].id == "2"

    async def test_target_multiple_runs(
        self,
        annotation_storage: PsqlAnnotationStorage,
        inserted_annotations: list[Annotation],
    ):
        retrieved = await annotation_storage.list(
            TargetFilter(
                completion_id={
                    uuid7(ms=lambda: 0, rand=lambda: 1),
                    uuid7(ms=lambda: 0, rand=lambda: 2),
                },
            ),
            None,
            None,
            10,
        )
        assert len(retrieved) == 3
        assert {a.id for a in retrieved} == {"1", "2", "4"}

    async def test_context_agent_id_filter(
        self,
        annotation_storage: PsqlAnnotationStorage,
        inserted_annotations: list[Annotation],
        test_agent: Agent,
    ):
        retrieved = await annotation_storage.list(
            None,
            ContextFilter(agent_id={test_agent.id}),
            None,
            10,
        )
        assert len(retrieved) == 1
        assert retrieved[0].id == "2"

    async def test_target_experiment_and_run(
        self,
        annotation_storage: PsqlAnnotationStorage,
        inserted_annotations: list[Annotation],
        test_experiment: Experiment,
    ):
        retrieved = await annotation_storage.list(
            TargetFilter(
                experiment_id={test_experiment.id},
                completion_id={uuid7(ms=lambda: 0, rand=lambda: 1)},
            ),
            None,
            None,
            10,
        )
        assert len(retrieved) == 3

        retrieved = await annotation_storage.list(
            TargetFilter(experiment_id={test_experiment.id}),
            None,
            None,
            10,
        )
        assert len(retrieved) == 1, "sanity check"


class TestDelete:
    async def test_delete(
        self,
        annotation_storage: PsqlAnnotationStorage,
        inserted_annotations: list[Annotation],
    ):
        await annotation_storage.delete(inserted_annotations[0].id)
        retrieved = await annotation_storage.list(None, None, None, 10)
        assert len(retrieved) == len(inserted_annotations) - 1
        assert inserted_annotations[0].id not in {a.id for a in retrieved}

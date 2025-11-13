# pyright: reportPrivateUsage=false

from unittest.mock import Mock

import pytest

from core.domain.annotation import Annotation
from core.utils.uuid import uuid7
from protocol.api._services.annotation_service import AnnotationService
from tests.fake_models import fake_annotation


@pytest.fixture
def annotation_service(
    mock_annotation_storage: Mock,
    mock_experiment_storage: Mock,
    mock_completion_storage: Mock,
    mock_event_router: Mock,
):
    return AnnotationService(
        mock_annotation_storage,
        mock_experiment_storage,
        mock_completion_storage,
        mock_event_router,
    )


class TestSanitizeContext:
    async def test_with_completion_id(self, annotation_service: AnnotationService, mock_completion_storage: Mock):
        mock_completion_storage.raw_query.return_value = [
            {
                "id": uuid7(ms=lambda: 0, rand=lambda: 1),
                "agent_id": "test-agent-id",
                "experiment_id": "test-experiment-id",
            },
        ]
        annotation = fake_annotation(
            target=Annotation.Target(completion_id=uuid7(ms=lambda: 0, rand=lambda: 1)),
            context=None,
        )

        await annotation_service._sanitize_context([annotation])
        assert annotation.context is not None
        assert annotation.context.agent_id == "test-agent-id"
        assert annotation.context.experiment_id == "test-experiment-id"

        mock_completion_storage.raw_query.assert_awaited_once()

    async def test_with_experiment_id(self, annotation_service: AnnotationService, mock_experiment_storage: Mock):
        mock_experiment_storage.get_agents_ids.return_value = {
            "test-experiment-id": "test-agent-id",
        }
        annotation = fake_annotation(
            target=Annotation.Target(experiment_id="test-experiment-id"),
            context=None,
        )

        await annotation_service._sanitize_context([annotation])
        assert annotation.context is not None
        assert annotation.context.agent_id == "test-agent-id"

        mock_experiment_storage.get_agents_ids.assert_awaited_once_with(["test-experiment-id"])

    async def test_with_multiple_completion_ids(
        self,
        annotation_service: AnnotationService,
        mock_completion_storage: Mock,
    ):
        completion_id_1 = uuid7(ms=lambda: 0, rand=lambda: 1)
        completion_id_2 = uuid7(ms=lambda: 0, rand=lambda: 2)

        mock_completion_storage.raw_query.return_value = [
            {
                "id": completion_id_1,
                "agent_id": "agent-1",
                "experiment_id": "experiment-1",
            },
            {
                "id": completion_id_2,
                "agent_id": "agent-2",
                "experiment_id": "experiment-2",
            },
        ]

        annotation_1 = fake_annotation(
            id="annotation-1",
            target=Annotation.Target(completion_id=completion_id_1),
            context=None,
        )
        annotation_2 = fake_annotation(
            id="annotation-2",
            target=Annotation.Target(completion_id=completion_id_2),
            context=None,
        )

        await annotation_service._sanitize_context([annotation_1, annotation_2])

        assert annotation_1.context is not None
        assert annotation_1.context.agent_id == "agent-1"
        assert annotation_1.context.experiment_id == "experiment-1"

        assert annotation_2.context is not None
        assert annotation_2.context.agent_id == "agent-2"
        assert annotation_2.context.experiment_id == "experiment-2"

        mock_completion_storage.raw_query.assert_awaited_once()

    async def test_with_both_completion_and_experiment_id(
        self,
        annotation_service: AnnotationService,
        mock_completion_storage: Mock,
        mock_experiment_storage: Mock,
    ):
        completion_id = uuid7(ms=lambda: 0, rand=lambda: 1)

        mock_completion_storage.raw_query.return_value = [
            {
                "id": completion_id,
                "agent_id": "completion-agent-id",
                "experiment_id": "completion-experiment-id",
            },
        ]
        mock_experiment_storage.get_agents_ids.return_value = {
            "experiment-id": "experiment-agent-id",
        }

        annotation = fake_annotation(
            target=Annotation.Target(
                completion_id=completion_id,
                experiment_id="experiment-id",
            ),
            context=None,
        )

        await annotation_service._sanitize_context([annotation])

        assert annotation.context is not None
        # Experiment ID overrides completion ID for agent_id
        assert annotation.context.agent_id == "experiment-agent-id"
        # Completion provides experiment_id
        assert annotation.context.experiment_id == "completion-experiment-id"

    async def test_with_mixed_targets(
        self,
        annotation_service: AnnotationService,
        mock_completion_storage: Mock,
        mock_experiment_storage: Mock,
    ):
        completion_id = uuid7(ms=lambda: 0, rand=lambda: 1)

        mock_completion_storage.raw_query.return_value = [
            {
                "id": completion_id,
                "agent_id": "completion-agent",
                "experiment_id": "completion-experiment",
            },
        ]
        mock_experiment_storage.get_agents_ids.return_value = {
            "experiment-id": "experiment-agent",
        }

        annotation_1 = fake_annotation(
            id="annotation-1",
            target=Annotation.Target(completion_id=completion_id),
            context=None,
        )
        annotation_2 = fake_annotation(
            id="annotation-2",
            target=Annotation.Target(experiment_id="experiment-id"),
            context=None,
        )

        await annotation_service._sanitize_context([annotation_1, annotation_2])

        assert annotation_1.context is not None
        assert annotation_1.context.agent_id == "completion-agent"
        assert annotation_1.context.experiment_id == "completion-experiment"

        assert annotation_2.context is not None
        assert annotation_2.context.agent_id == "experiment-agent"

    async def test_with_existing_context(self, annotation_service: AnnotationService, mock_completion_storage: Mock):
        completion_id = uuid7(ms=lambda: 0, rand=lambda: 1)

        mock_completion_storage.raw_query.return_value = [
            {
                "id": completion_id,
                "agent_id": "new-agent-id",
                "experiment_id": "new-experiment-id",
            },
        ]

        annotation = fake_annotation(
            target=Annotation.Target(completion_id=completion_id),
            context=Annotation.Context(agent_id="old-agent-id", experiment_id="old-experiment-id"),
        )

        await annotation_service._sanitize_context([annotation])

        # Context should be overwritten with data from completion
        assert annotation.context is not None
        assert annotation.context.agent_id == "new-agent-id"
        assert annotation.context.experiment_id == "new-experiment-id"

    async def test_missing_target_raises_error(self, annotation_service: AnnotationService):
        from core.domain.exceptions import BadRequestError

        annotation = fake_annotation(target=None)

        with pytest.raises(BadRequestError, match="Annotation target is required"):
            await annotation_service._sanitize_context([annotation])

    async def test_completion_not_found_raises_error(
        self,
        annotation_service: AnnotationService,
        mock_completion_storage: Mock,
    ):
        from core.domain.exceptions import ObjectNotFoundError

        completion_id = uuid7(ms=lambda: 0, rand=lambda: 1)
        mock_completion_storage.raw_query.return_value = []

        annotation = fake_annotation(
            target=Annotation.Target(completion_id=completion_id),
            context=None,
        )

        with pytest.raises(ObjectNotFoundError, match="Completion not found"):
            await annotation_service._sanitize_context([annotation])

    async def test_empty_list(self, annotation_service: AnnotationService):
        # Should not raise any errors
        await annotation_service._sanitize_context([])

    async def test_target_with_only_key_path(self, annotation_service: AnnotationService):
        # Target with only key_path (no completion_id or experiment_id) is incomplete
        annotation = fake_annotation(
            target=Annotation.Target(key_path="response.message"),
            context=None,
        )

        # This should succeed since the target exists, but context won't have agent_id set
        await annotation_service._sanitize_context([annotation])

        # Context should be created but empty
        assert annotation.context is not None
        assert annotation.context.agent_id is None
        assert annotation.context.experiment_id is None

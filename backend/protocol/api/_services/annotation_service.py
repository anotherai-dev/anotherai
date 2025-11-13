from datetime import datetime
from typing import Any, final
from uuid import UUID

from core.consts import METADATA_KEY_EXPERIMENT_ID
from core.domain.annotation import Annotation as DomainAnnotation
from core.domain.events import AnnotationAddedEvent, AnnotationDeletedEvent, EventRouter
from core.domain.exceptions import BadRequestError, InternalError, ObjectNotFoundError
from core.storage.annotation_storage import AnnotationStorage
from core.storage.completion_storage import CompletionStorage
from core.storage.experiment_storage import ExperimentStorage
from protocol.api._api_models import Annotation, Page
from protocol.api._services.conversions import annotation_from_domain, annotation_to_domain
from protocol.api._services.ids_service import sanitized_completion_uuid


@final
class AnnotationService:
    def __init__(
        self,
        storage: AnnotationStorage,
        experiment_storage: ExperimentStorage,
        completion_storage: CompletionStorage,
        event_router: EventRouter,
    ):
        self.annotation_storage = storage
        self.experiment_storage = experiment_storage
        self.completion_storage = completion_storage
        self._event_router = event_router

    async def get_annotations(
        self,
        experiment_id: str | None = None,
        completion_id: str | None = None,
        agent_id: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> Page[Annotation]:
        since_datetime = None
        if since:
            since_datetime = datetime.fromisoformat(since.rstrip("Z"))

        sanitized_completion_id = sanitized_completion_uuid(completion_id) if completion_id else None

        domain_annotations = await self.annotation_storage.list(
            experiment_id=experiment_id,
            completion_id=sanitized_completion_id,
            agent_id=agent_id,
            since=since_datetime,
            limit=limit,
        )

        api_annotations = [annotation_from_domain(annotation) for annotation in domain_annotations]

        return Page(items=api_annotations, total=len(api_annotations))

    # Not sure how to break this function apart we would be returning tuples, etc.
    # We could also split by "target" which might be clearer but would require more intermediary variables
    # Let's leave as is for now
    async def _sanitize_context(self, annotations: list[DomainAnnotation]) -> None:  # noqa: C901
        completion_ids: list[UUID] = []
        experiment_ids: list[str] = []
        for annotation in annotations:
            if not annotation.target:
                raise BadRequestError("Annotation target is required")
            if annotation.target.completion_id:
                completion_ids.append(annotation.target.completion_id)
            if annotation.target.experiment_id:
                experiment_ids.append(annotation.target.experiment_id)

        by_cid: dict[UUID, dict[str, Any]] = {}
        if completion_ids:
            raw_result = await self.completion_storage.raw_query(
                f"SELECT id, agent_id, metadata['{METADATA_KEY_EXPERIMENT_ID}'] as experiment_id"
                f"FROM completions WHERE id IN ({', '.join(str(c) for c in completion_ids)})",
            )
            by_cid = {r["id"]: r for r in raw_result}

        agent_id_by_eid: dict[str, str] = {}
        if experiment_ids:
            agent_id_by_eid = await self.experiment_storage.get_agents_ids(experiment_ids)

        for annotation in annotations:
            if not annotation.target:
                # Should have been caught by the previous check
                raise InternalError("Annotation target is required")
            if not annotation.context:
                annotation.context = DomainAnnotation.Context()
            if annotation.target.completion_id:
                try:
                    val = by_cid[annotation.target.completion_id]
                except KeyError:
                    raise ObjectNotFoundError(
                        object_type="completion",
                        msg=f"Completion not found: {annotation.target.completion_id}",
                    ) from None
                annotation.context.agent_id = val["agent_id"]
                annotation.context.experiment_id = val["experiment_id"]
            if annotation.target.experiment_id:
                annotation.context.agent_id = agent_id_by_eid[annotation.target.experiment_id]

    async def add_annotations(self, annotations: list[Annotation]) -> None:
        if not annotations:
            return

        domain_annotations = [annotation_to_domain(annotation) for annotation in annotations]
        await self._sanitize_context(domain_annotations)
        await self.annotation_storage.create(domain_annotations)
        for annotation in domain_annotations:
            self._event_router(AnnotationAddedEvent(annotation_id=annotation.id))

    async def delete_annotation(self, annotation_id: str) -> None:
        await self.annotation_storage.delete(annotation_id)

        self._event_router(AnnotationDeletedEvent(annotation_id=annotation_id))

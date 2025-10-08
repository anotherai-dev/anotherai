from datetime import datetime
from typing import final

from core.domain.annotation import Annotation as DomainAnnotation
from core.storage.annotation_storage import AnnotationStorage
from core.storage.completion_storage import CompletionStorage
from core.storage.experiment_storage import ExperimentStorage
from core.utils.background import add_background_task
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
    ):
        self.annotation_storage = storage
        self.experiment_storage = experiment_storage
        self.completion_storage = completion_storage

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

    async def _assign_agent_id(self, annotation: DomainAnnotation) -> None:
        if not annotation.target:
            return

        if annotation.target.completion_id:
            run = await self.completion_storage.completions_by_id(
                annotation.target.completion_id,
                include={"agent_id"},
            )
            annotation.set_context_agent_id(run.agent.id)
            return

        if annotation.target.experiment_id:
            experiment = await self.experiment_storage.get_experiment(
                annotation.target.experiment_id,
                include={"agent_id"},
            )
            annotation.set_context_agent_id(experiment.agent_id)
            return

    async def _insert_annotation(self, annotation: DomainAnnotation) -> None:
        if not annotation.context or not annotation.context.agent_id:
            await self._assign_agent_id(annotation)
        await self.annotation_storage.create(annotation)

        # TODO: insert all annotations at once
        if annotation.target:
            # TODO: use actual event
            add_background_task(self.completion_storage.store_annotation(annotation))

    async def add_annotations(self, annotations: list[Annotation]) -> None:
        if not annotations:
            return

        # TODO: automatically add context if annotation targets a completion ?

        domain_annotations = [annotation_to_domain(annotation) for annotation in annotations]
        # Create one annotation at a time, n+1 is ok because we rarely add more than 1 annotation at
        # a time
        # TODO: add better information about which one fails
        for annotation in domain_annotations:
            await self._insert_annotation(annotation)

    async def delete_annotation(self, annotation_id: str) -> None:
        await self.annotation_storage.delete(annotation_id)
        # TODO: update clickhouse

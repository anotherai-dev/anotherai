from datetime import datetime
from typing import NamedTuple, Protocol
from uuid import UUID

from core.domain.annotation import Annotation


class TargetFilter(NamedTuple):
    experiment_id: set[str] | None = None
    completion_id: set[UUID] | None = None


class ContextFilter(NamedTuple):
    experiment_id: set[str] | None = None
    agent_id: set[str] | None = None


class AnnotationStorage(Protocol):
    async def create(self, annotation: Annotation) -> None:
        pass

    async def list(
        self,
        target: TargetFilter | None,
        context: ContextFilter | None,
        since: datetime | None,
        limit: int,
    ) -> list[Annotation]: ...

    async def delete(self, annotation_id: str) -> None: ...

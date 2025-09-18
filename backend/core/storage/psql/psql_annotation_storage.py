from datetime import datetime
from typing import Any, override

import structlog
from asyncpg.pool import PoolConnectionProxy

from core.domain.annotation import Annotation
from core.domain.exceptions import ObjectNotFoundError
from core.storage.annotation_storage import AnnotationStorage, ContextFilter, TargetFilter
from core.storage.psql._psql_base_storage import JSONDict, PsqlBaseRow, PsqlBaseStorage, WithUpdatedAtRow
from core.utils.fields import datetime_zero
from core.utils.uuid import uuid7

_log = structlog.get_logger(__name__)


class PsqlAnnotationStorage(PsqlBaseStorage, AnnotationStorage):
    @override
    @classmethod
    def table(cls) -> str:
        return "annotations"

    async def _resolve_experiment_uid(
        self,
        connection: PoolConnectionProxy,
        val: Annotation.Target | Annotation.Context | None,
    ) -> int | None:
        if val and val.experiment_id:
            map = await self._experiment_uids(connection, {val.experiment_id})
            _id = map.get(val.experiment_id)
            if _id is None:
                raise ObjectNotFoundError(object_type="experiment")
            return _id
        return None

    async def _resolve_agent_uid(
        self,
        connection: PoolConnectionProxy,
        val: Annotation.Context | None,
    ) -> int | None:
        if val and val.agent_id:
            return await self._agent_uid(connection, val.agent_id)
        return None

    @override
    async def create(self, annotation: Annotation) -> None:
        if not annotation.id:
            annotation.id = str(uuid7())
        # TODO: replace on conflict
        async with self._connect() as connection:
            agent_uid = await self._resolve_agent_uid(connection, annotation.context)
            target_experiment_uid = await self._resolve_experiment_uid(connection, annotation.target)
            context_experiment_uid = await self._resolve_experiment_uid(connection, annotation.context)

            row = _AnnotationRow.from_domain(
                annotation,
                target_experiment_uid=target_experiment_uid,
                context_experiment_uid=context_experiment_uid,
                context_agent_uid=agent_uid,
            )

            _ = await self._insert(connection, row)

    async def _where_annotations(  # noqa: C901
        self,
        connection: PoolConnectionProxy,
        target: TargetFilter | None,
        context: ContextFilter | None,
        since: datetime | None,
    ) -> tuple[list[str], list[Any]]:
        where: list[str] = ["deleted_at IS NULL"]
        arguments: list[Any] = []

        if since is not None:
            where.append(f"created_at > ${len(arguments) + 1}")
            arguments.append(since)

        experiment_ids = set[str]()
        if target and target.experiment_id:
            experiment_ids.update(target.experiment_id)
        if context and context.experiment_id:
            experiment_ids.update(context.experiment_id)

        experiment_uid_map = await self._experiment_uids(connection, experiment_ids)

        if target:
            target_filter: list[str] = []
            if target.experiment_id:
                target_experiment_uids = [experiment_uid_map.get(e) for e in target.experiment_id]
                target_filter.append(f"target_experiment_uid = ANY(${len(arguments) + 1})")
                arguments.append(target_experiment_uids)
            if target.completion_id:
                target_filter.append(f"target_completion_id = ANY(${len(arguments) + 1})")
                arguments.append(target.completion_id)
            if len(target_filter) == 1:
                where.append(target_filter[0])
            elif target_filter:
                where.append("(" + " OR ".join(target_filter) + ")")
        if context:
            if context.experiment_id is not None:
                if context.experiment_id:
                    context_experiment_uids = [experiment_uid_map.get(e) for e in context.experiment_id]
                    where.append(f"context_experiment_uid = ANY(${len(arguments) + 1})")
                    arguments.append(context_experiment_uids)
                else:
                    where.append("context_experiment_uid IS NULL")
            if context.agent_id:
                agent_uids = await self._agent_uids(connection, context.agent_id)
                where.append(f"context_agent_uid = ANY(${len(arguments) + 1})")
                arguments.append(set(agent_uids.values()))

        return where, arguments

    @override
    async def list(
        self,
        target: TargetFilter | None,
        context: ContextFilter | None,
        since: datetime | None,
        limit: int,
    ) -> list[Annotation]:
        # Convert experiment IDs to UIDs for filtering
        async with self._connect() as connection:
            where, arguments = await self._where_annotations(connection, target, context, since)
            query = f"""
            SELECT *
            FROM annotations
            WHERE {" AND ".join(where)}
            ORDER BY created_at DESC
            LIMIT ${len(arguments) + 1}
            """  # noqa: S608 # OK here since where is defined above

            rows = await connection.fetch(
                query,
                *arguments,
                limit,
            )

            validated_rows: list[_AnnotationRow] = []
            experiment_uids: set[int] = set()
            agent_uids: set[int] = set()
            for row in rows:
                annotation_row = self._validate(_AnnotationRow, row)
                validated_rows.append(annotation_row)
                if annotation_row.target_experiment_uid:
                    experiment_uids.add(annotation_row.target_experiment_uid)
                if annotation_row.context_agent_uid:
                    agent_uids.add(annotation_row.context_agent_uid)
                if annotation_row.context_experiment_uid:
                    experiment_uids.add(annotation_row.context_experiment_uid)

            experiment_ids = await self._experiment_ids(connection, experiment_uids)
            agent_ids = await self._agent_ids(connection, agent_uids)

            annotations = [
                annotation_row.to_domain(self, experiment_ids=experiment_ids, agent_ids=agent_ids)
                for annotation_row in validated_rows
            ]

            return annotations

    @override
    async def delete(self, annotation_id: str) -> None:
        async with self._connect() as connection:
            _ = await connection.execute(
                """
                UPDATE annotations
                SET deleted_at = CURRENT_TIMESTAMP
                WHERE slug = $2
                """,
                annotation_id,
            )


class _AnnotationRow(PsqlBaseRow, WithUpdatedAtRow):
    """A representation of an annotation row"""

    slug: str = ""

    author_name: str = ""
    target_completion_id: str | None = None
    target_experiment_uid: int | None = None
    target_key_path: str | None = None
    context_experiment_uid: int | None = None
    context_agent_uid: int | None = None
    text: str | None = None
    metric_name: str | None = None
    metric_value_float: float | None = None
    metric_value_str: str | None = None
    metric_value_bool: bool | None = None
    metadata: JSONDict | None = None

    @classmethod
    def from_domain(
        cls,
        ann: Annotation,
        target_experiment_uid: int | None,
        context_experiment_uid: int | None,
        context_agent_uid: int | None,
    ):
        return cls(
            slug=ann.id,
            author_name=ann.author_name,
            target_completion_id=ann.target.completion_id if ann.target else None,
            target_experiment_uid=target_experiment_uid,
            target_key_path=ann.target.key_path if ann.target else None,
            context_experiment_uid=context_experiment_uid,
            context_agent_uid=context_agent_uid,
            text=ann.text,
            metric_name=ann.metric.name if ann.metric else None,
            metric_value_float=ann.metric.value if ann.metric and isinstance(ann.metric.value, float) else None,
            metric_value_str=ann.metric.value if ann.metric and isinstance(ann.metric.value, str) else None,
            metric_value_bool=ann.metric.value if ann.metric and isinstance(ann.metric.value, bool) else None,
            metadata=ann.metadata or {},
            created_at=ann.created_at,
            updated_at=ann.updated_at,
        )

    def domain_metric(self) -> Annotation.Metric | None:
        if self.metric_name is None:
            return None
        if self.metric_value_float is not None:
            return Annotation.Metric(name=self.metric_name, value=self.metric_value_float)
        if self.metric_value_str is not None:
            return Annotation.Metric(name=self.metric_name, value=self.metric_value_str)
        if self.metric_value_bool is not None:
            return Annotation.Metric(name=self.metric_name, value=self.metric_value_bool)
        _log.warning("Unknown metric value type", metric_name=self.metric_name, metric_value=self.metric_value_str)
        return None

    def domain_target(self, experiment_ids: dict[int, str]) -> Annotation.Target | None:
        if self.target_experiment_uid is None and self.target_completion_id is None:
            return None
        target = Annotation.Target(
            experiment_id=experiment_ids.get(self.target_experiment_uid, "") if self.target_experiment_uid else None,
            completion_id=self.target_completion_id,
            key_path=self.target_key_path,
        )
        if not target.model_dump(exclude_none=True):
            return None
        return target

    def domain_context(self, experiment_ids: dict[int, str], agent_ids: dict[int, str]) -> Annotation.Context | None:
        if self.context_agent_uid is None and self.context_experiment_uid is None:
            return None
        context = Annotation.Context(
            agent_id=agent_ids.get(self.context_agent_uid, "") if self.context_agent_uid else None,
            experiment_id=experiment_ids.get(self.context_experiment_uid, "") if self.context_experiment_uid else None,
        )
        if not context.model_dump(exclude_none=True):
            return None
        return context

    def to_domain(
        self,
        storage: PsqlAnnotationStorage,
        experiment_ids: dict[int, str],
        agent_ids: dict[int, str],
    ) -> Annotation:
        return Annotation(
            id=self.slug,
            created_at=self.created_at or datetime_zero(),
            updated_at=self.updated_at or datetime_zero(),
            author_name=self.author_name,
            target=self.domain_target(experiment_ids),
            context=self.domain_context(experiment_ids, agent_ids),
            text=self.text,
            metric=self.domain_metric(),
            metadata=self.metadata or None,
        )

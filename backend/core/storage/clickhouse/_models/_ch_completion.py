import json
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

import structlog
from pydantic import BaseModel, Field, TypeAdapter, field_serializer, field_validator

from core.domain.agent import Agent
from core.domain.agent_completion import AgentCompletion
from core.domain.agent_input import AgentInput
from core.domain.agent_output import AgentOutput
from core.domain.inference_usage import InferenceUsage
from core.domain.message import Message
from core.domain.trace import LLMTrace, ToolTrace, Trace
from core.domain.version import Version
from core.storage.clickhouse._models._ch_field_utils import (
    MAX_UINT_16,
    MAX_UINT_32,
    validate_fixed,
    validate_int,
)
from core.utils.fields import datetime_zero, uuid_zero
from core.utils.iter_utils import safe_map
from core.utils.uuid import uuid7_generation_time

log = structlog.get_logger(__name__)

DEFAULT_EXCLUDE = {"input_variables", "input_messages", "output_messages", "messages", "traces"}


class _Trace(BaseModel):
    kind: str = ""
    model: str = ""
    provider: str = ""
    usage: str = ""
    name: str = ""
    tool_input_preview: str = ""
    tool_output_preview: str = ""
    duration_ds: int = 0
    cost_millionth_usd: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0

    @classmethod
    def from_domain(cls, trace: Trace):
        base = cls(
            kind=trace.kind,
            duration_ds=_duration_ds(trace.duration_seconds),
            cost_millionth_usd=_cost_millionth_usd(trace.cost_usd),
        )
        if isinstance(trace, LLMTrace):
            base.model = trace.model
            base.provider = trace.provider
            base.usage = _stringify_json(trace.usage)
            if trace.usage:
                base.prompt_tokens = int(trace.usage.prompt.text_token_count or 0)
                base.completion_tokens = int(trace.usage.completion.text_token_count or 0)
                base.reasoning_tokens = int(trace.usage.completion.reasoning_token_count or 0)
                base.cached_tokens = int(trace.usage.completion.cached_token_count or 0)
        elif isinstance(trace, ToolTrace):  # pyright: ignore [reportUnnecessaryIsInstance]
            base.name = trace.name
            base.tool_input_preview = trace.tool_input_preview
            base.tool_output_preview = trace.tool_output_preview
        return base

    def to_domain(self) -> Trace:
        duration_seconds = _from_duration_ds(self.duration_ds)
        cost_usd = _from_cost_millionth_usd(self.cost_millionth_usd)
        if self.kind == "llm":
            return LLMTrace(
                kind="llm",
                duration_seconds=duration_seconds,
                cost_usd=cost_usd,
                model=self.model,
                provider=self.provider,
                usage=InferenceUsage.model_validate_json(self.usage) if self.usage else None,
            )
        if self.kind == "tool":
            return ToolTrace(
                kind="tool",
                duration_seconds=duration_seconds,
                cost_usd=cost_usd,
                name=self.name,
                tool_input_preview=self.tool_input_preview,
                tool_output_preview=self.tool_output_preview,
            )
        raise ValueError(f"Unknown trace kind: {self.kind}")


# TODO: we should use a duplicated type to avoid side effects
_Messages = TypeAdapter(list[Message])


class ClickhouseCompletion(BaseModel):
    # Core identifiers
    tenant_uid: Annotated[int, validate_int(MAX_UINT_32)] = 0
    agent_id: str = ""
    id: UUID = Field(default_factory=uuid_zero)
    updated_at: datetime = Field(default_factory=datetime_zero)

    # Version information
    version_id: Annotated[str, validate_fixed()] = ""
    version_model: str = ""
    version: str = ""

    # Hashes
    input_id: Annotated[str, validate_fixed()] = ""
    input_preview: str = ""
    input_messages: str = ""
    input_variables: str = ""

    output_id: Annotated[str, validate_fixed()] = ""
    output_preview: str = ""
    output_messages: str = ""
    output_error: str = ""

    messages: str = ""

    # Metrics
    duration_ds: Annotated[int, validate_int(MAX_UINT_16, "duration_ds")] = 0
    cost_millionth_usd: Annotated[int, validate_int(MAX_UINT_32, "cost_millionth_usd")] = 0

    # Metadata
    metadata: dict[str, str] = Field(default_factory=dict)

    # Origin of the run
    source: Literal["web", "api", "mcp"] = "api"

    # Whether the completion was streamed
    stream: bool = False

    # Traces as array of strings
    traces: list[_Trace] = Field(default_factory=list)

    @field_serializer("traces")
    def serialize_traces(self, traces: list[_Trace]) -> list[dict[str, Any]]:
        return [trace.model_dump(exclude_none=True) for trace in traces]

    # TODO: fix validation of nested fields
    # Clickhouse splats the fields instead
    @classmethod
    @field_validator("traces")
    def validate_traces(cls, traces: list[dict[str, Any]]) -> list[_Trace]:
        return safe_map(traces, _Trace.model_validate, log)

    # annotations: list[_Annotation] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, tenant: int, completion: AgentCompletion):
        return cls(
            # Core identifiers
            tenant_uid=tenant,
            agent_id=completion.agent.id,
            id=completion.id,
            updated_at=uuid7_generation_time(completion.id),
            # Version
            version_id=completion.version.id,
            version_model=completion.version.model or "",
            # TODO: use a separate model for validation ?
            version=_stringify_json(completion.version),
            # Hashes
            input_id=completion.agent_input.id,
            input_preview=completion.agent_input.preview,
            input_messages=_dump_messages(completion.agent_input.messages),
            input_variables=_stringify_json(completion.agent_input.variables),
            output_id=completion.agent_output.id,
            output_preview=completion.agent_output.preview,
            output_messages=_dump_messages(completion.agent_output.messages),
            output_error=_stringify_json(completion.agent_output.error),
            messages=_dump_messages(completion.messages),
            # IO
            # Metrics
            duration_ds=_duration_ds(completion.duration_seconds),
            cost_millionth_usd=_cost_millionth_usd(completion.cost_usd),
            metadata=_sanitize_metadata(completion.metadata),
            source=completion.source,
            stream=completion.stream,
            # Traces
            traces=[_Trace.from_domain(trace) for trace in completion.traces],
        )

    def _domain_version(self) -> Version:
        payload: dict[str, Any] = _from_stringified_json(self.version) or {}
        if self.version_id:
            payload["id"] = self.version_id
        if self.version_model:
            payload["model"] = self.version_model
        return Version.model_validate(payload)

    def to_domain(self, agent: Agent | None = None) -> AgentCompletion:
        agent = agent or Agent(id=self.agent_id, uid=0)

        return AgentCompletion(
            id=self.id,
            agent=agent,
            agent_input=_input_to_domain(self.input_variables, self.input_messages, self.input_preview, self.input_id),
            agent_output=_output_to_domain(
                self.output_messages,
                self.output_error,
                self.output_preview,
                self.output_id,
            ),
            messages=parse_messages(self.messages) or [],
            version=self._domain_version(),
            status="success" if not self.output_error else "failure",
            duration_seconds=_from_duration_ds(self.duration_ds),
            cost_usd=_from_cost_millionth_usd(self.cost_millionth_usd),
            traces=[_Trace.to_domain(trace) for trace in self.traces],
            metadata=from_sanitized_metadata(self.metadata),
            source=self.source,
            stream=self.stream,
            from_cache=False,
        )

    @classmethod
    def select(cls, exclude: set[str] | None = None) -> list[str]:
        if not exclude:
            return list(cls.model_fields.keys())
        return [f for f in cls.model_fields if f not in exclude]


# Nested annotations structure
# class _Annotation(BaseModel):
#     id: str = ""
#     experiment_id: str = ""
#     key_path: str = ""
#     text: str = ""
#     metric_name: str = ""
#     metric_value: Any = None
#     metadata: dict[str, str] = Field(default_factory=dict)
#     user_id: str = ""
#     updated_at: datetime = Field(default_factory=datetime_zero)
#     created_at: datetime = Field(default_factory=datetime_zero)

#     @classmethod
#     def from_domain(cls, annotation: Annotat):
#         # Convert domain annotation to ClickHouse format
#         metric_name = ""
#         metric_value = None
#         if hasattr(annotation, "metric") and annotation.metric:
#             metric_name = annotation.metric.name
#             metric_value = annotation.metric.value

#         return cls(
#             id=annotation.id,
#             experiment_id=getattr(annotation, "experiment_id", "") or "",
#             key_path=getattr(annotation, "key_path", "") or "",
#             text=getattr(annotation, "text", "") or "",
#             metric_name=metric_name,
#             metric_value=metric_value,
#             metadata=_sanitize_metadata(getattr(annotation, "metadata", None)) or {},
#             user_id=getattr(annotation, "author_name", "") or "",
#             updated_at=getattr(annotation, "updated_at", datetime_zero()) or datetime_zero(),
#             created_at=getattr(annotation, "created_at", datetime_zero()) or datetime_zero(),
#         )

#     @classmethod
#     def sanitize_id(cls, annotation_id: str, created_at: datetime) -> UUID:
#         try:
#             uuid = UUID(annotation_id)
#         except ValueError:
#             _logger.warning(
#                 "Found a non uuid annotation id generating a new one",
#                 extra={"annotation_id": annotation_id},
#             )
#             return uuid7(ms=lambda: int(created_at.timestamp() * 1000))

#         if is_uuid7(uuid):
#             return uuid
#         return uuid7(ms=lambda: int(created_at.timestamp() * 1000), rand=lambda: uuid.int)


def _duration_ds(duration: float | None) -> int:
    return round(duration * 10) if duration else 0


def _cost_millionth_usd(cost: float | None) -> int:
    return round(cost * 1_000_000) if cost else 0


def _from_cost_millionth_usd(cost: int) -> float:
    return cost / 1_000_000


def _from_duration_ds(duration: int) -> float:
    return duration / 10


def _stringify_json(data: Any) -> str:
    if isinstance(data, BaseModel):
        data = data.model_dump(exclude_none=True)
    # Remove spaces from the JSON string to allow using simplified json queries
    # see https://clickhouse.com/docs/en/sql-reference/functions/json-functions#simplejsonextractstring
    if not data:
        return ""
    return json.dumps(data, separators=(",", ":"))


def _from_stringified_json(data: str) -> Any:
    if not data:
        return None
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return data


def _sanitize_metadata_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _from_sanitized_metadata_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _sanitize_metadata(metadata: dict[str, Any] | None):
    return {k: _sanitize_metadata_value(v) for k, v in metadata.items()} if metadata else {}


def from_sanitized_metadata(metadata: dict[str, str] | None):
    if not metadata:
        return None
    return {k: _from_sanitized_metadata_value(v) for k, v in metadata.items()}


def _dump_messages(messages: list[Message] | None) -> str:
    if not messages:
        return ""
    return _Messages.dump_json(messages, exclude_none=True).decode()


def parse_messages(messages: str) -> list[Message] | None:
    if not messages:
        return None
    return _Messages.validate_json(messages)


def _input_to_domain(input_variables: str, input_messages: str, preview: str, id: str) -> AgentInput:
    payload: dict[str, Any] = {
        "id": id,
        "preview": preview,
    }
    payload["variables"] = _from_stringified_json(input_variables)
    payload["messages"] = parse_messages(input_messages)
    return AgentInput.model_validate(payload)


def _output_to_domain(output_messages: str, output_error: str, preview: str, id: str) -> AgentOutput:
    payload: dict[str, Any] = {
        "id": id,
        "preview": preview,
    }
    payload["messages"] = parse_messages(output_messages)
    payload["error"] = _from_stringified_json(output_error)
    return AgentOutput.model_validate(payload)

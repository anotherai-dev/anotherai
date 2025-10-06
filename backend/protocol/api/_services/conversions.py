from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import TypeAdapter
from pydantic_core import ValidationError
from structlog import get_logger

from core.consts import ANOTHERAI_API_URL
from core.domain.agent import Agent as DomainAgent
from core.domain.agent_completion import AgentCompletion as DomainCompletion
from core.domain.agent_input import AgentInput as DomainInput
from core.domain.agent_output import AgentOutput as DomainOutput
from core.domain.annotation import Annotation as DomainAnnotation
from core.domain.api_key import APIKey as DomainAPIKey
from core.domain.api_key import CompleteAPIKey as DomainCompleteAPIKey
from core.domain.deployment import Deployment as DomainDeployment
from core.domain.error import Error as DomainError
from core.domain.exceptions import BadRequestError, JSONSchemaValidationError
from core.domain.experiment import Experiment as DomainExperiment
from core.domain.experiment import ExperimentInput as DomainExperimentInput
from core.domain.experiment import ExperimentOutput
from core.domain.experiment import ExperimentVersion as DomainExperimentVersion
from core.domain.file import File
from core.domain.inference_usage import CompletionUsage as DomainCompletionUsage
from core.domain.inference_usage import InferenceUsage as DomainInferenceUsage
from core.domain.inference_usage import TokenUsage as DomainTokenUsage
from core.domain.message import Message as DomainMessage
from core.domain.message import MessageContent as DomainMessageContent
from core.domain.message import MessageRole as DomainMessageRole
from core.domain.models.model_data import FinalModelData, MaxTokensData
from core.domain.models.model_data import ModelReasoningBudget as DomainModelReasoningBudget
from core.domain.models.model_data_supports import ModelDataSupports
from core.domain.models.model_provider_data import ModelProviderData
from core.domain.tenant_data import TenantData
from core.domain.tool import HostedTool as DomainHostedTool
from core.domain.tool import Tool as DomainTool
from core.domain.tool_call import ToolCallRequest as DomainToolCallRequest
from core.domain.tool_call import ToolCallResult as DomainToolCallResult
from core.domain.trace import LLMTrace as DomainLLMTrace
from core.domain.trace import ToolTrace as DomainToolTrace
from core.domain.trace import Trace as DomainTrace
from core.domain.version import Version as DomainVersion
from core.domain.view import Graph as DomainGraph
from core.domain.view import View as DomainView
from core.domain.view import ViewFolder as DomainViewFolder
from core.services.messages.messages_utils import json_schema_for_template
from core.utils.schema_sanitation import validate_schema
from core.utils.uuid import uuid7
from protocol.api._api_models import (
    URL,
    Agent,
    Annotation,
    APIKey,
    CompleteAPIKey,
    Completion,
    CompletionUsage,
    CreateAgentRequest,
    CreateExperimentRequest,
    CreateViewResponse,
    Deployment,
    Error,
    Experiment,
    ExperimentInput,
    ExperimentVersion,
    Graph,
    IDAndAlias,
    InferenceUsage,
    Input,
    Message,
    Model,
    ModelContextWindow,
    ModelField,
    ModelPricing,
    ModelReasoning,
    ModelSupports,
    Output,
    OutputSchema,
    SupportsModality,
    Tenant,
    TokenUsage,
    Tool,
    ToolCallRequest,
    ToolCallResult,
    Trace,
    Version,
    VersionRequest,
    View,
    ViewFolder,
)
from protocol.api._run_models import OpenAIProxyResponseFormat
from protocol.api._services._urls import deployment_url, experiments_url, view_url
from protocol.api._services.ids_service import IDType, sanitize_id

_log = get_logger(__name__)


def _sanitize_datetime(dt: datetime):
    """Sanitize a datetime to remove microseconds and timezone information.
    For now, having microseconds or not having a timezone breaks the MCP."""
    return dt.replace(microsecond=0, tzinfo=UTC)


def tool_from_domain(tool: DomainTool | DomainHostedTool) -> Tool:
    if isinstance(tool, DomainHostedTool):
        return Tool(
            name=tool.name,
            description=None,
            input_schema={},
        )
    return Tool(
        name=tool.name,
        description=tool.description,
        input_schema=tool.input_schema,
    )


def tool_to_domain(tool: Tool) -> DomainTool | DomainHostedTool:
    if tool.name.startswith("@") and tool.name in DomainHostedTool:
        return DomainHostedTool(tool.name)
    return DomainTool(
        name=tool.name,
        description=tool.description,
        input_schema=tool.input_schema,
        output_schema=None,
    )


def tool_call_request_from_domain(tool_call_request: DomainToolCallRequest) -> ToolCallRequest:
    return ToolCallRequest(
        id=tool_call_request.id,
        name=tool_call_request.tool_name,
        arguments=tool_call_request.tool_input_dict,
    )


def tool_call_request_to_domain(tool_call_request: ToolCallRequest) -> DomainToolCallRequest:
    return DomainToolCallRequest(
        id=tool_call_request.id,
        tool_name=tool_call_request.name,
        tool_input_dict=tool_call_request.arguments,
    )


def tool_call_result_from_domain(tool_call_result: DomainToolCallResult) -> ToolCallResult:
    return ToolCallResult(
        id=tool_call_result.id,
        output=tool_call_result.result,
        error=tool_call_result.error,
    )


def tool_call_result_to_domain(tool_call_result: ToolCallResult) -> DomainToolCallResult:
    return DomainToolCallResult(
        id=tool_call_result.id,
        tool_name="",
        tool_input_dict={},
        result=tool_call_result.output,
        error=tool_call_result.error,
    )


def message_role_to_domain(
    message_role: Literal["system", "user", "assistant", "developer", "tool"],
) -> DomainMessageRole:
    match message_role:
        case "system" | "developer":
            return "system"
        case "user" | "tool":
            return "user"
        case "assistant":
            return "assistant"


def _extract_url(url: str | URL) -> str:
    if isinstance(url, URL):
        return url.url
    return url


def message_content_to_domain(message_content: Message.Content) -> DomainMessageContent:
    if len(message_content.model_fields_set) > 1:
        raise BadRequestError("Contents can only contain one field at a time")
    if message_content.image_url:
        return DomainMessageContent(file=File(url=_extract_url(message_content.image_url), format="image"))
    if message_content.audio_url:
        return DomainMessageContent(file=File(url=_extract_url(message_content.audio_url), format="audio"))
    if message_content.tool_call_request:
        return DomainMessageContent(
            tool_call_request=tool_call_request_to_domain(message_content.tool_call_request),
        )
    if message_content.tool_call_result:
        return DomainMessageContent(
            tool_call_result=tool_call_result_to_domain(message_content.tool_call_result),
        )
    if message_content.object:
        return DomainMessageContent(object=message_content.object)
    return DomainMessageContent(
        text=message_content.text,
        reasoning=message_content.reasoning,
    )


def message_content_from_domain(content: DomainMessageContent) -> Message.Content:
    if content.file:
        return Message.Content(image_url=content.file.url)
    if content.tool_call_request:
        return Message.Content(tool_call_request=tool_call_request_from_domain(content.tool_call_request))
    if content.tool_call_result:
        return Message.Content(tool_call_result=tool_call_result_from_domain(content.tool_call_result))
    if content.object:
        return Message.Content(object=content.object)
    return Message.Content(text=content.text, reasoning=content.reasoning)


def _message_content_to_domain(message: Message) -> list[DomainMessageContent]:
    if isinstance(message.content, str):
        return [DomainMessageContent(text=message.content)]
    if isinstance(message.content, dict):
        return [DomainMessageContent(object=message.content)]

    return [message_content_to_domain(c) for c in message.content]


def message_to_domain(message: Message) -> DomainMessage:
    return DomainMessage(
        role=message_role_to_domain(message.role),
        content=_message_content_to_domain(message),
    )


def _inlined_message_content(message: DomainMessageContent):
    if message.text:
        return message.text
    if message.object and isinstance(message.object, dict):
        # We only inline dict objects to avoid conflicts with the list[Content]
        return message.object
    return None


def message_from_domain(message: DomainMessage) -> Message:
    if len(message.content) == 1 and (inlined := _inlined_message_content(message.content[0])):
        return Message(
            role=message.role,
            content=inlined,
        )
    return Message(
        role=message.role,
        content=[message_content_from_domain(c) for c in message.content],
    )


def output_schema_to_domain(output_schema: OutputSchema) -> DomainVersion.OutputSchema:
    return DomainVersion.OutputSchema(json_schema=output_schema.json_schema)


def output_schema_from_domain(output_schema: DomainVersion.OutputSchema) -> OutputSchema:
    return OutputSchema(id=output_schema.id, json_schema=output_schema.json_schema)


def version_to_domain(version: Version) -> DomainVersion:
    return DomainVersion(
        model=version.model,
        temperature=version.temperature,
        top_p=version.top_p,
        enabled_tools=[tool_to_domain(t) for t in version.tools] if version.tools else None,
        prompt=[message_to_domain(m) for m in version.prompt] if version.prompt else None,
        output_schema=output_schema_to_domain(version.output_schema) if version.output_schema else None,
        input_variables_schema=version.input_variables_schema,
        max_output_tokens=version.max_output_tokens,
        tool_choice=version.tool_choice,
        parallel_tool_calls=version.parallel_tool_calls,
        reasoning_effort=version.reasoning_effort,
        reasoning_budget=version.reasoning_budget,
        presence_penalty=version.presence_penalty,
        frequency_penalty=version.frequency_penalty,
        use_structured_generation=version.use_structured_generation,
        provider=version.provider,
    )


def version_from_domain[T: Version](version: DomainVersion, t: type[T] = Version, **kwargs: Any) -> T:
    return t(
        id=version.id,
        model=version.model or "",
        temperature=version.temperature,
        top_p=version.top_p,
        tools=[tool_from_domain(t) for t in version.enabled_tools] if version.enabled_tools else None,
        prompt=[message_from_domain(m) for m in version.prompt] if version.prompt else None,
        output_schema=output_schema_from_domain(version.output_schema) if version.output_schema else None,
        input_variables_schema=version.input_variables_schema,
        max_output_tokens=version.max_output_tokens,
        tool_choice=version.tool_choice,
        parallel_tool_calls=version.parallel_tool_calls,
        reasoning_effort=version.reasoning_effort,
        reasoning_budget=version.reasoning_budget,
        presence_penalty=version.presence_penalty,
        frequency_penalty=version.frequency_penalty,
        use_structured_generation=version.use_structured_generation,
        provider=version.provider,
        **kwargs,
    )


def experiment_version_from_domain(version: DomainExperimentVersion) -> ExperimentVersion:
    return version_from_domain(version, ExperimentVersion, alias=version.alias)


def _sanitize_json_schema(json_schema: dict[str, Any]) -> DomainVersion.OutputSchema:
    # We have a straight JSON Schema
    try:
        validate_schema(json_schema)
    except JSONSchemaValidationError as e:
        raise BadRequestError(
            f"Invalid output json schema: {e}. Please provide a valid JSON schema or an OpenAI response format",
        ) from e
    return DomainVersion.OutputSchema(json_schema=json_schema)


def _extract_json_schema(output_json_schema: dict[str, Any]) -> dict[str, Any] | None:  # noqa: C901
    if not output_json_schema:
        return None
    _type = output_json_schema.get("type")
    match _type:
        case None:
            # Weird case, maybe the model decided to send us back an OutputSchema it found in a version
            # Let's validate the model
            possible_keys = ["json_schema", "schema"]
            for key in possible_keys:
                if schema := output_json_schema.get(key):
                    # We are re-performing an extract here
                    # We have seen models return a `json_schema` type object from OAI
                    # But not sending the `json_schema` type
                    return _extract_json_schema(schema)
            # Fallthrough to BadRequestError below
        case "array":
            raise BadRequestError("Array as root types are not supported. Please wrap in the array within an object")
        case "string" | "integer" | "number" | "boolean":
            raise BadRequestError(
                "String, integer, number, and boolean as root types are not supported. Please wrap in the string, integer, number, or boolean within an object",
            )
        case "object":
            return output_json_schema
        # Assuming we are getting a response format
        # https://platform.openai.com/docs/api-reference/chat/create#chat-create-response_format
        case "json_object":
            return {}
        case "text":
            return None
        case "json_schema":
            try:
                validated = OpenAIProxyResponseFormat.model_validate(output_json_schema)
            except ValidationError as e:
                raise BadRequestError(f"Invalid JSON Schema response format: {e}") from e
            if not validated.json_schema:
                raise BadRequestError("JSON Schema response format must have a json_schema")
            return validated.json_schema.schema_
        case _:
            pass  # Fallthrough to BadRequestError below

    raise BadRequestError("Invalid output json schema. Please provide a valid JSON schema or an OpenAI response format")


def _sanitize_output_json_schema(output_json_schema: dict[str, Any] | None) -> DomainVersion.OutputSchema | None:
    if not output_json_schema:
        return None
    schema = _extract_json_schema(output_json_schema)
    if schema is None:
        return None
    return _sanitize_json_schema(schema)


def version_request_to_domain(version: VersionRequest) -> DomainExperimentVersion:
    if version.prompt is not None:
        input_variables_schema, _ = json_schema_for_template([message_to_domain(m) for m in version.prompt], {})
    else:
        input_variables_schema = None

    return DomainExperimentVersion(
        alias=version.alias,
        model=version.model,
        temperature=version.temperature,
        top_p=version.top_p,
        enabled_tools=[tool_to_domain(t) for t in version.tools] if version.tools else None,
        prompt=[message_to_domain(m) for m in version.prompt] if version.prompt else None,
        output_schema=_sanitize_output_json_schema(version.output_json_schema),
        max_output_tokens=version.max_output_tokens,
        tool_choice=version.tool_choice,
        parallel_tool_calls=version.parallel_tool_calls,
        reasoning_effort=version.reasoning_effort,
        reasoning_budget=version.reasoning_budget,
        presence_penalty=version.presence_penalty,
        frequency_penalty=version.frequency_penalty,
        use_structured_generation=version.use_structured_generation,
        provider=version.provider,
        input_variables_schema=input_variables_schema,
    )


def version_request_from_domain(version: DomainVersion) -> VersionRequest:
    return VersionRequest(
        model=version.model or "",
        temperature=version.temperature,
        top_p=version.top_p,
        tools=[tool_from_domain(t) for t in version.enabled_tools] if version.enabled_tools else None,
        prompt=[message_from_domain(m) for m in version.prompt] if version.prompt else None,
        output_json_schema=version.output_schema.json_schema if version.output_schema else None,
        max_output_tokens=version.max_output_tokens,
        tool_choice=version.tool_choice,
        parallel_tool_calls=version.parallel_tool_calls,
        reasoning_effort=version.reasoning_effort,
        reasoning_budget=version.reasoning_budget,
        presence_penalty=version.presence_penalty,
        frequency_penalty=version.frequency_penalty,
        use_structured_generation=version.use_structured_generation,
        provider=version.provider,
    )


def input_from_domain[T: Input](agent_input: DomainInput, t: type[T] = Input, **kwargs: Any) -> T:
    return t(
        id=agent_input.id,
        messages=[message_from_domain(m) for m in agent_input.messages] if agent_input.messages else None,
        variables=agent_input.variables or None,
        **kwargs,
    )


def experiment_input_from_domain(input: DomainExperimentInput) -> ExperimentInput:
    test = input_from_domain(input, ExperimentInput, alias=input.alias)
    return test


def input_to_domain(agent_input: Input) -> DomainInput:
    return DomainInput(
        messages=[message_to_domain(m) for m in agent_input.messages] if agent_input.messages else None,
        variables=agent_input.variables or None,
    )


def experiment_input_to_domain(experiment_input: ExperimentInput) -> DomainExperimentInput:
    return DomainExperimentInput(
        messages=[message_to_domain(m) for m in experiment_input.messages] if experiment_input.messages else None,
        variables=experiment_input.variables or None,
        alias=experiment_input.alias,
    )


def output_from_domain(output: DomainOutput) -> Output:
    return Output(
        messages=[message_from_domain(m) for m in output.messages] if output.messages else None,
        error=Error(error=output.error.message) if output.error else None,
    )


def output_to_domain(output: Output) -> DomainOutput:
    return DomainOutput(
        messages=[message_to_domain(m) for m in output.messages] if output.messages else None,
        error=DomainError(message=output.error.error) if output.error else None,
    )


def completion_from_domain(completion: DomainCompletion) -> Completion:
    # Always derive created_at from the UUID7 ID for consistency

    return Completion(
        id=completion.id,
        agent_id=completion.agent.id,
        created_at=_sanitize_datetime(completion.created_at),
        version=version_from_domain(completion.version),
        input=input_from_domain(completion.agent_input),
        output=output_from_domain(completion.agent_output),
        messages=[message_from_domain(m) for m in completion.messages] if completion.messages else [],
        annotations=None,  # TODO:
        metadata=completion.metadata or None,
        cost_usd=completion.cost_usd or 0.0,
        duration_seconds=completion.duration_seconds or 0.0,
        traces=[trace_from_domain(t) for t in completion.traces] if completion.traces else None,
    )


def completion_to_domain(completion: Completion) -> DomainCompletion:
    # Always derive created_at from the UUID7 ID for consistency

    return DomainCompletion(
        id=completion.id,
        agent=DomainAgent(id=completion.agent_id, uid=0),
        version=version_to_domain(completion.version),
        agent_input=input_to_domain(completion.input),
        agent_output=output_to_domain(completion.output),
        messages=[message_to_domain(m) for m in completion.messages] if completion.messages else [],
        metadata=completion.metadata or None,
        cost_usd=completion.cost_usd or 0.0,
        duration_seconds=completion.duration_seconds or 0.0,
        traces=[trace_to_domain(t) for t in completion.traces] if completion.traces else [],
    )


def experiment_from_domain(
    experiment: DomainExperiment,
    annotations: list[DomainAnnotation],
) -> Experiment:
    return Experiment(
        id=experiment.id,
        agent_id=experiment.agent_id,
        created_at=_sanitize_datetime(experiment.created_at),
        updated_at=_sanitize_datetime(experiment.updated_at) if experiment.updated_at else None,
        author_name=experiment.author_name,
        title=experiment.title,
        description=experiment.description,
        result=experiment.result,
        completions=[experiment_completion_from_domain(c) for c in experiment.outputs] if experiment.outputs else None,
        versions=[experiment_version_from_domain(v) for v in experiment.versions] if experiment.versions else None,
        inputs=[experiment_input_from_domain(i) for i in experiment.inputs] if experiment.inputs else None,
        annotations=[annotation_from_domain(a) for a in annotations] if annotations else None,
        metadata=experiment.metadata or None,
        url=experiments_url(experiment.id),
    )


def create_experiment_to_domain(experiment: CreateExperimentRequest) -> DomainExperiment:
    return DomainExperiment(
        id=experiment.id or str(uuid7()),
        agent_id=experiment.agent_id,
        author_name=experiment.author_name,
        title=experiment.title,
        description=experiment.description or "",
        metadata=experiment.metadata or None,
        result=None,
        use_cache=experiment.use_cache,
    )


def agent_from_domain(agent: DomainAgent) -> Agent:
    return Agent(
        id=agent.id,
        name=agent.name,
        created_at=_sanitize_datetime(agent.created_at),
        uid=agent.uid,
    )


def create_agent_to_domain(agent: CreateAgentRequest) -> DomainAgent:
    return DomainAgent(
        id=agent.id,
        name=agent.name or "",
        uid=0,
    )


def model_reasoning_from_domain(model: DomainModelReasoningBudget) -> ModelReasoning:
    return ModelReasoning(
        can_be_disabled=model.disabled is not None,
        low_effort_reasoning_budget=model.low or 0,
        medium_effort_reasoning_budget=model.medium or 0,
        high_effort_reasoning_budget=model.high or 0,
        min_reasoning_budget=model.min or 0,
        max_reasoning_budget=model.max,
    )


def model_context_window_from_domain(model: MaxTokensData) -> ModelContextWindow:
    return ModelContextWindow(
        max_tokens=model.max_tokens,
        max_output_tokens=model.max_output_tokens or model.max_tokens,
    )


def model_pricing(model: ModelProviderData) -> ModelPricing:
    return ModelPricing(
        input_token_usd=model.text_price.prompt_cost_per_token,
        output_token_usd=model.text_price.completion_cost_per_token,
    )


def model_supports_from_domain(model: ModelDataSupports) -> ModelSupports:
    return ModelSupports(
        input=SupportsModality(
            image=model.supports_input_image,
            audio=model.supports_input_audio,
            pdf=model.supports_input_pdf,
            # TODO: we need to overhaul the model data to
            # add a proper support field for input test
            # See https://linear.app/workflowai/issue/WOR-4926/sanitize-model-supports-to-include-temperature-and-other-parameters
            text=not model.supports_audio_only,
        ),
        output=SupportsModality(
            image=model.supports_output_image,
            audio=False,
            pdf=False,
            text=model.supports_output_text,
        ),
        parallel_tool_calls=model.supports_parallel_tool_calls,
        tools=model.supports_tool_calling,
        # TODO: see https://linear.app/workflowai/issue/WOR-4926/sanitize-model-supports-to-include-temperature-and-other-parameters
        top_p=True,
        temperature=True,
    )


def model_response_from_domain(model_id: str, model: FinalModelData) -> Model:
    provider_data = model.providers[0][1]
    return Model(
        id=model_id,
        display_name=model.display_name,
        icon_url=model.icon_url,
        supports=model_supports_from_domain(model),
        pricing=model_pricing(provider_data),
        release_date=model.release_date,
        reasoning=model_reasoning_from_domain(model.reasoning) if model.reasoning is not None else None,
        context_window=model_context_window_from_domain(model.max_tokens_data),
        speed_index=model.speed_index,
    )


def model_response_filter(fields: Iterable[ModelField] | None, models: Iterable[Model]) -> Iterable[dict[str, Any]]:
    """Convert model data for MCP responses, excluding icon_url to reduce context window usage."""
    include = {"id", "display_name"}
    if fields is None:
        include.update(ModelField)
    else:
        include.update(fields)
    for model in models:
        yield model.model_dump(include=include, exclude_none=True)


def _sanitized_completion_id(completion_id: str) -> UUID:
    return UUID(sanitize_id(completion_id, IDType.COMPLETION))


def annotation_from_domain(annotation: DomainAnnotation) -> Annotation:
    target = None
    if annotation.target:
        target = Annotation.Target(
            completion_id=str(annotation.target.completion_id) if annotation.target.completion_id else None,
            experiment_id=annotation.target.experiment_id,
            key_path=annotation.target.key_path,
        )

    context = None
    if annotation.context:
        context = Annotation.Context(
            experiment_id=annotation.context.experiment_id,
            agent_id=annotation.context.agent_id,
        )

    metric = None
    if annotation.metric:
        metric = Annotation.Metric(
            name=annotation.metric.name,
            value=annotation.metric.value,
        )

    return Annotation(
        id=annotation.id,
        created_at=_sanitize_datetime(annotation.created_at),
        updated_at=_sanitize_datetime(annotation.updated_at) if annotation.updated_at else None,
        author_name=annotation.author_name,
        target=target,
        context=context,
        text=annotation.text,
        metric=metric,
        metadata=annotation.metadata,
    )


def annotation_to_domain(api_annotation: Annotation) -> DomainAnnotation:
    target = None
    if api_annotation.target:
        target = DomainAnnotation.Target(
            completion_id=_sanitized_completion_id(api_annotation.target.completion_id)
            if api_annotation.target.completion_id
            else None,
            experiment_id=sanitize_id(api_annotation.target.experiment_id, IDType.EXPERIMENT)
            if api_annotation.target.experiment_id
            else None,
            key_path=api_annotation.target.key_path,
        )

    context = None
    if api_annotation.context:
        context = DomainAnnotation.Context(
            experiment_id=sanitize_id(api_annotation.context.experiment_id, IDType.EXPERIMENT)
            if api_annotation.context.experiment_id
            else None,
            agent_id=sanitize_id(api_annotation.context.agent_id, IDType.AGENT)
            if api_annotation.context.agent_id
            else None,
        )

    metric = None
    if api_annotation.metric:
        metric = DomainAnnotation.Metric(
            name=api_annotation.metric.name,
            value=api_annotation.metric.value,
        )

    return DomainAnnotation(
        id=api_annotation.id,
        created_at=api_annotation.created_at,
        updated_at=api_annotation.updated_at or api_annotation.created_at,
        author_name=api_annotation.author_name,
        target=target,
        context=context,
        text=api_annotation.text,
        metric=metric,
        metadata=api_annotation.metadata,
    )


def graph_to_domain(graph: Graph) -> DomainGraph:
    return DomainGraph(
        type=graph.type,
        attributes=graph.model_dump(
            exclude={"type"},
            exclude_none=True,
        ),
    )


_GraphTypeAdapter = TypeAdapter(Graph)


def graph_from_domain(graph: DomainGraph) -> Graph | None:
    if not graph.type:
        _log.warning("Dashboard graph has no type", graph=graph)
        return None
    try:
        return _GraphTypeAdapter.validate_python(
            {
                "type": graph.type,
                **(graph.attributes or {}),
            },
        )
    except ValidationError as e:
        _log.warning("Invalid dashboard graph", graph=graph, error=e)
        return None


def view_to_domain(view: View) -> DomainView:
    return DomainView(
        id=view.id,
        title=view.title,
        query=view.query,
        graph=graph_to_domain(view.graph) if view.graph else None,
        position=0,
    )


def view_from_domain(view: DomainView) -> View:
    return View(
        id=view.id,
        title=view.title or "",
        query=view.query or "",
        graph=graph_from_domain(view.graph) if view.graph else None,
    )


def view_folder_to_domain(view_folder: ViewFolder) -> DomainViewFolder:
    return DomainViewFolder(
        id=view_folder.id,
        name=view_folder.name,
        views=[view_to_domain(v) for v in view_folder.views],
    )


def view_folder_from_domain(view_folder: DomainViewFolder) -> ViewFolder:
    return ViewFolder(
        id=view_folder.id,
        name=view_folder.name,
        views=[view_from_domain(v) for v in view_folder.views] if view_folder.views else [],
    )


def view_to_create_view_response(view: View) -> CreateViewResponse:
    return CreateViewResponse(
        id=view.id,
        view_url=view_url(view.id),
    )


def api_key_from_domain(api_key: DomainAPIKey) -> APIKey:
    return APIKey(
        id=api_key.id,
        name=api_key.name,
        partial_key=api_key.partial_key,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        created_by=api_key.created_by,
    )


def api_key_from_domain_complete(api_key: DomainCompleteAPIKey) -> CompleteAPIKey:
    if not api_key.api_key:
        raise ValueError("Partial key is not allowed")
    return CompleteAPIKey(
        id=api_key.id,
        name=api_key.name,
        partial_key=api_key.partial_key,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        created_by=api_key.created_by,
        key=api_key.api_key,
        api_host=ANOTHERAI_API_URL,
    )


def deployment_from_domain(deployment: DomainDeployment) -> Deployment:
    return Deployment(
        id=deployment.id,
        agent_id=deployment.agent_id,
        version=version_from_domain(deployment.version),
        metadata=deployment.metadata or {},
        created_at=_sanitize_datetime(deployment.created_at),
        updated_at=_sanitize_datetime(deployment.updated_at) if deployment.updated_at else None,
        url=deployment_url(deployment.id),
        created_by=deployment.created_by,
        archived_at=_sanitize_datetime(deployment.archived_at) if deployment.archived_at else None,
    )


def page_token_to_datetime(token: str | None):
    if not token:
        return None
    try:
        int_value = int(token)
    except ValueError as e:
        raise BadRequestError("Invalid page token") from e
    return datetime.fromtimestamp(int_value, UTC)


def page_token_from_datetime(dt: datetime) -> str:
    return str(int(dt.timestamp()))


def usage_from_domain(usage: DomainInferenceUsage) -> InferenceUsage:
    return InferenceUsage(
        prompt=TokenUsage(
            text_token_count=usage.prompt.text_token_count,
            audio_token_count=usage.prompt.audio_token_count,
            audio_count=usage.prompt.audio_count,
            image_token_count=usage.prompt.image_token_count,
            image_count=usage.prompt.image_count,
            cost_usd=usage.prompt.cost_usd,
        ),
        completion=CompletionUsage(
            text_token_count=usage.completion.text_token_count,
            cost_usd=usage.completion.cost_usd,
            cached_token_count=usage.completion.cached_token_count,
            reasoning_token_count=usage.completion.reasoning_token_count,
        ),
    )


def usage_to_domain(usage: InferenceUsage) -> DomainInferenceUsage:
    return DomainInferenceUsage(
        prompt=DomainTokenUsage(
            text_token_count=usage.prompt.text_token_count,
            audio_token_count=usage.prompt.audio_token_count,
            audio_count=usage.prompt.audio_count,
            image_token_count=usage.prompt.image_token_count,
            image_count=usage.prompt.image_count,
            cost_usd=usage.prompt.cost_usd,
        ),
        completion=DomainCompletionUsage(
            text_token_count=usage.completion.text_token_count,
            cost_usd=usage.completion.cost_usd,
            cached_token_count=usage.completion.cached_token_count,
            reasoning_token_count=usage.completion.reasoning_token_count,
        ),
    )


def trace_from_domain(trace: DomainTrace) -> Trace:
    if trace.kind == "llm":
        return Trace(
            kind=trace.kind,
            duration_seconds=trace.duration_seconds,
            cost_usd=trace.cost_usd,
            model=trace.model,
            provider=trace.provider,
            usage=usage_from_domain(trace.usage) if trace.usage else None,
        )
    return Trace(
        kind=trace.kind,
        duration_seconds=trace.duration_seconds,
        cost_usd=trace.cost_usd,
        name=trace.name,
        tool_input_preview=trace.tool_input_preview,
        tool_output_preview=trace.tool_output_preview,
    )


def trace_to_domain(trace: Trace) -> DomainTrace:
    if trace.kind == "llm":
        return DomainLLMTrace(
            kind="llm",
            duration_seconds=trace.duration_seconds,
            cost_usd=trace.cost_usd,
            usage=usage_to_domain(trace.usage) if trace.kind == "llm" and trace.usage else None,
            model=trace.model or "",
            provider=trace.provider or "",
        )
    return DomainToolTrace(
        kind="tool",
        duration_seconds=trace.duration_seconds,
        cost_usd=trace.cost_usd,
        name=trace.name or "",
        tool_input_preview=trace.tool_input_preview or "",
        tool_output_preview=trace.tool_output_preview or "",
    )


def experiment_completion_from_domain(completion: ExperimentOutput) -> Experiment.Completion:
    return Experiment.Completion(
        id=completion.completion_id,
        version=IDAndAlias(id=completion.version_id, alias=completion.version_alias),
        input=IDAndAlias(id=completion.input_id, alias=completion.input_alias),
        output=output_from_domain(completion.output) if completion.output else Output(),
        cost_usd=completion.cost_usd or 0.0,
        duration_seconds=completion.duration_seconds or 0.0,
    )


def _automatic_payment_from_domain(tenant: TenantData) -> Tenant.AutomaticPayment | None:
    if not tenant.automatic_payment_enabled:
        return None
    if tenant.automatic_payment_threshold is None or tenant.automatic_payment_balance_to_maintain is None:
        _log.warning("Automatic payment is enabled but threshold or balance to maintain is not set", tenant=tenant)
        return None
    return Tenant.AutomaticPayment(
        threshold=tenant.automatic_payment_threshold,
        balance_to_maintain=tenant.automatic_payment_balance_to_maintain,
    )


def tenant_from_domain(tenant: TenantData) -> Tenant:
    return Tenant(
        id=tenant.slug,
        current_credits_usd=tenant.current_credits_usd,
        automatic_payment=_automatic_payment_from_domain(tenant),
        payment_failure=Tenant.PaymentFailure(
            failure_date=tenant.payment_failure.failure_date,
            failure_code=tenant.payment_failure.failure_code,
            failure_reason=tenant.payment_failure.failure_reason,
        )
        if tenant.payment_failure
        else None,
    )

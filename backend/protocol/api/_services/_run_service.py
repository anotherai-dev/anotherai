import re
from typing import Any, NamedTuple

import structlog

from core.domain.agent import Agent
from core.domain.agent_input import AgentInput
from core.domain.deployment import DeploymentName
from core.domain.exceptions import BadRequestError
from core.domain.message import Message
from core.domain.models.model_data_mapping import MODEL_COUNT, get_model_id
from core.domain.models.models import Model
from core.domain.tenant_data import TenantData
from core.domain.version import Version
from core.providers._base.provider_error import MissingModelError
from core.services.completion_runner import CompletionRunner
from core.services.messages.messages_utils import json_schema_for_template
from core.services.models_service import suggest_model
from core.utils.coroutines import capture_errors
from core.utils.schema_gen import schema_from_data
from core.utils.schema_sanitation import streamline_schema, validate_schema
from protocol.api._run_models import (
    CHAT_COMPLETION_REQUEST_UNSUPPORTED_FIELDS,
    OpenAIProxyChatCompletionRequest,
    OpenAIProxyResponseFormat,
)
from protocol.api._services._run_conversions import (
    completion_response_from_domain,
    request_apply_to_version,
    request_messages_to_domain,
    use_fallback_to_domain,
)

_log = structlog.get_logger(__name__)


class _EnvironmentRef(NamedTuple):
    """A reference to a deployed environment"""

    agent_id: str
    schema_id: int
    environment: DeploymentName


class _ModelRef(NamedTuple):
    """A reference to a model with an optional agent id"""

    model: Model
    agent_id: str | None


class RunService:
    def __init__(self, tenant: TenantData, completion_runner: CompletionRunner):
        self._tenant = tenant
        self._completion_runner = completion_runner

    @classmethod
    async def missing_model_error(cls, model: str | None, prefix: str = ""):
        _check_lineup = f"Check the lineup 👉 ({MODEL_COUNT} models)"
        if not model:
            return BadRequestError(
                f"""Empty model
{_check_lineup}
To list all models programmatically: Use the list_models tool""",
            )

        components = [
            f"Unknown {prefix}model: {model}",
            _check_lineup,
            "To list all models programmatically: Use the list_models tool",
        ]
        if suggested := await suggest_model(model):
            components.insert(1, f"Did you mean {suggested}?")
        return BadRequestError("\n".join(components))

    @classmethod
    def _check_supported_fields(cls, request: OpenAIProxyChatCompletionRequest):
        set_fields = request.model_fields_set
        used_unsupported_fields = set_fields.intersection(CHAT_COMPLETION_REQUEST_UNSUPPORTED_FIELDS)
        if used_unsupported_fields:
            # Ignoring all set None fields
            fields = [f for f in used_unsupported_fields if getattr(request, f, None) is not None]
            if not fields:
                return

            plural = len(fields) > 1
            fields.sort()
            raise BadRequestError(
                f"Field{'s' if plural else ''} `{'`, `'.join(fields)}` {'are' if plural else 'is'} not supported",
                capture=True,
            )

        if request.n and request.n > 1:
            raise BadRequestError(
                "An n value greated than 1 is not supported",
            )

    class PreparedRun(NamedTuple):
        version: Version
        agent_input: AgentInput

    async def run(self, request: OpenAIProxyChatCompletionRequest, start_time: float):
        # First we need to locate the agent
        try:
            agent_ref = _extract_references(request)
        except MissingModelError as e:
            raise await self.missing_model_error(e.extras.get("model")) from None

        messages = list(request_messages_to_domain(request))

        if isinstance(agent_ref, _EnvironmentRef):
            raise BadRequestError("Deployments are not supported yet")
        prepared_run = await self._prepare_for_model(
            agent_ref=agent_ref,
            messages=messages,
            variables=request.input,
            response_format=request.response_format,
        )
        request_apply_to_version(request, prepared_run.version)

        try:
            use_fallback = use_fallback_to_domain(request.use_fallback)
        except MissingModelError as e:
            final_error = await self.missing_model_error(e.extras.get("model"), prefix="fallback ")
            raise final_error from None

        completion = await self._completion_runner.run(
            agent=Agent(id=agent_ref.agent_id or "default", uid=0),  # agent will be automatically created
            version=prepared_run.version,
            input=prepared_run.agent_input,
            start_time=start_time,
            metadata=request.metadata or {},
            timeout=None,
            use_cache=request.use_cache or "auto",
            use_fallback=use_fallback,
            conversation_id=request.conversation_id,
            completion_id=None,
        )
        return completion_response_from_domain(
            completion=completion,
            deprecated_function=request.function_call is not None,
            org=self._tenant,
        )

    async def _prepare_for_model(
        self,
        agent_ref: _ModelRef,
        messages: list[Message],
        variables: dict[str, Any] | None,
        response_format: OpenAIProxyResponseFormat | None,
    ) -> PreparedRun:
        if variables:
            # We have variables so we should have templated messages
            # We split the messages into two parts:
            # - The part that is templated (or the first system message)
            # - The part that is not templated
            # We don't remove any extras from the input, we just validate it
            schema_from_template, last_templated_index = _json_schema_from_input(messages, variables)
            if last_templated_index == -1:
                cutoff_index = 1 if messages[0].role == "system" else 0
            else:
                cutoff_index = last_templated_index + 1
        else:
            schema_from_template = None
            cutoff_index = 0

        version = Version(
            model=agent_ref.model,
            output_schema=_extract_output_schema(response_format),
            input_variables_schema=schema_from_template,
            prompt=messages[:cutoff_index] if cutoff_index > 0 else None,
        )

        return self.PreparedRun(
            version=version,
            agent_input=AgentInput(
                messages=messages[cutoff_index:],
                variables=variables,
            ),
        )


_environment_aliases = {
    "prod": DeploymentName.PRODUCTION,
    "development": DeploymentName.DEV,
}
_agent_schema_env_regex = re.compile(
    rf"^([^/]+)/#(\d+)/({'|'.join([*DeploymentName, *_environment_aliases.keys()])})$",
)
_metadata_env_regex = re.compile(
    rf"^#(\d+)/({'|'.join([*DeploymentName, *_environment_aliases.keys()])})$",
)


def _env_from_model_str(model: str) -> _EnvironmentRef | None:
    if match := _agent_schema_env_regex.match(model):
        with capture_errors(_log, f"Model {model} matched regexp but we failed to parse the values"):
            return _EnvironmentRef(
                agent_id=match.group(1),
                schema_id=int(match.group(2)),
                environment=DeploymentName(_environment_aliases.get(match.group(3), match.group(3))),
            )

    return None


def _env_from_fields(
    request: OpenAIProxyChatCompletionRequest,
    agent_id: str | None,
    model: Model | None,
) -> _EnvironmentRef | None:
    if not (request.environment or request.schema_id):
        return None
    if not (request.environment and request.schema_id and agent_id):
        raise BadRequestError(
            "When an environment or schema_id is provided, agent_id, environment and schema_id must be provided",
            capture=True,
            extras={"model": request.model, "environment": request.environment, "schema_id": request.schema_id},
        )

    try:
        environment = DeploymentName(request.environment)
    except Exception:  # noqa: BLE001
        if model:
            # That's ok. It could mean that someone passed an extra body parameter that's also called
            # environment. We can probably ignore it.
            _log.warning(
                "Received an invalid environment",
                environment=request.environment,
                model=request.model,
            )
            return None
        # We don't have a model. Meaning that it's likely a user error
        raise BadRequestError(
            f"Environment {request.environment} is not a valid environment. Valid environments are: "
            f"{', '.join(DeploymentName)}",
            capture=True,
            extras={"model": request.model, "environment": request.environment, "schema_id": request.schema_id},
        ) from None
    return _EnvironmentRef(
        agent_id=agent_id,
        schema_id=request.schema_id,
        environment=environment,
    )


def _reference_from_metadata(
    request: OpenAIProxyChatCompletionRequest,
    model: Model,
    agent_id: str | None,
) -> _EnvironmentRef | _ModelRef | None:
    if not request.metadata or "agent_id" not in request.metadata:
        return None

    # Overriding if the agent_id is None or not provided directly in the request
    if not agent_id or not request.agent_id:
        agent_id = request.metadata.get("agent_id")
    if not agent_id:
        return None

    if "environment" in request.metadata:
        match = _metadata_env_regex.match(request.metadata["environment"])
        if match:
            try:
                return _EnvironmentRef(
                    agent_id=request.metadata["agent_id"],
                    schema_id=int(match.group(1)),
                    environment=DeploymentName(_environment_aliases.get(match.group(2), match.group(2))),
                )
            except Exception:  # noqa: BLE001
                _log.exception("Failed to parse environment from metadata", metadata=request.metadata)
                return None

    return _ModelRef(
        model=model,
        agent_id=agent_id,
    )


def _extract_references(request: OpenAIProxyChatCompletionRequest) -> _EnvironmentRef | _ModelRef:
    """Extracts the model, agent_id, schema_id and environment from the model string
    and other body optional parameters.
    References can come from either:
    - the model string with a format either "<model>", "<agent_id>/<model>" or "<agent_id>/#<schema_id>/<environment>"
    - the body parameters environment, schema_id and agent_id
    """

    if env := _env_from_model_str(request.model):
        return env

    splits = request.model.split("/")
    agent_id = request.agent_id or (splits[0] if len(splits) > 1 else None)
    # Getting the model from the last component. This is to support cases like litellm that
    # prefix the model string with the provider
    try:
        model = get_model_id(splits[-1])
    except ValueError:
        model = None

    if env := _env_from_fields(request, agent_id, model):
        return env

    if not model:
        if len(splits) > 2:
            # This is very likely an invalid environment error so we should raise an explicit BadRequestError
            raise BadRequestError(
                f"'{request.model}' does not refer to a valid model or deployment. Use either the "
                "'<agent-id>/#<schema-id>/<environment>' format to target a deployed environment or "
                "<agent-id>/<model> to target a specific model. If the model cannot be changed, it is also "
                "possible to pass the agent_id, schema_id and environment at the root of the completion request. "
                "See https://run.workflowai.com/docs#/openai/chat_completions_v1_chat_completions_post for more "
                "information.",
                capture=True,
                extras={"model": request.model},
            )
        raise MissingModelError(model=splits[-1])

    if from_metadata := _reference_from_metadata(request, model=model, agent_id=agent_id):
        return from_metadata

    return _ModelRef(
        model=model,
        agent_id=agent_id,
    )


def _extract_output_schema(response_format: OpenAIProxyResponseFormat | None) -> Version.OutputSchema | None:
    if not response_format:
        return None

    if response_format.json_schema:
        schema = response_format.json_schema.schema_
        validate_schema(schema)
        return Version.OutputSchema(json_schema=streamline_schema(schema))

    if response_format.type == "json_object":
        # We return an empty schema
        # This will be interpreted as JSON mode by providers
        # TODO: test
        return Version.OutputSchema(json_schema={})

    return None


def _json_schema_from_input(
    messages: list[Message],
    variables: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, int]:
    if variables is None:
        # No body was sent with the request, so we treat the messages as a raw string
        return None, -1

    schema_from_input: dict[str, Any] | None = schema_from_data(variables) if variables else None
    schema_from_template, last_templated_index = json_schema_for_template(
        messages,
        base_schema=schema_from_input,
    )
    if not schema_from_template:
        if schema_from_input:
            raise BadRequestError("Input variables are provided but the messages do not contain a valid template")
        return None, -1
    if not schema_from_input:
        raise BadRequestError("Messages are templated but no input variables are provided")

    return streamline_schema(schema_from_template), last_templated_index

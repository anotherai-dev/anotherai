import re
from collections.abc import AsyncIterable, Callable
from typing import Any, NamedTuple

import structlog

from core.domain.agent import Agent
from core.domain.agent_input import AgentInput
from core.domain.exceptions import BadRequestError, JSONSchemaValidationError, ObjectNotFoundError
from core.domain.message import Message
from core.domain.models.model_data_mapping import get_model_id
from core.domain.models.models import Model
from core.domain.tenant_data import TenantData
from core.domain.version import Version
from core.providers._base.provider_error import MissingModelError
from core.services.completion_runner import CompletionRunner
from core.services.messages.messages_utils import json_schema_for_template_and_variables
from core.services.models_service import suggest_model
from core.storage.deployment_storage import DeploymentStorage
from core.utils.schema_sanitation import streamline_schema, validate_schema
from protocol.api._run_models import (
    CHAT_COMPLETION_REQUEST_UNSUPPORTED_FIELDS,
    OpenAIProxyChatCompletionRequest,
    OpenAIProxyResponseFormat,
)
from protocol.api._services.run._run_conversions import (
    completion_response_from_domain,
    request_apply_to_version,
    request_messages_to_domain,
    use_fallback_to_domain,
)

_log = structlog.get_logger(__name__)


_DEPLOYMENT_REGEXP = re.compile(r"^(anotherai/)?deployments?/(.+)$")


class _EnvironmentRef(NamedTuple):
    """A reference to a deployed environment"""

    deployment_id: str


class _ModelRef(NamedTuple):
    """A reference to a model with an optional agent id"""

    model: Model
    agent_id: str | None


class RunService:
    def __init__(
        self,
        tenant: TenantData,
        completion_runner: CompletionRunner,
        deployments_storage: DeploymentStorage,
    ):
        self._tenant = tenant
        self._completion_runner = completion_runner
        self._deployments_storage = deployments_storage

    @classmethod
    async def missing_model_error(
        cls,
        model: str | None,
        list_deployment_ids: Callable[[], AsyncIterable[str]] | None,
    ):
        if not model:
            return BadRequestError(
                """Missing model. To list all models programmatically: Use the list_models tool""",
            )

        deployments = [d async for d in list_deployment_ids()] if list_deployment_ids else None

        components = [
            f"{model} does not refer to a valid model {f'or deployment {deployments}' if deployments else ''}. The accepted formats are:",
            "- <model>: a valid model name or alias",
            "- <agent_id>/<model>: passing an agent_id as a prefix",
        ]

        if deployments:
            components.append("- anotherai/deployment/<deployment_id>: passing a deployment id")

        components.extend(
            [
                "",
                "To list all models programmatically: Use the list_models tool",
            ],
        )

        if deployments:
            components.append("To list all deployments programmatically: Use the list_deployments tool")
        if suggested := await suggest_model(model, deployments or []):
            components.insert(4, f"Did you mean {suggested}?")
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
        agent_id: str
        version: Version
        agent_input: AgentInput
        metadata: dict[str, Any]

    async def run(self, request: OpenAIProxyChatCompletionRequest, start_time: float):
        # First we need to locate the agent
        try:
            agent_ref = _extract_references(request)
        except MissingModelError as e:
            raise await self.missing_model_error(
                e.extras.get("model"),
                self._deployments_storage.list_deployment_ids,
            ) from None

        messages = list(request_messages_to_domain(request))

        if isinstance(agent_ref, _EnvironmentRef):
            prepared_run = await self._prepare_for_deployment(
                deployment_id=agent_ref.deployment_id,
                messages=messages,
                variables=request.input,
                response_format=request.response_format,
            )
        else:
            prepared_run = await self._prepare_for_model(
                agent_ref=agent_ref,
                messages=messages,
                variables=request.input,
                response_format=request.response_format,
            )
        request_apply_to_version(request, prepared_run.version)
        prepared_run.version.reset_id()

        try:
            use_fallback = use_fallback_to_domain(request.use_fallback)
        except MissingModelError as e:
            invalid_model = e.extras.get("model")
            suggested = await suggest_model(invalid_model, []) if invalid_model else None
            base = f"Invalid fallback model: {e.extras.get('model')}."
            if suggested:
                base += f" Did you mean {suggested}?"
            raise BadRequestError(base) from None

        if request.metadata:
            prepared_run.metadata.update(request.metadata)

        completion = await self._completion_runner.run(
            agent=Agent(id=prepared_run.agent_id, uid=0),  # agent will be automatically created
            version=prepared_run.version,
            input=prepared_run.agent_input,
            start_time=start_time,
            metadata=prepared_run.metadata,
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

    async def _prepare_for_deployment(
        self,
        deployment_id: str,
        messages: list[Message],
        variables: dict[str, Any] | None,
        response_format: OpenAIProxyResponseFormat | None,
    ) -> PreparedRun:
        try:
            deployment = await self._deployments_storage.get_deployment(deployment_id)
        except ObjectNotFoundError:
            raise BadRequestError(
                f"Deployment {deployment_id} does not exist. Please check the deployment id and try again.",
                capture=True,
            ) from None

        # Check compatibility of response_format:
        output_schema = _extract_output_schema(response_format)
        output_schema = _check_output_schema_compatibility(deployment.version.output_schema, output_schema)

        # Check compatibility of input_variables
        try:
            deployment.version.validate_input(variables)
        except JSONSchemaValidationError as e:
            raise BadRequestError(f"Deployment expected a different input:\n{e}", capture=True) from None

        return self.PreparedRun(
            agent_id=deployment.agent_id,
            version=deployment.version,
            agent_input=AgentInput(
                messages=messages,
                variables=variables,
            ),
            metadata={
                "anotherai/deployment_id": deployment_id,
            },
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
            schema_from_template, last_templated_index = json_schema_for_template_and_variables(messages, variables)
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
            agent_id=agent_ref.agent_id or "default",
            version=version,
            agent_input=AgentInput(
                messages=messages[cutoff_index:],
                variables=variables,
            ),
            metadata={},
        )


def _env_from_fields(request: OpenAIProxyChatCompletionRequest) -> _EnvironmentRef | None:
    if request.deployment_id:
        # If the deployment id matches the deployment regexp, we still try and extract the actual deployment id
        # from the pattern. Otherwise we accept as is since it is a dedicated field
        match = _DEPLOYMENT_REGEXP.match(request.deployment_id)
        if match:
            return _EnvironmentRef(
                deployment_id=match.group(2),
            )
        return _EnvironmentRef(deployment_id=request.deployment_id)

    if match := _DEPLOYMENT_REGEXP.match(request.model):
        return _EnvironmentRef(deployment_id=match.group(2))
    return None


def _reference_from_metadata(
    request: OpenAIProxyChatCompletionRequest,
    model: Model,
    agent_id: str | None,
) -> _ModelRef | None:
    if not request.metadata or "agent_id" not in request.metadata:
        return None

    # Overriding if the agent_id is None or not provided directly in the request
    if not agent_id or not request.agent_id:
        agent_id = request.metadata.get("agent_id")
    if not agent_id:
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

    if env := _env_from_fields(request):
        return env

    splits = request.model.split("/")
    agent_id = request.agent_id or (splits[0] if len(splits) > 1 else None)
    # Getting the model from the last component. This is to support cases like litellm that
    # prefix the model string with the provider
    try:
        model = get_model_id(splits[-1])
    except ValueError:
        model = None

    if not model:
        if len(splits) > 2:
            # This is very likely an invalid environment error so we should raise an explicit BadRequestError
            raise BadRequestError(
                f"""'{request.model}' does not refer to a valid model or deployment. The accepted formats are:
                - <model>: a valid model name or alias
                - <agent_id>/<model>: passing an agent_id as a prefix
                - anotherai/deployment/<deployment_id>: passing a deployment id

                If the model cannot be changed, it is also possible to pass the agent_id or deployment_id in the
                body of the request.""",
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


def _check_output_schema_compatibility(
    deployment_schema: Version.OutputSchema | None,
    requested_schema: Version.OutputSchema | None,
):
    if requested_schema is None:
        # The requested schema was not provided so here we take whatever was in the deployment
        return deployment_schema

    if deployment_schema is None:
        raise BadRequestError(
            "You requested a response format but the deployment did not refer to one. "
            "Please create a new deployment with the response format you want to use.",
        )

    # It is actually a bad idea to check for schema compatibility here.
    # OpenAI SDKs tend to do werid stuff with schemas before sending them, meaning that schemas imported from a
    # deployment might not be compatible with a schema sent from the SDK.
    # TODO: we could try to be smarter here:
    # - accept deployments where the only difference is the "required" field or nullable fields
    # - change streamline_schema to make all fields required as expected by the OpenAI SDK
    # In any case, the `deployment_tests.test_response_formats` should pass
    # try:
    #     JsonSchema(deployment_schema.json_schema).check_compatible(JsonSchema(requested_schema.json_schema))
    # except IncompatibleSchemaError as e:
    #     raise BadRequestError(
    #         f"The requested response format is not compatible with the deployment's response format.\n{e}",
    #     ) from None
    return requested_schema

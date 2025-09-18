import asyncio
import itertools
import json
import time
from collections.abc import Iterable
from typing import Any, final
from uuid import UUID

from pydantic import ValidationError
from structlog import get_logger

from core.domain.agent import Agent
from core.domain.agent_input import AgentInput
from core.domain.agent_output import AgentOutput
from core.domain.cache_usage import CacheUsage
from core.domain.error import Error as DomainError
from core.domain.events import EventRouter, StartExperimentCompletionEvent
from core.domain.exceptions import (
    BadRequestError,
    DuplicateValueError,
    InternalError,
    OperationTimeoutError,
)
from core.domain.models.model_data_mapping import get_model_id
from core.domain.version import Version as DomainVersion
from core.services.completion_runner import CompletionRunner
from core.services.messages.messages_utils import json_schema_for_template
from core.services.store_completion._run_previews import assign_input_preview, assign_output_preview
from core.storage.agent_storage import AgentStorage
from core.storage.completion_storage import CompletionStorage
from core.storage.deployment_storage import DeploymentStorage
from core.storage.experiment_storage import CompletionIDTuple, CompletionOutputTuple, ExperimentStorage
from core.utils.hash import HASH_REGEXP_32, hash_model, is_hash_32
from core.utils.uuid import uuid7
from protocol.api._api_models import Input, Output, PlaygroundOutput, Version
from protocol.api._services.conversions import (
    experiments_url,
    input_to_domain,
    message_to_domain,
    output_from_domain,
    version_from_domain,
    version_to_domain,
)
from protocol.api._services.utils_service import IDType, sanitize_id, sanitize_ids

_log = get_logger(__name__)


@final
class PlaygroundService:
    def __init__(
        self,
        completion_runner: CompletionRunner,
        agent_storage: AgentStorage,
        experiment_storage: ExperimentStorage,
        completion_storage: CompletionStorage,
        deployment_storage: DeploymentStorage,
        event_router: EventRouter,
    ):
        self._completion_runner = completion_runner
        self._agent_storage = agent_storage
        self._experiment_storage = experiment_storage
        self._completion_storage = completion_storage
        self._deployment_storage = deployment_storage
        self._event_router = event_router

    async def _get_version_by_id(self, agent_id: str, version_id: str) -> DomainVersion:
        id_type, id = sanitize_id(version_id)
        if not id_type:
            # Not sure what this is so we check if it's a hash
            id_type = IDType.VERSION if is_hash_32(id) else IDType.DEPLOYMENT

        match id_type:
            case IDType.VERSION:
                val, _ = await self._completion_storage.get_version_by_id(agent_id, id)
                return val
            case IDType.DEPLOYMENT:
                deployment = await self._deployment_storage.get_deployment(id)
                return deployment.version
            case _:
                raise BadRequestError(f"Invalid version id: {version_id}")

    async def add_versions_to_experiment(
        self,
        experiment_id: str,
        version: str | Version,
        overrides: list[dict[str, Any]] | None,
    ) -> list[str]:
        # First fetch the experiment and the associated inputs
        experiment = await self._experiment_storage.get_experiment(experiment_id, include={"agent_id", "inputs"})

        if isinstance(version, str):
            # The double conversion to and from domain sucks here but is necessary
            # Since the overrides will apply to the exposed version type
            base_version: Version = version_from_domain(await self._get_version_by_id(experiment.agent_id, version))
        else:
            base_version = version

        # First we compute the list of all versions
        # The _version_with_override will raise an error if one override is not valid
        async def _version_iterator():
            yield _validate_version(base_version)
            if not overrides:
                return
            for override in overrides:
                yield _validate_version(_version_with_override(base_version, override))

        # Creating domain versions
        versions = [version_to_domain(v) async for v in _version_iterator()]
        inserted_ids = await self._experiment_storage.add_versions(experiment_id, versions)

        self._check_compatibility(versions, experiment.inputs)

        if experiment.inputs:
            # Now we create completions for each version / input combination
            await self._start_experiment_completions(
                experiment_id,
                input_ids=[input.id for input in experiment.inputs],
                version_ids=inserted_ids,
            )

        return [IDType.VERSION.wrap(id) for id in inserted_ids]

    async def add_inputs_to_experiment(
        self,
        experiment_id: str,
        inputs: list[Input] | None,
        input_query: str | None,
    ) -> list[str]:
        experiment = await self._experiment_storage.get_experiment(experiment_id, include={"versions"})
        if inputs and input_query:
            raise BadRequestError("Exactly one of inputs and input_query must be provided")

        if input_query:
            inputs = await self._extract_inputs_from_query(input_query)
        elif not inputs:
            raise BadRequestError("Exactly one of inputs and input_query must be provided")

        domain_inputs = [input_to_domain(input) for input in inputs]
        for input in domain_inputs:
            assign_input_preview(input)
        self._check_compatibility(experiment.versions, domain_inputs)

        inserted_ids = await self._experiment_storage.add_inputs(experiment_id, domain_inputs)
        if experiment.versions:
            await self._start_experiment_completions(
                experiment_id,
                version_ids=(v.id for v in experiment.versions),
                input_ids=(input.id for input in domain_inputs),
            )

        return [IDType.INPUT.wrap(id) for id in inserted_ids]

    async def _start_experiment_completions(
        self,
        experiment_id: str,
        version_ids: Iterable[str],
        input_ids: Iterable[str],
    ):
        completions_to_insert = [
            CompletionIDTuple(completion_id=uuid7(), version_id=version_id, input_id=input_id)
            for version_id, input_id in itertools.product(version_ids, input_ids)
        ]
        inserted_completions_ids = await self._experiment_storage.add_completions(
            experiment_id,
            completions_to_insert,
        )
        # All the inserted completions should be started
        for c in completions_to_insert:
            if c.completion_id not in inserted_completions_ids:
                # Might be a race condition somewhere so we can just ignore
                continue
            self._event_router(
                StartExperimentCompletionEvent(
                    experiment_id=experiment_id,
                    completion_id=c.completion_id,
                    version_id=c.version_id,
                    input_id=c.input_id,
                ),
            )

    async def _fetch_playground_output(
        self,
        experiment_id: str,
        version_ids: set[str] | None,
        input_ids: set[str] | None,
    ) -> PlaygroundOutput:
        completions = await self._experiment_storage.list_experiment_completions(
            experiment_id,
            version_ids=version_ids,
            input_ids=input_ids,
            include={"output"},
        )

        def _completion_iter():
            for c in completions:
                if not c.output or not c.cost_usd or not c.duration_seconds:
                    _log.warning("Playground: Completion is not properly completed", completion_id=c.completion_id)
                yield PlaygroundOutput.Completion(
                    id=c.completion_id,
                    input_id=c.input_id,
                    version_id=c.version_id,
                    output=output_from_domain(c.output) if c.output else Output(),
                    cost_usd=c.cost_usd,
                    duration_seconds=c.duration_seconds,
                )

        return PlaygroundOutput(
            experiment_id=experiment_id,
            experiment_url=experiments_url(experiment_id),
            completions=list(_completion_iter()),
        )

    async def get_experiment_outputs(
        self,
        experiment_id: str,
        version_ids: list[str] | None,
        input_ids: list[str] | None,
        max_wait_time_seconds: float = 30,
    ) -> PlaygroundOutput:
        sanitized_versions = sanitize_ids(version_ids, IDType.VERSION, HASH_REGEXP_32) if version_ids else None
        sanitized_inputs = sanitize_ids(input_ids, IDType.INPUT, HASH_REGEXP_32) if input_ids else None

        start_time = time.time()

        while time.time() - start_time < max_wait_time_seconds:
            # First fetch completions to check that all are properly completed
            completions = await self._experiment_storage.list_experiment_completions(
                experiment_id,
                version_ids=sanitized_versions,
                input_ids=sanitized_inputs,
            )
            if all(c.completed_at for c in completions):
                return await self._fetch_playground_output(experiment_id, sanitized_versions, sanitized_inputs)

            # TODO: check that all completions are properly started

            await asyncio.sleep(5)

        raise OperationTimeoutError(f"Playground: Experiment outputs not ready after {max_wait_time_seconds} seconds")

    async def _run_version(
        self,
        agent_id: str,
        version: DomainVersion,
        input: AgentInput,
        completion_id: UUID,
        metadata: dict[str, Any],
        use_cache: CacheUsage | None,
    ) -> CompletionOutputTuple:
        _log.debug("Playground: Running single completion", version_id=version.id, input_id=input.id)
        # TODO: fix to use UUIDs everywhere
        completion_id_str = str(completion_id)
        cached = await self._completion_runner.check_cache(
            completion_id=completion_id_str,
            agent=Agent(id=agent_id, uid=0),
            version=version,
            input=input,
            metadata=metadata,
            use_cache=use_cache,
        )
        if cached:
            return CompletionOutputTuple(
                output=cached.agent_output,
                duration_seconds=cached.duration_seconds,
                cost_usd=cached.cost_usd,
            )
        try:
            runner, builder = await self._completion_runner.prepare(
                agent=Agent(id=agent_id, uid=0),  # agent will be automatically created
                version=version,
                input=input,
                start_time=time.time(),
                metadata=metadata,
                timeout=None,
                use_fallback="never",
                conversation_id=None,
                completion_id=completion_id_str,
            )
            completion = await self._completion_runner.run(runner, builder)

        except Exception as e:  # noqa: BLE001
            _log.debug(
                "Playground: Running single completion failed",
                version_id=version.id,
                input_id=input.id,
            )
            return CompletionOutputTuple(
                output=AgentOutput(error=DomainError(message=str(e))),
                duration_seconds=None,
                cost_usd=None,
            )

        _log.debug(
            "Playground: Running single completion succeeded",
            version_id=version.id,
            input_id=input.id,
        )
        return CompletionOutputTuple(
            output=completion.agent_output,
            duration_seconds=completion.duration_seconds,
            cost_usd=completion.cost_usd,
        )

    async def _extract_inputs_from_query(self, query: str) -> list[Input]:
        # Replacing wildcard
        query = query.replace("SELECT * FROM completions", "SELECT input_variables, input_messages FROM completions")
        rows = await self._completion_storage.raw_query(query)
        if not rows:
            raise BadRequestError("Completion query returned no results")
        first_row = rows[0]
        if "input_variables" not in first_row and "input_messages" not in first_row:
            raise BadRequestError("Completion query must return input_variables and input_messages columns")
        out: list[Input] = []
        input_hashes: set[str] = set()

        def _load_raw_json(s: str) -> Any:
            if not s:
                return None
            return json.loads(s)

        for row in rows:
            _input = Input.model_validate(
                {
                    "variables": _load_raw_json(row["input_variables"]),
                    "messages": _load_raw_json(row["input_messages"]),
                },
            )
            _hash = hash_model(_input)
            if _hash in input_hashes:
                continue
            input_hashes.add(_hash)
            out.append(_input)
        return out

    def _check_compatibility(self, versions: list[DomainVersion] | None, inputs: list[AgentInput] | None):
        # check for empty prompt and messages
        # If at least one version has no prompt AND at least one input has no messages, raise an error
        if not versions or not inputs:
            return

        if any(not v.prompt for v in versions) and any(not i.messages for i in inputs):
            raise BadRequestError("""At least a combination of input and prompt resulted in empty messages.
            - If you do not provide a prompt, make sure all inputs have messages
            - If at least one input does not contain messages, make sure all prompts have messages""")

    async def _run_completion(self, event: StartExperimentCompletionEvent):
        # Retrieve the experiment to get the appropriate input and output
        experiment = await self._experiment_storage.get_experiment(
            event.experiment_id,
            include={"agent_id", "versions", "inputs", "use_cache", "metadata"},
            version_ids={event.version_id},
            input_ids={event.input_id},
        )
        if (
            not experiment.versions
            or not experiment.inputs
            or len(experiment.versions) != 1
            or len(experiment.inputs) != 1
        ):
            # Fatal exception, likely because an input or version was deleted in the mean time
            # TODO: handle proper fallback
            raise InternalError(
                "Experiment is missing either version or input",
                fatal=True,
                extras={
                    "experiment_id": event.experiment_id,
                    "version_id": event.version_id,
                    "input_id": event.input_id,
                    "versions_count": len(experiment.versions) if experiment.versions else 0,
                    "inputs_count": len(experiment.inputs) if experiment.inputs else 0,
                },
            )
        version = experiment.versions[0]
        input = experiment.inputs[0]

        output = await self._run_version(
            agent_id=experiment.agent_id,
            version=version,
            input=input,
            completion_id=event.completion_id,
            metadata={"anotherai/experiment_id": event.experiment_id},
            use_cache=experiment.use_cache,
        )
        assign_output_preview(output.output)

        # Now we have an output, we can just store it
        await self._experiment_storage.add_completion_output(
            event.experiment_id,
            event.completion_id,
            output,
        )

    async def start_experiment_completion(self, event: StartExperimentCompletionEvent):
        # First think we do is "lock" the completion by marking it as started
        try:
            await self._experiment_storage.start_completion(event.experiment_id, event.completion_id)
        except DuplicateValueError:
            # Logging as a warning, it's ok we can just skip
            _log.warning("Playground: Completion already started", completion_id=event.completion_id)
            return
        # Any other exception can raise
        # Now we should not fail

        try:
            await self._run_completion(event)
        except Exception as e:
            # We should fail the completion and re-raise
            await self._experiment_storage.fail_completion(event.experiment_id, event.completion_id)
            raise e


def _validate_version(version: Version) -> Version:
    try:
        version.model = get_model_id(version.model)
    except ValueError as e:
        raise BadRequestError(f"Invalid model: {version.model}") from e

    if version.prompt and not version.input_variables_schema:
        variables, _ = json_schema_for_template([message_to_domain(m) for m in version.prompt], {})
        version.input_variables_schema = variables

    return version


def _version_with_override(base: Version, override: dict[str, Any]) -> Version:
    try:
        return Version.model_validate(
            {
                **base.model_dump(exclude_unset=True, exclude_none=True),
                **override,
            },
        )

    except ValidationError as e:
        raise BadRequestError(f"Invalid version with override: {e}") from e

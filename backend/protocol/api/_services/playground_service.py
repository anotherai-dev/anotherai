import asyncio
import json
import time
from collections.abc import Coroutine
from typing import Any, final

from core.domain.agent import Agent
from core.domain.cache_usage import CacheUsage
from core.domain.exceptions import BadRequestError, ObjectNotFoundError
from core.domain.experiment import Experiment
from core.domain.models.model_data_mapping import get_model_id
from core.domain.models.models import Model
from core.domain.version import Version as DomainVersion
from core.services.completion_runner import CompletionRunner
from core.services.messages.messages_utils import json_schema_for_template_and_variables
from core.storage.agent_storage import AgentStorage
from core.storage.completion_storage import CompletionStorage
from core.storage.experiment_storage import ExperimentStorage
from core.utils.hash import hash_model
from core.utils.uuid import uuid7
from protocol.api._api_models import Error, Input, Message, Output, PlaygroundOutput, Tool
from protocol.api._services.conversions import (
    experiments_url,
    input_to_domain,
    message_to_domain,
    output_from_domain,
    tool_to_domain,
)


@final
class PlaygroundService:
    def __init__(
        self,
        completion_runner: CompletionRunner,
        agent_storage: AgentStorage,
        experiment_storage: ExperimentStorage,
        completion_storage: CompletionStorage,
    ):
        self._completion_runner = completion_runner
        self._agent_storage = agent_storage
        self._experiment_storage = experiment_storage
        self._completion_storage = completion_storage

    @classmethod
    def _parse_models(cls, models: str) -> list[Model]:
        out: list[Model] = []
        invalid_models: list[str] = []
        for model in models.split(","):
            m = model.strip()
            if not m:
                invalid_models.append(model)
                continue
            out.append(get_model_id(m))
        if invalid_models:
            raise BadRequestError(f"Invalid models: {invalid_models}")
        return out

    @classmethod
    def _parse_temperatures(cls, temperatures: str) -> list[float]:
        return [float(temp.strip()) for temp in temperatures.split(",") if temp.strip()] or [1.0]

    @classmethod
    def _version_iterator(
        cls,
        models: list[Model],
        temperatures: list[float],
        prompts: list[list[Message]],
        tool_lists: list[list[Tool]],
        output_schemas: list[dict[str, Any]],
        variables: dict[str, Any] | None,
    ):
        for model in models:
            for temperature in temperatures or [1.0]:
                for prompt in prompts or [None]:
                    if prompt:
                        domain_prompt = [message_to_domain(m) for m in prompt]
                        variables_schema, _ = json_schema_for_template_and_variables(domain_prompt, variables)
                    else:
                        domain_prompt = None
                        variables_schema = None

                    for tool_list in tool_lists or [None]:
                        for output_schema in output_schemas or [None]:
                            yield DomainVersion(
                                model=model,
                                temperature=temperature,
                                prompt=[message_to_domain(m) for m in prompt] if prompt else None,
                                enabled_tools=[tool_to_domain(t) for t in tool_list] if tool_list else None,
                                output_schema=DomainVersion.OutputSchema(json_schema=output_schema)
                                if output_schema
                                else None,
                                input_variables_schema=variables_schema,
                            )

    async def _run_version(
        self,
        agent_id: str,
        version: DomainVersion,
        input: Input,
        start_time: float,
        completion_id: str | None,
        metadata: dict[str, Any],
        use_cache: CacheUsage,
    ) -> PlaygroundOutput.Completion:
        try:
            completion = await self._completion_runner.run(
                agent=Agent(id=agent_id, uid=0),  # agent will be automatically created
                version=version,
                input=input_to_domain(input),
                start_time=start_time,
                metadata=metadata,
                timeout=None,
                use_cache=use_cache,
                use_fallback="never",
                conversation_id=None,
                completion_id=completion_id,
            )
        except Exception as e:  # noqa: BLE001
            return PlaygroundOutput.Completion(
                id=getattr(e, "task_run_id", None) or "",
                output=Output(error=Error(error=str(e))),
                cost_usd=None,
                duration_seconds=None,
            )
        return PlaygroundOutput.Completion(
            id=completion.id,
            output=output_from_domain(completion.agent_output),
            cost_usd=completion.cost_usd,
            duration_seconds=completion.duration_seconds,
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

    async def run(  # noqa: C901
        self,
        author_name: str,
        agent_id: str | None,
        inputs: list[Input] | None,
        completion_query: str | None,
        models: str,
        prompts: list[list[Message]] | None,
        temperatures: str,
        tool_lists: list[list[Tool]] | None,
        output_schemas: list[dict[str, Any]] | None,
        experiment_id: str | None,
        experiment_description: str | None,
        experiment_title: str | None,
        metadata: dict[str, Any] | None,
        use_cache: CacheUsage,
    ) -> PlaygroundOutput:
        # Validate that we have inputs
        if completion_query:
            if inputs:
                raise BadRequestError("Cannot provide both inputs and completion_query")
            inputs = await self._extract_inputs_from_query(completion_query)
        elif not inputs:
            if not prompts:
                raise ValueError("Either prompts, inputs or input_query must be provided")
            prompts, inputs = _extract_input_from_prompts(prompts)

        if not agent_id and metadata:
            agent_id = metadata.pop("agent_id", None)
        if not agent_id:
            agent_id = "default"

        if not experiment_id:
            if not experiment_title:
                raise BadRequestError(
                    "Experiment title is required if experiment_id is not provided",
                )
            experiment_id = str(uuid7())

        base_metadata = {
            "anotherai/experiment_id": experiment_id,
        }
        if metadata:
            base_metadata.update(metadata)

        try:
            agent = await self._agent_storage.get_agent(agent_id)
        except ObjectNotFoundError:
            agent = Agent(id=agent_id, uid=0)
            await self._agent_storage.store_agent(agent)

        tasks: list[Coroutine[Any, Any, PlaygroundOutput.Completion]] = []
        start_time = time.time()
        run_ids: list[str] = []
        for version in self._version_iterator(
            models=self._parse_models(models),
            temperatures=self._parse_temperatures(temperatures),
            prompts=prompts or [],
            tool_lists=tool_lists or [],
            output_schemas=output_schemas or [],
            # Only considering the first input to determine the variables schema
            # TODO: handle cases where the variable schemas are different accross inputs ?
            variables=inputs[0].variables if inputs else None,
        ):
            for i in inputs:
                completion_id = str(uuid7())
                tasks.append(
                    self._run_version(
                        agent_id,
                        version,
                        i,
                        start_time,
                        completion_id=completion_id,
                        metadata=base_metadata,
                        use_cache=use_cache,
                    ),
                )
                run_ids.append(completion_id)

        experiment = Experiment(
            id=experiment_id,
            author_name=author_name,
            title=experiment_title or "",
            description=experiment_description or "",
            result=None,
            agent_id=agent_id,
            run_ids=run_ids,
            metadata={},
        )
        await self._experiment_storage.create(experiment, agent.uid)

        completions = await asyncio.gather(*tasks)
        return PlaygroundOutput(
            completions=completions,
            experiment_id=experiment_id,
            experiment_url=experiments_url(experiment_id),
        )


def _extract_input_from_prompts(prompts: list[list[Message]]) -> tuple[list[list[Message]], list[Input]]:
    # We attempt to extract a common system message from the prompts
    first_prompt = prompts[0]
    if first_prompt and first_prompt[0].role in {"developer", "system"}:
        first_system_message = first_prompt[0]
        # We check if all the prompts have the same system message
        if all(p and p[0] == first_system_message for p in prompts):
            # That means that the first system messages should actually be part of the prompt (aka version.prompt)
            return ([[first_system_message]], [Input(messages=m[1:]) for m in prompts])

    # otherwise every list of messages in prompt should actually be part of the input
    return ([], [Input(messages=m) for m in prompts])

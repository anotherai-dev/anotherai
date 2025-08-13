from collections.abc import Iterator

import structlog

from core.domain.agent_completion import AgentCompletion
from core.domain.file import File
from core.services.file_service import FileService
from core.services.store_completion._run_previews import assign_run_previews
from core.storage.agent_storage import AgentStorage
from core.storage.completion_storage import CompletionStorage
from core.storage.file_storage import FileStorage
from core.utils.coroutines import capture_errors
from core.utils.hash import hash_string

log = structlog.get_logger(__name__)


class CompletionStorer:
    def __init__(
        self,
        completion_storage: CompletionStorage,
        agent_storage: AgentStorage,
        file_storage: FileStorage,
        # event_router: EventRouter,
    ):
        self._completion_storage = completion_storage
        # self._event_router = event_router
        self._file_storage = file_storage
        self._agent_storage = agent_storage

    # TODO: test
    async def store_completion(self, completion: AgentCompletion):
        # Handle files
        with capture_errors(log, "Error storing files"):
            await FileService(self._file_storage).store_files(
                _file_iterator(completion),
                f"completions/{completion.id}",
            )
        # Create agent if needed
        if completion.agent.uid == 0:
            await self._agent_storage.store_agent(completion.agent)

        assign_run_previews(completion)
        # TODO: conversation_id
        # Store completion
        completion.version.reset_id()
        _ = await self._completion_storage.store_completion(completion)


def _file_cache_key(file: File) -> str:
    return file.url or hash_string(file.data or "")


def _file_iterator(completion: AgentCompletion) -> Iterator[File]:
    for message in completion.messages:
        yield from message.file_iterator()
    if completion.agent_input.messages:
        for message in completion.agent_input.messages:
            yield from message.file_iterator()
    if completion.agent_output.messages:
        for message in completion.agent_output.messages:
            yield from message.file_iterator()

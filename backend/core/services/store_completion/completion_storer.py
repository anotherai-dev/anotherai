import asyncio
from collections.abc import Iterator

import structlog

from core.domain.agent_completion import AgentCompletion
from core.domain.file import File
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

    async def _store_files(self, completion: AgentCompletion):
        """Make sure we only store URLs for files and not base64 data"""
        unique_files: dict[str, File] = {}

        for file in _file_iterator(completion):
            if file.storage_url:
                continue

            unique_files[_file_cache_key(file)] = file

        _storage_urls: dict[str, str] = {}

        async def _download_file(key: str, file: File):
            with capture_errors(log, "Error downloading file"):
                _storage_urls[key] = await self._file_storage.store_file(file, completion.id)

        async with asyncio.TaskGroup() as tg:
            for key, file in unique_files.items():
                tg.create_task(_download_file(key, file))

        for file in _file_iterator(completion):
            if storage_url := _storage_urls.get(_file_cache_key(file)):
                file.storage_url = storage_url
                # Overriding file url if it is a data url or not set
                if not file.url or file.url.startswith("data:"):
                    file.url = file.storage_url
            if file.url:
                file.data = None

    async def store_completion(self, completion: AgentCompletion):
        # Handle files
        with capture_errors(log, "Error storing files"):
            await self._store_files(completion)
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

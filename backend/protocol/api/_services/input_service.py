from collections.abc import Iterator

from core.domain.agent_input import AgentInput
from core.domain.file import File
from core.services.file_service import FileService
from core.services.store_completion._run_previews import compute_input_preview
from core.storage.completion_storage import CompletionStorage
from core.storage.file_storage import FileStorage
from protocol.api._api_models import CreateInputRequest, SavedInput
from protocol.api._services.conversions import create_input_to_domain, saved_input_from_domain


class InputService:
    def __init__(self, completion_storage: CompletionStorage, file_storage: FileStorage):
        self._completion_storage = completion_storage
        self._file_storage = file_storage

    # TODO: test
    async def create_input(self, input: CreateInputRequest) -> SavedInput:
        # TODO: handle files
        domain_input = create_input_to_domain(input)
        if not domain_input.preview:
            domain_input.preview = compute_input_preview(
                domain_input.variables,
                domain_input.messages,
            )
        await FileService(self._file_storage).store_files(
            _input_file_iterator(domain_input),
            f"inputs/{domain_input.id}",
        )
        await self._completion_storage.store_input(domain_input)
        return saved_input_from_domain(domain_input)


def _input_file_iterator(input: AgentInput) -> Iterator[File]:
    if not input.messages:
        return

    for m in input.messages:
        yield from m.file_iterator()

from typing import final
from urllib.parse import quote_plus

from core.consts import ANOTHERAI_APP_URL
from core.domain.exceptions import BadRequestError
from core.services.store_completion.completion_storer import CompletionStorer
from core.storage.agent_storage import AgentStorage
from core.storage.completion_storage import CompletionStorage
from core.utils.uuid import is_uuid7_str, uuid7
from protocol.api._api_models import Completion, ImportCompletionResponse, QueryCompletionResponse
from protocol.api._services._urls import completion_url
from protocol.api._services.conversions import completion_from_domain, completion_to_domain


@final
class CompletionService:
    def __init__(self, completion_storage: CompletionStorage, agent_storage: AgentStorage):
        self._completion_storage = completion_storage
        self._agent_storage = agent_storage

    async def get_completion(self, completion_id: str) -> Completion:
        completion = await self._completion_storage.completions_by_id(completion_id)
        return completion_from_domain(completion)

    async def query_completions(self, query: str) -> QueryCompletionResponse:
        rows = await self._completion_storage.raw_query(query)

        quoted = quote_plus(query)

        return QueryCompletionResponse(rows=rows, url=f"{ANOTHERAI_APP_URL}/completions?query={quoted}")

    @classmethod
    async def create_completion(
        cls,
        completion: Completion,
        completion_storer: CompletionStorer,
    ) -> ImportCompletionResponse:
        if not completion.id:
            completion.id = str(uuid7())
        elif not is_uuid7_str(completion.id):
            raise BadRequestError(f"Invalid completion id '{completion.id}'. The completion ID must be a UUID7.")
        await completion_storer.store_completion(completion_to_domain(completion))
        return ImportCompletionResponse(id=completion.id, url=completion_url(completion.id))

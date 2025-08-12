from typing import final
from urllib.parse import quote_plus

from core.consts import ANOTHERAI_APP_URL
from core.storage.agent_storage import AgentStorage
from core.storage.completion_storage import CompletionStorage
from protocol.api._api_models import Completion, QueryCompletionResponse
from protocol.api._services.conversions import completion_from_domain


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

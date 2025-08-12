from unittest.mock import Mock

import pytest

from core.consts import ANOTHERAI_APP_URL
from core.storage.agent_storage import AgentStorage
from core.storage.completion_storage import CompletionStorage
from protocol.api._services.completion_service import CompletionService


@pytest.fixture
def mock_completion_storage():
    return Mock(spec=CompletionStorage)


@pytest.fixture
def mock_agent_storage():
    return Mock(spec=AgentStorage)


@pytest.fixture
def completion_service(mock_completion_storage: Mock, mock_agent_storage: Mock):
    return CompletionService(mock_completion_storage, mock_agent_storage)


class TestQueryCompletions:
    async def test_query_completions(self, completion_service: CompletionService, mock_completion_storage: Mock):
        mock_completion_storage.raw_query.return_value = [
            {"id": "1", "input_variables": {"a": "b"}, "input_messages": ["c"]},
        ]
        res = await completion_service.query_completions("SELECT * FROM completions")
        assert res.url == f"{ANOTHERAI_APP_URL}/completions?query=SELECT+%2A+FROM+completions"

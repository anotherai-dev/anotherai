# pyright: reportPrivateUsage=false

from typing import Any

import pytest

from protocol.api._run_models import OpenAIProxyChatCompletionRequest, OpenAIProxyMessage
from protocol.api._services.run.run_service import _EnvironmentRef, _extract_references


def _proxy_request(**kwargs: Any):
    base = OpenAIProxyChatCompletionRequest(
        model="gpt-4o",
        messages=[
            OpenAIProxyMessage(
                role="user",
                content="Hello, how are you?",
            ),
        ],
    )
    return base.model_copy(update=kwargs)


class TestExtractReferences:
    @pytest.mark.parametrize(
        ("updates", "deployment_id"),
        [
            pytest.param(
                {"model": "anotherai/deployments/123"},
                "123",
                id="in model",
            ),
            pytest.param(
                {"deployment_id": "123"},
                "123",
                id="in body",
            ),
        ],
    )
    def test_deployments(self, updates: dict[str, Any], deployment_id: str):
        request = _proxy_request(**updates)
        extracted = _extract_references(request)
        assert isinstance(extracted, _EnvironmentRef)
        assert extracted.deployment_id == deployment_id

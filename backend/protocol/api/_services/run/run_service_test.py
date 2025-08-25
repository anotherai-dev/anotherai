# pyright: reportPrivateUsage=false

from typing import Any

import pytest

from core.domain.exceptions import BadRequestError
from core.domain.models.model_data_mapping import get_model_id
from protocol.api._run_models import OpenAIProxyChatCompletionRequest, OpenAIProxyMessage
from protocol.api._services.run.run_service import _EnvironmentRef, _extract_references, _ModelRef


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

    @pytest.mark.parametrize(
        ("updates", "expected_agent_id"),
        [
            pytest.param(
                {"model": "gpt-4o"},
                None,
                id="model_only",
            ),
            pytest.param(
                {"model": "agent-123/gpt-4o"},
                "agent-123",
                id="agent_in_model_path",
            ),
            pytest.param(
                {"model": "gpt-4o", "agent_id": "body-agent"},
                "body-agent",
                id="agent_in_body",
            ),
            pytest.param(
                {"model": "agent-in-path/gpt-4o", "metadata": {"agent_id": "meta-agent"}},
                "meta-agent",
                id="metadata_overrides_when_body_missing",
            ),
            pytest.param(
                {
                    "model": "agent-in-path/gpt-4o",
                    "agent_id": "body-agent",
                    "metadata": {"agent_id": "meta-agent"},
                },
                "body-agent",
                id="body_wins_over_metadata",
            ),
        ],
    )
    def test_model_references(self, updates: dict[str, Any], expected_agent_id: str | None):
        request = _proxy_request(**updates)
        extracted = _extract_references(request)
        assert isinstance(extracted, _ModelRef)
        assert extracted.model == get_model_id("gpt-4o")
        assert extracted.agent_id == expected_agent_id

    def test_invalid_environment_error(self):
        request = _proxy_request(model="agent/#schema/dev")
        with pytest.raises(BadRequestError) as excinfo:
            _extract_references(request)
        assert "does not refer to a valid model or deployment" in str(excinfo.value)


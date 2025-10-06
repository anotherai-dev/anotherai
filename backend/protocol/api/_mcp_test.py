# pyright: reportPrivateUsage=false

from typing import Any
from unittest.mock import ANY, AsyncMock, Mock, patch

import pytest
from fastmcp import Client

from core.domain.tenant_data import TenantData
from core.domain.version import Version
from protocol._common.lifecycle import LifecycleDependencies
from protocol.api._api_models import VersionRequest
from protocol.api._services.playground_service import PlaygroundService
from tests.fake_models import fake_experiment


@pytest.fixture
def mock_lifecycle_deps(mock_storage_builder: Mock, mock_event_router: Mock, mock_provider_factory: Mock):
    patched = AsyncMock(spec=LifecycleDependencies)
    patched.storage_builder = mock_storage_builder
    patched.tenant_event_router = mock_event_router
    patched.provider_factory = mock_provider_factory
    patched.check_credits = Mock(return_value=None)
    with patch("protocol.api._mcp_utils.lifecycle_dependencies", return_value=patched):
        yield patched


@pytest.fixture
def mock_authenticated_tenant():
    mock_tenant_data = TenantData(uid=123, slug="test-tenant")
    with patch("protocol.api._mcp_utils._authenticated_tenant", return_value=mock_tenant_data):
        yield mock_tenant_data


@pytest.fixture
async def test_mcp_client(mock_authenticated_tenant: Mock, mock_lifecycle_deps: Mock):
    from protocol.api._mcp import mcp

    async with Client(mcp) as mcp_client:
        yield mcp_client


@pytest.fixture
def mock_playground_service():
    mock = AsyncMock(spec=PlaygroundService)
    with patch("protocol.api._mcp_utils.playground_service", return_value=mock):
        yield mock


class TestAddVersionsToExperiment:
    async def test_sanitized_id(self, test_mcp_client: Client[Any], mock_playground_service: Mock):
        payload = {
            "experiment_id": "anotherai/experiment/01997d25-b859-7066-681c-c11fe1250b89",
            "version": {"model": "gpt-4o-mini-latest"},
        }

        res = await test_mcp_client.call_tool("add_versions_to_experiment", payload)
        assert res
        mock_playground_service.add_versions_to_experiment.assert_awaited_once_with(
            "01997d25-b859-7066-681c-c11fe1250b89",
            VersionRequest(model="gpt-4o-mini-latest"),
            None,
        )

    async def test_with_response_format(self, test_mcp_client: Client[Any], mock_experiment_storage: Mock):
        payload = {
            "experiment_id": "01997d25-b859-7066-681c-c11fe1250b89",
            "version": '{\n  "model": "gpt-4o-mini-latest",\n  "prompt": [\n    {\n      "role": "system",\n      "content": "You are an expert in animals. Find the animal in the image"\n    },\n    {\n      "role": "user", \n      "content": [\n        {\n          "type": "image_url",\n          "image_url": {\n            "url": "{{image_url}}"\n          }\n        }\n      ]\n    }\n  ],\n  "response_format": {\n    "json_schema": {\n      "name": "AnimalClassificationOutput",\n      "schema": {\n        "type": "object",\n        "properties": {\n          "animals": {\n            "type": "array",\n            "items": {\n              "type": "object",\n              "properties": {\n                "location": {\n                  "type": "string",\n                  "enum": ["top", "bottom", "left", "right", "center"]\n                },\n                "name": {\n                  "type": "string"\n                },\n                "subspecies": {\n                  "type": "string"\n                },\n                "latin_name": {\n                  "type": "string"\n                },\n                "endangered_level": {\n                  "type": "string",\n                  "enum": ["least concern", "near threatened", "vulnerable", "endangered", "critically endangered", "extinct in the wild", "extinct"]\n                }\n              },\n              "required": ["location", "name", "endangered_level"]\n            }\n          }\n        },\n        "required": ["animals"]\n      }\n    }\n  }\n}',
            "overrides": [
                {
                    "model": "gpt-5-nano-2025-08-07",
                },
            ],
        }
        mock_experiment_storage.get_experiment.return_value = fake_experiment()
        mock_experiment_storage.add_versions.return_value = ["01997d25-b859-7066-681c-c11fe1250b89"]

        res = await test_mcp_client.call_tool("add_versions_to_experiment", payload)
        assert res

        mock_experiment_storage.add_versions.assert_awaited_once()
        added_versions: list[Version] = mock_experiment_storage.add_versions.call_args[0][1]
        assert len(added_versions) == 2

        first = added_versions[0]

        for version in added_versions[1:]:
            assert version.model_dump(exclude={"id", "model"}) == first.model_dump(exclude={"id", "model"})

        assert added_versions[0].model == "gpt-4o-mini-latest"
        assert added_versions[1].model == "gpt-5-nano-2025-08-07"

        # Check input variables
        assert first.input_variables_schema == {
            "type": "object",
            "properties": {
                "image_url": {},
            },
        }
        assert first.output_schema
        assert first.output_schema.json_schema == {
            "type": "object",
            "properties": {
                "animals": ANY,
            },
            "required": ["animals"],
        }


class TestGetExperiment:
    async def test_sanitized_id(self, test_mcp_client: Client[Any], mock_experiment_storage: Mock):
        payload = {
            "id": "anotherai/experiment/01997d25-b859-7066-681c-c11fe1250b89",
        }
        mock_experiment_storage.list_experiment_completions.return_value = []
        mock_experiment_storage.get_experiment.return_value = fake_experiment()
        res = await test_mcp_client.call_tool("get_experiment", payload)
        assert res
        mock_experiment_storage.get_experiment.assert_called_once_with(
            "01997d25-b859-7066-681c-c11fe1250b89",
            include={"outputs", "annotations", "versions", "inputs"},
            version_ids=None,
            input_ids=None,
        )

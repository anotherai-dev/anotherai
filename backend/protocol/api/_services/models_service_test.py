"""Test for models service to verify API vs MCP response differences."""

import pytest

from protocol.api._services import models_service


@pytest.mark.asyncio
async def test_list_models_api_includes_icon_url():
    """Test that API response includes icon_url field."""
    models = await models_service.list_models()

    assert len(models) > 0, "Should return at least one model"

    # Check that all models have icon_url field with non-empty values
    for model in models:
        assert hasattr(model, "icon_url"), f"Model {model.id} should have icon_url field"
        assert model.icon_url, f"Model {model.id} should have non-empty icon_url"
        assert model.icon_url.startswith("http"), f"Model {model.id} icon_url should be a valid URL"


@pytest.mark.asyncio
async def test_list_models_mcp_excludes_icon_url():
    """Test that MCP response excludes icon_url field by setting it to empty string."""
    models = await models_service.list_models_mcp()

    assert len(models) > 0, "Should return at least one model"

    # Check that all models have icon_url field set to empty string
    for model in models:
        assert hasattr(model, "icon_url"), f"Model {model.id} should have icon_url field"
        assert model.icon_url == "", f"Model {model.id} icon_url should be empty string for MCP"


@pytest.mark.asyncio
async def test_api_and_mcp_have_same_models_except_icon_url():
    """Test that API and MCP responses have the same models except for icon_url."""
    api_models = await models_service.list_models()
    mcp_models = await models_service.list_models_mcp()

    assert len(api_models) == len(mcp_models), "API and MCP should return same number of models"

    # Sort models by ID for comparison
    api_models_sorted = sorted(api_models, key=lambda m: m.id)
    mcp_models_sorted = sorted(mcp_models, key=lambda m: m.id)

    for api_model, mcp_model in zip(api_models_sorted, mcp_models_sorted, strict=False):
        # Check that all fields are the same except icon_url
        assert api_model.id == mcp_model.id
        assert api_model.display_name == mcp_model.display_name
        assert api_model.supports == mcp_model.supports
        assert api_model.pricing == mcp_model.pricing
        assert api_model.release_date == mcp_model.release_date
        assert api_model.reasoning == mcp_model.reasoning
        assert api_model.context_window == mcp_model.context_window
        assert api_model.speed_index == mcp_model.speed_index

        # Verify icon_url difference
        assert api_model.icon_url != "", f"API model {api_model.id} should have icon_url"
        assert mcp_model.icon_url == "", f"MCP model {mcp_model.id} should have empty icon_url"


@pytest.mark.asyncio
async def test_mcp_response_serialization_no_icon_url():
    """Test that MCP response when serialized to dict has empty icon_url."""
    models = await models_service.list_models_mcp()

    assert len(models) > 0, "Should return at least one model"

    # Check serialized form
    for model in models:
        model_dict = model.model_dump()
        assert "icon_url" in model_dict, "Serialized model should have icon_url field"
        assert model_dict["icon_url"] == "", f"Serialized MCP model {model.id} should have empty icon_url"

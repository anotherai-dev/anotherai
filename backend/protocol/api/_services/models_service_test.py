import pytest

from core.domain.models.model_data import FinalModelData
from core.domain.models.model_provider_data import ModelProviderData, ModelProviderTextPrice
from core.domain.models.models import Model as ModelID
from protocol.api._services import models_service


@pytest.fixture
def mock_model_data():
    """Create mock model data for testing."""
    return {
        ModelID.CLAUDE_3_5_HAIKU_LATEST: FinalModelData(
            display_name="Claude 3.5 Haiku",
            icon_url="https://example.com/haiku.png",
            providers=[
                (
                    "anthropic",
                    ModelProviderData(
                        anthropic_model_id="claude-3-5-haiku",
                        text_price=ModelProviderTextPrice(
                            prompt_cost_per_token=0.000001,
                            completion_cost_per_token=0.000005,
                        ),
                    ),
                ),
            ],
            release_date="2024-11-01",
            speed_index=85,
        ),
        ModelID.GPT_4O_MINI: FinalModelData(
            display_name="GPT-4o mini",
            icon_url="https://example.com/gpt4o-mini.png",
            providers=[
                (
                    "openai",
                    ModelProviderData(
                        openai_model_id="gpt-4o-mini",
                        text_price=ModelProviderTextPrice(
                            prompt_cost_per_token=0.00000015,
                            completion_cost_per_token=0.0000006,
                        ),
                    ),
                ),
            ],
            release_date="2024-07-18",
            speed_index=90,
        ),
    }


@pytest.mark.asyncio
async def test_list_models_returns_models():
    """Test that list_models returns a list of Model objects."""
    models = await models_service.list_models()

    assert isinstance(models, list)
    assert len(models) > 0

    # Check first model has expected structure
    first_model = models[0]
    assert hasattr(first_model, "id")
    assert hasattr(first_model, "display_name")
    assert hasattr(first_model, "supports")
    assert hasattr(first_model, "pricing")
    assert hasattr(first_model, "release_date")
    assert hasattr(first_model, "context_window")
    assert hasattr(first_model, "speed_index")

    # Verify icon_url is NOT in the model
    assert not hasattr(first_model, "icon_url")


@pytest.mark.asyncio
async def test_list_models_no_icon_url():
    """Test that list_models does not include icon_url in the response."""
    models = await models_service.list_models()

    # Check that none of the models have icon_url
    for model in models:
        assert not hasattr(model, "icon_url")

        # Also check the dict representation doesn't contain icon_url
        model_dict = model.model_dump()
        assert "icon_url" not in model_dict

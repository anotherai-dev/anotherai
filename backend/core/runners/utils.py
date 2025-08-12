from typing import Any

from core.domain.exceptions import InvalidRunOptionsError
from core.domain.models.model_data_mapping import get_model_id
from core.domain.models.models import Model
from core.domain.models.providers import Provider
from core.utils.strings import clean_unicode_chars


def sanitize_model_and_provider(
    model_str: str | None,
    provider_str: str | None,
) -> tuple[Model, Provider | None]:
    if not model_str:
        # We should never be here so we capture
        raise InvalidRunOptionsError("Model is required", capture=True)

    try:
        model = get_model_id(model_str)
    except ValueError as e:
        raise InvalidRunOptionsError(f"Model {model_str} is not valid") from e

    try:
        provider = Provider(provider_str) if provider_str else None
    except ValueError as e:
        raise InvalidRunOptionsError(f"Provider {provider_str} is not valid") from e

    return model, provider


def cleanup_provider_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: cleanup_provider_json(v) for k, v in obj.items()}  # pyright: ignore[reportUnknownVariableType]
    if isinstance(obj, list):
        return [cleanup_provider_json(v) for v in obj]  # pyright: ignore[reportUnknownVariableType]
    if isinstance(obj, str):
        return clean_unicode_chars(obj)
    return obj

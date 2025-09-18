# pyright: reportPrivateUsage=false

from typing import Any

import pytest

from core.domain.exceptions import BadRequestError
from protocol.api._api_models import Version
from protocol.api._services.playground_service import _validate_version, _version_with_override


class TestValidateVersion:
    @pytest.mark.parametrize(
        "model_id",
        [
            # Use a few known-good ids and aliases (see core/domain/models/models.py)
            "gpt-4o-2024-05-13",
            "gpt-4o-mini-latest",
            "gpt-4.1-mini-latest",
        ],
    )
    def test_accepts_valid_models(self, model_id: str):
        v = Version(model=model_id)
        out = _validate_version(v)
        assert out.model  # normalized to canonical id or kept as is

    @pytest.mark.parametrize(
        "model_id",
        [
            "non-existent-model",
            "",
        ],
    )
    def test_rejects_invalid_models(self, model_id: str):
        v = Version(model=model_id)
        with pytest.raises(BadRequestError, match="Invalid model"):
            _validate_version(v)


class TestVersionWithOverride:
    def test_valid_override_updates_fields(self):
        base = Version(model="gpt-4o-mini-latest", temperature=0.1, top_p=None)
        override = {"temperature": 0.5, "top_p": 0.9}
        out = _version_with_override(base, override)
        assert out.temperature == 0.5
        assert out.top_p == 0.9
        # model is preserved
        assert out.model

    @pytest.mark.parametrize(
        "override",
        [
            pytest.param({"tools": {"not": "a list"}}, id="wrong type for tools"),  # wrong type for tools
            pytest.param({"max_output_tokens": "abc"}, id="wrong type for int"),  # wrong type for int
            pytest.param({"temperature": "hot"}, id="wrong type for float"),  # wrong type for float
            pytest.param({"not_a_field": "value"}, id="wrong field"),  # wrong field
        ],
    )
    def test_invalid_override_raises(self, override: dict[str, Any]):
        base = Version(model="gpt-4o-mini-latest")
        with pytest.raises(BadRequestError, match="Invalid version with override"):
            _version_with_override(base, override)

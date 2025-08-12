# pyright: reportPrivateUsage=false
import pytest
from pydantic import BaseModel

from core.logs._pydantic_processor import _serialize_pydantic_model, pydantic_processor


class _SampleModel(BaseModel):
    id: int
    name: str | None = None


def test_serialize_pydantic_model_excludes_none_fields():
    model = _SampleModel(id=1, name=None)
    assert _serialize_pydantic_model(model) == {"id": 1}


def test_pydantic_processor_serializes_single_model_value():
    model = _SampleModel(id=42, name=None)
    event = {"model": model, "other": 123}
    result = pydantic_processor(None, "info", event)
    assert result["model"] == {"id": 42}
    assert result["other"] == 123


@pytest.mark.parametrize("factory", [list, tuple])
def test_pydantic_processor_serializes_sequence_of_models(factory):
    models = factory([_SampleModel(id=1), _SampleModel(id=2, name="x")])
    event = {"models": models}
    result = pydantic_processor(None, "info", event)
    assert isinstance(result["models"], list)
    # Order preserved for list/tuple
    assert result["models"] == [{"id": 1}, {"id": 2, "name": "x"}]


def test_pydantic_processor_converts_set_to_list_and_keeps_values():
    # Sets of BaseModel are invalid because BaseModel is unhashable; use non-models here
    values_set = {"a", "b"}
    event = {"values": values_set}
    result = pydantic_processor(None, "info", event)
    assert isinstance(result["values"], list)
    assert sorted(result["values"]) == ["a", "b"]


def test_pydantic_processor_handles_mixed_sequence_items():
    mixed = [_SampleModel(id=3), 7, "x"]
    event = {"items": mixed}
    result = pydantic_processor(None, "info", event)
    assert result["items"] == [{"id": 3}, 7, "x"]


def test_pydantic_processor_leaves_dicts_and_scalars_untouched():
    event = {"data": {"x": 1}, "count": 5, "flag": True}
    result = pydantic_processor(None, "info", event)
    assert result["data"] == {"x": 1}
    assert result["count"] == 5
    assert result["flag"] is True

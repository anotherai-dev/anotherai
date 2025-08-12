import json
from typing import Any

import pytest
from pydantic import BaseModel

from .previews import compute_preview


class _Hello(BaseModel):
    hello: str = "world"

    class Nested(BaseModel):
        nested: str = "value"

    nested: Nested = Nested()

    a_list: list[float] | None = None


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (_Hello(), 'hello: "world", nested: {nested: "value"}'),
        (_Hello(hello="world\n"), 'hello: "world ", nested: {nested: "value"}'),
        ({"hello": "1", "b": None}, 'hello: "1", b: null'),
        (_Hello(a_list=[1, 2, 3.545]), 'hello: "world", nested: {nested: "value"}, a_list: [1, 2, 3.54]'),
    ],
)
def test_compute_preview(model: BaseModel, expected: str):
    assert compute_preview(model) == expected


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        pytest.param(_Hello(), 'hello: "wo...', id="hello_world"),
    ],
)
def test_compute_preview_limit(model: BaseModel, expected: str):
    assert compute_preview(model, 10) == expected


def test_compute_preview_default_limit():
    d = {
        "a": "a" * 256,
    }
    assert len(json.dumps(d)) > 255, "sanity check"
    assert len(compute_preview(d)) == 255 + 3  # "..."


@pytest.mark.parametrize(
    ("file_payload", "expected"),
    [
        pytest.param(
            {"url": "https://example.com/image.png", "content_type": "image/png"},
            "[[img:https://example.com/image.png]]...",
            id="image_url",
        ),
        pytest.param(
            {"url": "data:base64,...", "content_type": "image/png", "storage_url": "https://example.com/image.png"},
            "[[img:https://example.com/image.png]]...",
            id="url_with_data",
        ),
        pytest.param(
            {"url": 10, "content_type": "image/png"},
            "{url...",  # truncated
            id="not_a_file",
        ),
    ],
)
def test_compute_preview_file(file_payload: dict[str, Any], expected: str):
    assert compute_preview({"file": file_payload}, max_len=10) == "file: " + expected

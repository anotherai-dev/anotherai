from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import BaseModel

from ._ch_field_utils import data_and_columns, validate_fixed, zip_columns


class TestValidateFixed:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("10", "10"),
            ("100001", "10000"),
            ("abcde", "abcde"),
            # Last character is stripped entirely since it makes the string too long
            # when encoded
            ("abcdéa", "abcd"),
        ],
    )
    def test_not_raise(self, value: str, expected: str):
        assert validate_fixed(size=5, log_name="bla").func(value) == expected  # pyright: ignore[reportCallIssue]


class TestDataAndColumns:
    def test_with_nested(self):
        class NestedModel(BaseModel):
            class SubModel(BaseModel):
                a: str
                b: int

            sub: list[SubModel]
            hello: str

        model = NestedModel(sub=[NestedModel.SubModel(a="a", b=1), NestedModel.SubModel(a="b", b=2)], hello="hello")
        data, columns = data_and_columns(model)
        assert data == [["a", "b"], [1, 2], "hello"]
        assert columns == ["sub.a", "sub.b", "hello"]


class TestZipColumns:
    def test_with_nested(self):
        rows: Sequence[Sequence[Any]] = [[["d", "f"], [1, 2], "hello"]]
        column_names = ["sub.a", "sub.b", "hello"]
        nested_fields = {"sub"}
        actual = zip_columns(column_names, rows, nested_fields=nested_fields)
        assert actual == [{"sub": [{"a": "d", "b": 1}, {"a": "f", "b": 2}], "hello": "hello"}]

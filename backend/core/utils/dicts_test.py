import re
from typing import Any

import pytest
from pydantic import BaseModel

from .dicts import (
    InvalidKeyPathError,
    TwoWayDict,
    blacklist_keys,
    deep_merge,
    delete_at_keypath,
    get_at_keypath_str,
    remove_nulls,
    set_at_keypath_str,
)


class _Dummy(BaseModel):
    a: int = 1

    class Inner(BaseModel):
        b: dict[str, int] = {"c": 3}

    inner: Inner = Inner()

    inners: list[Inner] = [Inner(), Inner()]


@pytest.mark.parametrize(
    ("dict1", "dict2", "expected_result"),
    [
        # Test merging flat dictionaries with no overlap
        ({"a": 1}, {"b": 2}, {"a": 1, "b": 2}),
        # Test merging flat dictionaries with overlap; dict2 should override dict1
        ({"a": 1}, {"a": 2}, {"a": 2}),
        # Test merging nested dictionaries with no overlap
        ({"a": {"x": 1}}, {"b": {"y": 2}}, {"a": {"x": 1}, "b": {"y": 2}}),
        # Test merging nested dictionaries with overlap; inner values from dict2 should override those from dict1
        ({"a": {"x": 1, "y": 2}}, {"a": {"y": 3, "z": 4}}, {"a": {"x": 1, "y": 3, "z": 4}}),
        # Test merging with one empty dictionary
        ({}, {"a": 2}, {"a": 2}),
        # Test merging where dict2 is empty; result should be identical to dict1
        ({"a": 1}, {}, {"a": 1}),
        # Test deep merging with multiple levels of nesting
        ({"a": {"x": {"y": 1}}}, {"a": {"x": {"y": 2, "z": 3}}, "b": 2}, {"a": {"x": {"y": 2, "z": 3}}, "b": 2}),
    ],
)
def test_deep_merge(dict1: dict[str, Any], dict2: dict[str, Any], expected_result: dict[str, Any]):
    assert deep_merge(dict1, dict2) == expected_result


@pytest.mark.parametrize(
    ("d", "key_path", "value", "expected"),
    [
        ({"a": 1}, "b", 2, {"a": 1, "b": 2}),  # Test setting a key in a dict
        ({"a": {"b": 1}}, "a.c", 2, {"a": {"b": 1, "c": 2}}),  # Test setting a nested key in a dict
        ({"a": [{"b": 1}]}, "a.0.b", 2, {"a": [{"b": 2}]}),  # Test setting a nested key in a list of dicts
        ({}, "a.0", 1, {"a": [1]}),  # Test setting an array in an empty dict
        ([0, 1, 2], "1", 3, [0, 3, 2]),  # Test setting an index in a list
        ([0, {"a": 1}], "1.b", 2, [0, {"a": 1, "b": 2}]),  # Test setting a key in a dict inside a list
        ([0, [1, 2]], "1.1", 3, [0, [1, 3]]),  # Test setting an index in a list inside a list
        ([0, [1, 2]], "1.2", 3, [0, [1, 2, 3]]),  # Test setting an index beyond the end of a list
    ],
)
def test_set_keypath_str(d: Any, key_path: str, value: Any, expected: Any):
    set_at_keypath_str(d, key_path, value)
    assert d == expected


@pytest.mark.parametrize(
    ("d", "key_path"),
    [
        ({"a": "hello"}, "a.b"),  # Test setting a key in a string
    ],
)
def test_set_keypath_raise(d: Any, key_path: str):
    with pytest.raises(InvalidKeyPathError):
        set_at_keypath_str(d, key_path, 1)


@pytest.mark.parametrize(
    ("d", "key_path", "expected"),
    [
        ({"a": 1}, "a", 1),  # Test getting a key in a dict
        ({"a": {"b": 1}}, "a.b", 1),  # Test getting a nested key in a dict
        ({"a": [{"b": 1}]}, "a.0.b", 1),  # Test getting a nested key in a list of dicts
        ([0, 1, 2], "1", 1),  # Test getting an index in a list
        ([0, {"a": 1}], "1.a", 1),  # Test getting a key in a dict inside a list
        ([0, [1, 2]], "1.1", 2),  # Test getting an index in a list inside a list
        ([0, [1, 2]], "1.-2", 1),  # Test getting an index in a list inside a list with a negative index
        (_Dummy(), "a", 1),  # Test getting a nested key in a nested model
        (_Dummy(), "inners.0.b.c", 3),  # Test getting a nested key in a nested model inside a list
    ],
)
def test_get_keypath_str(d: Any, key_path: str, expected: Any):
    assert expected == get_at_keypath_str(d, key_path)


@pytest.mark.parametrize(
    ("d", "key_path"),
    [
        ({"a": 1}, "b"),  # Test getting a non-existent key in a dict
        ({"a": {"b": 1}}, "a.c"),  # Test getting a non-existent nested key in a dict
        ({"a": [{"b": 1}]}, "a.0.c"),  # Test getting a non-existent nested key in a list of dicts
        ([0, 1, 2], "3"),  # Test getting an index beyond the end of a list
        ([0, {"a": 1}], "1.b"),  # Test getting a non-existent key in a dict inside a list
        ([0, [1, 2]], "1.2"),  # Test getting an index beyond the end of a list inside a list
        (_Dummy(), "inner.a"),  # Test getting a nested key in a nested model
        (_Dummy(), "inners.0.b.d"),  # Test getting a non-existent nested key in a nested model inside a list
    ],
)
def test_get_keypath_raises(d: Any, key_path: str):
    with pytest.raises(KeyError):
        get_at_keypath_str(d, key_path)


class TestBlackListKeys:
    @pytest.mark.parametrize(
        ("d", "keys", "expected"),
        [
            # Test removing a key from a dict
            ({"a": 1, "b": 2}, ["a"], {"a": "...", "b": 2}),
            # Test removing a nested key from a dict
            ({"a": {"b": 1, "c": 2}}, ["b"], {"a": {"b": "...", "c": 2}}),
            # Test removing a nested key from a list of dicts
            (
                {"a": [{"b": 1}, {"b": 2}]},
                ["b"],
                {"a": [{"b": "..."}, {"b": "..."}]},
            ),
            # Test removing multiple keys
            (
                {"a": 1, "b": 2, "c": 3},
                ["a", "c"],
                {"a": "...", "b": 2, "c": "..."},
            ),
            # Test removing keys with regex
            (
                {"a": 1, "ab": 2},
                [r"^a$"],
                {"a": "...", "ab": 2},
            ),
            # Does not crash if keys are not strings
            (
                {1: 1, "a": 2},
                [r"^a$"],
                {1: 1, "a": "..."},
            ),
        ],
    )
    def test_blacklist_keys(self, d: dict[str, Any], keys: list[str], expected: dict[str, Any]):
        assert blacklist_keys(d, "...", *[re.compile(k) for k in keys]) == expected


class TestTwoWayDict:
    def test_forward(self):
        d = TwoWayDict(("a", 1), ("b", 2))
        assert d["a"] == 1
        assert d["b"] == 2

    def test_backward(self):
        d = TwoWayDict(("a", 1), ("b", 2))
        assert d.backward(1) == "a"
        assert d.backward(2) == "b"

    def test_setitem(self):
        d = TwoWayDict(("a", 1), ("b", 2))
        d["c"] = 3
        assert d["c"] == 3
        assert d.backward(3) == "c"


class TestDeleteAtKeypath:
    @pytest.mark.parametrize(
        ("d", "key_path", "expected"),
        [
            ({"a": 1}, "a", {}),
            ({"a": {"b": 1}}, "a.b", {"a": {}}),
            ({"a": [{"b": 1}, {"b": 2}]}, "a.*.b", {"a": [dict[str, Any](), dict[str, Any]()]}),
            ({"a": [{"b": 1}, {"b": 2}]}, "a.0.b", {"a": [dict[str, Any](), {"b": 2}]}),
            ({"a": "b"}, "c.b", {"a": "b"}),  # Non existing key
            ({"a": ["b", "c"]}, "a.2", {"a": ["b", "c"]}),  # Non existing index
        ],
    )
    def test_delete_keypath(self, d: Any, key_path: str, expected: Any):
        assert delete_at_keypath(d, key_path.split(".")) == expected


class TestRemoveNulls:
    @pytest.mark.parametrize(
        ("d", "expected"),
        [
            pytest.param({"a": 1, "b": None}, {"a": 1}, id="dict with None is removed"),
            pytest.param({"a": {"b": 1, "c": None}}, {"a": {"b": 1}}, id="nested dict with None is removed"),
            pytest.param({"a": [1, None]}, {"a": [1, None]}, id="list with None is preserved"),
        ],
    )
    def test_remove_nulls(self, d: Any, expected: Any):
        assert remove_nulls(d) == expected

import contextlib
import re
from collections.abc import Mapping, Sequence
from typing import Any, TypeVar, cast

T = TypeVar("T", bound=dict[Any, Any])


def deep_merge(dict1: T, dict2: T) -> T:
    """
    Recursively merge two dictionaries, including nested dictionaries.
    Values from dict2 will override those from dict1 in case of conflicts.
    """
    result = dict1.copy()  # Start with dict1's keys and values
    for key, value in dict2.items():
        # If the value is a dictionary, perform a deep merge
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)  # pyright: ignore [reportUnknownArgumentType]
        else:
            # Otherwise, use the value from dict2
            result[key] = value
    return cast(T, result)


class InvalidKeyPathError(ValueError):
    def __init__(self, msg: str, extras: dict[str, Any]):
        super().__init__(msg)
        self.extras: dict[str, Any] = extras


def _set_keypath_inner[T](
    d: T,
    keys: list[int | str],
    value: Any,
) -> T:
    if not keys:
        return value

    root = d
    key = keys[0]

    # Setting by index
    if isinstance(key, int):
        if root is None:
            root = []
        elif isinstance(root, dict):
            root = cast(dict[str, Any], root)
            # key probably got converted by mistake
            root[f"{key}"] = _set_keypath_inner(root.get(f"{key}", None), keys[1:], value)
            return cast(T, root)
        elif not isinstance(root, list):
            raise InvalidKeyPathError(f"Cannot set keypath {key} on non-list object", extras={"root": root})

        root = cast(list[Any], root)

        if key < 0:
            key = max(0, len(root) + key + 1)

        if len(root) <= key:
            root.extend([None for _ in range(key - len(root) + 1)])
        root[key] = _set_keypath_inner(root[key], keys[1:], value)
        return cast(T, root)

    # Setting by key
    if root is None:
        root = {}
    elif not isinstance(root, dict):
        raise InvalidKeyPathError(f"Cannot set keypath '{key}' on non-dict object", extras={"root": root})
    root = cast(dict[str, Any], root)
    root[key] = _set_keypath_inner(root.get(key), keys[1:], value)

    return cast(T, root)


KeyPath = list[str | int]


def split_keys(key_path: str) -> KeyPath:
    def _convert_key(key: str) -> str | int:
        try:
            return int(key)
        except ValueError:
            return key

    return [_convert_key(k) for k in key_path.split(".")]


def set_at_keypath[T](
    d: T,
    key_path: KeyPath,
    value: Any,
) -> T:
    return _set_keypath_inner(d, key_path, value)


def set_at_keypath_str[T](
    d: T,
    key_path: str,
    value: Any,
) -> T:
    keys = split_keys(key_path)
    return _set_keypath_inner(d, keys, value)


def get_at_keypath_str(d: Any, key_path: str) -> Any:
    return get_at_keypath(d, split_keys(key_path))


def get_at_keypath(d: Any, key_path: KeyPath) -> Any:
    for key in key_path:
        if isinstance(d, dict):
            d = cast(dict[str | int, Any], d)[key]
        elif isinstance(d, list):
            if not isinstance(key, int):
                raise KeyError(f"Cannot get keypath '{key}' on list object")
            try:
                d = cast(list[Any], d)[key]
            except IndexError as e:
                raise KeyError(f"Index {key} out of range") from e
        elif isinstance(key, str):
            try:
                d = getattr(d, key)
            except AttributeError as e:
                raise KeyError(f"Cannot get keypath '{key}' on object {type(d)})") from e
        else:
            raise KeyError(f"Cannot get keypath '{key}' on non-dict or list object")
    return d


def blacklist_keys(d: Any, replace_with: str, *keys: re.Pattern[str]) -> Any:
    """Recursively remove keys from a dictionary that match any of the provided patterns."""

    def _maybe_replace_value(k: Any, v: Any) -> Any:
        if isinstance(k, str) and any(p.match(k) for p in keys):
            return replace_with
        return _blacklist_keys_inner(v)

    def _blacklist_keys_inner(d: Any) -> Any:
        if isinstance(d, dict):
            return {k: _maybe_replace_value(k, v) for k, v in d.items()}  # pyright: ignore [reportUnknownVariableType]
        if isinstance(d, list):
            return [_blacklist_keys_inner(v) for v in d]  # pyright: ignore [reportUnknownVariableType]
        return d

    return _blacklist_keys_inner(d)


class TwoWayDict[K1, K2]:
    def __init__(self, *values: tuple[K1, K2]):
        self._forward: dict[K1, K2] = dict(values)
        self._backward: dict[K2, K1] = {v2: v1 for v1, v2 in values}

    def __getitem__(self, key: K1) -> K2:
        return self._forward[key]

    def backward(self, key: K2) -> K1:
        return self._backward[key]

    def __setitem__(self, key: K1, value: K2):
        self._forward[key] = value
        self._backward[value] = key

    def __contains__(self, key: K1) -> bool:
        return key in self._forward or key in self._backward

    def in_forward_keys(self, key: K1) -> bool:
        return key in self._forward

    @property
    def forward_map(self) -> Mapping[K1, K2]:
        return self._forward

    @property
    def backward_map(self) -> Mapping[K2, K1]:
        return self._backward


def _delete_at_keypath_in_list(root: list[Any], keys: Sequence[int | str]) -> list[Any]:
    key = keys[0]
    final_key = len(keys) == 1
    if key == "*":
        for i in range(len(root)):
            root[i] = delete_at_keypath(root[i], keys[1:])
        return root
    if not isinstance(key, int):
        try:
            key = int(key)
        except ValueError as e:
            raise InvalidKeyPathError(f"Cannot delete keypath '{key}' on non-list object", extras={"root": root}) from e
    if final_key:
        with contextlib.suppress(IndexError):
            root.pop(key)
        return root
    root[key] = delete_at_keypath(root[key], keys[1:])
    return root


def _delete_at_keypath_in_dict(root: dict[str, Any], keys: Sequence[int | str]) -> dict[str, Any]:
    key = keys[0]
    final_key = len(keys) == 1

    key = str(key)
    if final_key:
        root.pop(key, None)
        return root
    with contextlib.suppress(KeyError):
        root[key] = delete_at_keypath(root[key], keys[1:])
    return root


def delete_at_keypath[T](d: T, keys: Sequence[int | str]) -> T:
    if not keys:
        return d
    if not d:
        return d

    if isinstance(d, list):
        return _delete_at_keypath_in_list(d, keys)  # pyright: ignore [reportUnknownArgumentType]
    if isinstance(d, dict):
        return _delete_at_keypath_in_dict(d, keys)  # pyright: ignore [reportUnknownArgumentType]

    return d


def exclude_keys(d: dict[str, Any], keys: set[str]) -> dict[str, Any]:
    """Returns a copy of the dictionary without the keys in the set."""
    return {k: v for k, v in d.items() if k not in keys}


def remove_nulls(d: Any) -> Any:
    """Returns a copy of the dictionary without the keys in the set."""
    if isinstance(d, dict):
        return {k: remove_nulls(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [remove_nulls(v) for v in d]
    return d

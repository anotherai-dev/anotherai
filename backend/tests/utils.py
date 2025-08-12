import json
import os
import warnings
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest


def root_dir() -> Path:
    return Path(__file__).parent.parent.parent


def fixture_path(*components: str, relative: bool = False) -> str:
    p = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        *components,
    )
    if relative:
        return os.path.relpath(p)
    return p


def fixture_bytes(*components: str) -> bytes:
    with open(fixture_path(*components), "rb") as f:
        return f.read()


def fixture_text(*components: str) -> str:
    with open(fixture_path(*components)) as f:
        return f.read()


def fixtures_json(*components: str) -> Any:
    with open(fixture_path(*components)) as f:
        return json.load(f)


@contextmanager
def ignore_deprecation():
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        yield


class _AsyncGeneratorMock:
    def __init__(self, arr: Any):
        self.idx = 0
        self.arr = arr

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            obj = self.arr[self.idx]
        except IndexError:
            raise StopAsyncIteration from None
        self.idx += 1
        return obj


def mock_aiter(*args: Any):
    return _AsyncGeneratorMock(args)


def request_json_body(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content)


def remove_none(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {k: remove_none(v) for k, v in payload.items() if v is not None}  # type: ignore  # noqa: PGH003
    if isinstance(payload, list):
        return [remove_none(v) for v in payload]  # type: ignore # noqa: PGH003
    return payload


def fixtures_stream_hex(category: str, name: str) -> list[bytes]:
    """Load stream fixture data from a text file with one hex-encoded string per line."""
    with open(fixture_path(category, f"{name}")) as f:
        return [
            eval(line.strip())  # This will evaluate the full b'...' string  # noqa: S307
            for line in f
            if line.strip()
        ]


def fixtures_stream(*components: str) -> list[bytes]:
    """Load stream fixture data from a text file with one string per line."""
    with open(fixture_path(*components), "rb") as f:
        full_text = f.read().split(b"\n\n")
        return [line + b"\n\n" for line in full_text if line]


def cut_string(s: str, cut_idxs: list[int]):
    """Cut a string json into chunks"""

    idx = cut_idxs[0]
    yield s[:idx]
    for i in cut_idxs[1:]:
        yield s[idx:i]
        idx = i
    yield s[idx:]


def cut_json(j: dict[str, Any], cut_idxs: list[int]):
    """Cut a stringified json into chunks of json objects"""
    json_str = json.dumps(j)
    return cut_string(json_str, cut_idxs)


def approx(value: float, abs: float | None = None, rel: float | None = None):
    return pytest.approx(value, abs=abs, rel=rel)  # pyright: ignore reportUnknownArgumentType

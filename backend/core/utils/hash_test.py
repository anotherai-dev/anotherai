import pytest

from .hash import hash_object, hash_string, is_hash_32


def test_hash_object() -> None:
    obj = {"actual": {"category": "A"}, "input": {"value": "sugar"}}

    assert hash_object(obj) == "13f9f95cf06f1be8e9ececf83c4e7931"

    obj = {"input": {"value": "sugar"}, "actual": {"category": "A"}}

    assert hash_object(obj) == "13f9f95cf06f1be8e9ececf83c4e7931"


@pytest.mark.parametrize(
    ("val", "exp"),
    [
        pytest.param("13f9f95cf06f1be8e9ececf83c4e7931", True, id="hash"),
        pytest.param("13f9f95cf06f1be8e9ececf83c4e792", False, id="wrong len"),
        pytest.param("13f9f95cf06f1Be8e9ececf83c4e7931", False, id="wrong chars"),
        pytest.param(hash_string("bla"), True, id="hash string"),
        pytest.param(hash_object({"a": "b"}), True, id="hash object"),
    ],
)
def test_is_hash_32(val: str, exp: bool) -> None:
    assert is_hash_32(val) is exp

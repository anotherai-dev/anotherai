from .hash import hash_object


def test_hash_object() -> None:
    obj = {"actual": {"category": "A"}, "input": {"value": "sugar"}}

    assert hash_object(obj) == "13f9f95cf06f1be8e9ececf83c4e7931"

    obj = {"input": {"value": "sugar"}, "actual": {"category": "A"}}

    assert hash_object(obj) == "13f9f95cf06f1be8e9ececf83c4e7931"

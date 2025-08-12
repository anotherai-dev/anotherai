import datetime
import hashlib
import json
from typing import Any

from fastapi.types import IncEx
from pydantic import BaseModel


def hash_string(s: str, max_length: int = 32) -> str:
    """A simple hash function that returns a string of 32 characters.
    Not for security."""
    return hashlib.blake2s(s.encode("utf-8")).hexdigest()[:max_length]


class _CustomEncoder(json.JSONEncoder):
    """A custom json encoder that defaults to str representation for non-serializable objects."""

    def default(self, o: Any) -> Any:
        if isinstance(o, (datetime.date, datetime.datetime, datetime.time)):
            return o.isoformat()  # Convert dates and datetimes to ISO format strings
        try:
            return json.JSONEncoder.default(self, o)
        except TypeError:
            # Attempt to convert non-JSON-serializable objects to strings
            return str(o)


def hash_object(obj: Any) -> str:
    """Compute a hash of an object based on its json representation."""
    obj_str = json.dumps(obj, sort_keys=True, indent=None, separators=(",", ":"), cls=_CustomEncoder)
    # cannot use python hash function here because it is not
    # stable accross sessions. Using blake2s for speed
    return hash_string(obj_str)


def hash_model(
    model: BaseModel,
    exclude: IncEx | None = None,
    exclude_unset: bool = False,
    exclude_defaults: bool = False,
    exclude_none: bool = True,
) -> str:
    dumped = model.model_dump(
        mode="json",
        exclude=exclude,
        exclude_unset=exclude_unset,
        exclude_defaults=exclude_defaults,
        exclude_none=exclude_none,
    )
    # We should use model_dump_json here but sorting keys is not yet possible
    # https://github.com/pydantic/pydantic/issues/7424
    return hash_object(dumped)


def secure_hash(val: str) -> str:
    """A hash that can be used for security purposes."""
    return hashlib.sha256(val.encode()).hexdigest()

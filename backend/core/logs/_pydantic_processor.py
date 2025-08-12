from typing import Any

from pydantic import BaseModel
from structlog.types import EventDict


def _serialize_pydantic_model(value: Any):
    if isinstance(value, BaseModel):
        return value.model_dump(exclude_none=True)
    return value


def pydantic_processor(logger: Any, log_method: str, event_dict: EventDict) -> EventDict:
    for k, v in event_dict.items():
        if isinstance(v, BaseModel):
            event_dict[k] = v.model_dump(exclude_none=True)
        elif isinstance(v, (list, set, tuple)):
            event_dict[k] = [_serialize_pydantic_model(item) for item in v]
    return event_dict

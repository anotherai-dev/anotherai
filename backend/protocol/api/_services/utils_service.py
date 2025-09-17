from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from core.services.messages.messages_utils import json_schema_for_template
from core.utils.schema_sanitation import streamline_schema
from protocol.api._api_models import Message
from protocol.api._services.conversions import message_to_domain


class ExtractVariablesRequest(BaseModel):
    messages: list[Message]

    base_schema: dict[str, Any] | None = None


class ExtractVariablesResponse(BaseModel):
    json_schema: Mapping[str, Any] | None
    last_templated_index: int


def extract_variables_from_messages(request: ExtractVariablesRequest) -> ExtractVariablesResponse:
    json_schema, last_templated_index = json_schema_for_template(
        [message_to_domain(m) for m in request.messages],
        base_schema=streamline_schema(request.base_schema) if request.base_schema else None,
    )
    return ExtractVariablesResponse(
        json_schema=json_schema,
        last_templated_index=last_templated_index,
    )


class IDType(StrEnum):
    VERSION = "version"
    DEPLOYMENT = "deployment"
    EXPERIMENT = "experiment"
    COMPLETION = "completion"
    INPUT = "input"
    OUTPUT = "output"
    ANNOTATION = "annotation"

    def wrap(self, id: str) -> str:
        return f"anotherai/{self.value}/{id}"


def sanitize_id(value: str) -> tuple[IDType | None, str]:
    """Makes sure to remove extra prefixes from an id. Returns the type of the id if it is known"""
    final_id = value
    if final_id.startswith("anotherai/"):
        final_id = value[10:]
    splits = final_id.split("/", 2)
    if len(splits) != 2:
        # Not touching the ID. It might be a weird custom ID
        # Or a plain ID
        return None, value

    try:
        id_type = IDType(splits[0])
    except ValueError:
        # Same thing here, might be a custom ID
        return None, value

    return id_type, splits[1]

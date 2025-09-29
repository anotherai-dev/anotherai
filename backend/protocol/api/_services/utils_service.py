import re
from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from core.domain.exceptions import BadRequestError
from core.services.messages.messages_utils import json_schema_for_template
from core.utils.hash import HASH_REGEXP_32
from core.utils.schema_sanitation import streamline_schema
from core.utils.uuid import UUID7_REGEXP
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
    AGENT = "agent"

    def wrap(self, id: str) -> str:
        return f"anotherai/{self.value}/{id}"

    @property
    def expected_regexp(self) -> re.Pattern[str] | None:
        return _EXPECTED_ID_REGEXPS.get(self)


_EXPECTED_ID_REGEXPS = {
    IDType.VERSION: HASH_REGEXP_32,
    IDType.COMPLETION: UUID7_REGEXP,
    IDType.INPUT: HASH_REGEXP_32,
    IDType.OUTPUT: HASH_REGEXP_32,
}


def extract_id(value: str) -> tuple[IDType | None, str]:
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


def sanitize_id(value: str, expected_type: IDType) -> str:
    id_type, sanitized = extract_id(value)
    if id_type is not None and id_type != expected_type:
        raise BadRequestError(f"Invalid {expected_type.value} id: {value}")
    expected_regexp = expected_type.expected_regexp
    if expected_regexp and not expected_regexp.match(sanitized):
        raise BadRequestError(f"Invalid {expected_type.value} id: {value}")
    return sanitized


def sanitize_ids(ids: list[str], expected_type: IDType) -> set[str]:
    return {sanitize_id(id, expected_type) for id in ids}

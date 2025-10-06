from collections.abc import Mapping
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

from datetime import datetime

from pydantic import BaseModel

from core.domain.agent_input import SavedAgentInput
from core.storage.clickhouse._models._ch_field_utils import dump_messages, sanitize_metadata, stringify_json


class ClickhouseInput(BaseModel):
    tenant_uid: int
    input_id: str
    input_preview: str
    input_messages: str
    input_variables: str
    created_at: datetime
    agent_id: str
    metadata: dict[str, str]

    @classmethod
    def from_domain(cls, tenant_uid: int, input: SavedAgentInput):
        return cls(
            tenant_uid=tenant_uid,
            input_id=input.id,
            input_preview=input.preview,
            input_messages=dump_messages(input.messages),
            input_variables=stringify_json(input.variables),
            created_at=input.created_at,
            agent_id=input.agent_id,
            metadata=sanitize_metadata(input.metadata),
        )

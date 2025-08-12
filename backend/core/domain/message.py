import json
from collections.abc import Sequence
from enum import StrEnum, auto
from typing import Any, Literal

from pydantic import BaseModel, Field

from core.domain.file import File
from core.domain.tool_call import ToolCallRequest, ToolCallResult


# TODO: remove
class MessageDeprecated(BaseModel):
    class Role(StrEnum):
        SYSTEM = auto()
        USER = auto()
        ASSISTANT = auto()

    role: Role
    content: str
    files: Sequence[File] | None = None

    tool_call_requests: list[ToolCallRequest] | None = None
    tool_call_results: list[ToolCallResult] | None = None


class MessageContent(BaseModel):
    # Used for structured output
    object: dict[str, Any] | list[Any] | None = None
    text: str | None = None
    file: File | None = None
    tool_call_request: ToolCallRequest | None = None
    tool_call_result: ToolCallResult | None = None
    reasoning: str | None = None


MessageRole = Literal["system", "user", "assistant"]


class Message(BaseModel):
    # It would be nice to use strict validation since we know that certain roles are not allowed to
    # have certain content. Unfortunately it would mean that we would have oneOfs in the schema which
    # we currently do not handle client side
    role: MessageRole
    content: list[MessageContent]
    run_id: str | None = Field(
        default=None,
        description="The id of the run that generated this message. If available.",
    )

    @classmethod
    def with_text(cls, text: str, role: MessageRole = "user"):
        return cls(role=role, content=[MessageContent(text=text)])

    @classmethod
    def with_file_url(cls, url: str, role: MessageRole = "user"):
        return cls(role=role, content=[MessageContent(file=File(url=url))])

    @property
    def has_files(self) -> bool:
        return any(content.file for content in self.content)

    def to_deprecated(self) -> MessageDeprecated:
        # TODO: remove this method
        content = "\n\n".join(
            [*(c.text for c in self.content if c.text), *(json.dumps(c.object) for c in self.content if c.object)],
        )
        files = [c.file for c in self.content if c.file]
        tool_call_requests = [c.tool_call_request for c in self.content if c.tool_call_request]
        tool_call_results = [c.tool_call_result for c in self.content if c.tool_call_result]
        match self.role:
            case "system":
                return MessageDeprecated(role=MessageDeprecated.Role.SYSTEM, content=content)
            case "user":
                return MessageDeprecated(
                    role=MessageDeprecated.Role.USER,
                    content=content,
                    files=files,
                    tool_call_requests=tool_call_requests,
                    tool_call_results=tool_call_results,
                )
            case "assistant":
                return MessageDeprecated(
                    role=MessageDeprecated.Role.ASSISTANT,
                    content=content,
                    files=files,
                    tool_call_requests=tool_call_requests,
                )
        # We should never reach this point
        from core.domain.exceptions import InternalError

        raise InternalError("Unexpected message type")

    def file_iterator(self):
        for content in self.content:
            if content.file:
                yield content.file

    def tool_call_request_iterator(self):
        for content in self.content:
            if content.tool_call_request:
                yield content.tool_call_request

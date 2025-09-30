from collections.abc import Iterable
from typing import Any

from core.domain.exceptions import BadRequestError
from core.domain.file import FileKind
from core.domain.message import Message
from core.utils.schema_gen import schema_from_data
from core.utils.schema_sanitation import streamline_schema
from core.utils.templates import InvalidTemplateError, extract_variable_schema


def _ref_name(file_kind: FileKind | str | None) -> str:
    match file_kind:
        case FileKind.IMAGE:
            return "Image"
        case FileKind.AUDIO:
            return "Audio"
        case FileKind.DOCUMENT:
            return "File"
        case FileKind.PDF:
            return "PDF"
        case FileKind.ANY:
            return "File"
        case _:
            return "File"


class MessageTemplateError(InvalidTemplateError):
    def __init__(
        self,
        message: str,
        line_number: int | None,
        source: str | None = None,
        unexpected_char: str | None = None,
        message_index: int | None = None,
        content_index: int | None = None,
    ):
        super().__init__(message=message, line_number=line_number, source=source, unexpected_char=unexpected_char)
        self.message_index = message_index
        self.content_index = content_index

    def serialize_details(self) -> dict[str, Any]:
        return {
            "message_index": self.message_index,
            "content_index": self.content_index,
            **super().serialize_details(),
        }


def json_schema_for_template(
    messages: Iterable[Message],
    base_schema: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, int]:
    """Returns a json schema for template variables present in the messages and the index
    of the last templated message"""

    schema: dict[str, Any] = {}
    last_templated_index = -1

    for i, m in enumerate(messages):
        for j, c in enumerate(m.content):
            if c.file:
                templatable = c.file.templatable_content()
            elif c.text:
                templatable = c.text
            else:
                continue

            try:
                extracted, is_templated = extract_variable_schema(
                    templatable,
                    start_schema=schema,
                    use_types_from=base_schema,
                )
            except InvalidTemplateError as e:
                raise MessageTemplateError(
                    message=e.message,
                    line_number=e.line_number,
                    source=e.source,
                    unexpected_char=e.unexpected_char,
                    message_index=i,
                    content_index=j,
                ) from e
            if extracted:
                schema = extracted
            if is_templated:
                last_templated_index = i

    return streamline_schema(schema) if schema else None, last_templated_index


def json_schema_for_template_and_variables(
    messages: list[Message],
    variables: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, int]:
    if variables is None:
        # No body was sent with the request, so we treat the messages as a raw string
        return None, -1

    schema_from_input: dict[str, Any] | None = schema_from_data(variables) if variables else None
    schema_from_template, last_templated_index = json_schema_for_template(
        messages,
        base_schema=schema_from_input,
    )
    if not schema_from_template:
        if schema_from_input:
            raise BadRequestError("Input variables are provided but the messages do not contain a valid template")
        return None, -1
    if not schema_from_input:
        raise BadRequestError("Messages are templated but no input variables are provided")

    return streamline_schema(schema_from_template), last_templated_index

from collections.abc import Iterable
from typing import Any

from core.domain.file import FileKind
from core.domain.message import Message
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


def _add_file_to_schema(schema: dict[str, Any], template_key: str, file_kind: FileKind | str | None):
    splits = template_key.split(".")
    # We don't deal with complex stuff here. We just assume that at worst
    # The key is in a nested object. No array

    # We add the properties up to the last one
    for k in splits:
        properties = schema.setdefault("properties", {})
        schema = properties.setdefault(k, {})

    ref_name = _ref_name(file_kind)
    schema["$ref"] = f"#/$defs/{ref_name}"


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
            if c.file and (template_key := c.file.template_key()):
                # We have a template key so we should add the file to the schema
                _add_file_to_schema(schema, template_key, c.file.format)
                last_templated_index = i
            if not c.text:
                continue
            try:
                extracted, is_templated = extract_variable_schema(
                    c.text,
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

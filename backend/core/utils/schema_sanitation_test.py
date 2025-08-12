# pyright: reportPrivateUsage=false

import copy
from typing import Any

import pytest
from jsonschema import validate
from jsonschema.validators import validator_for
from pydantic import BaseModel, Field
from structlog.testing import LogCapture

from core.domain.consts import FILE_DEFS, FILE_REF_NAME
from core.utils.schema_sanitation import (
    _INTERNAL_DEFS,
    _build_internal_defs,
    _CircularReferenceError,
    _handle_internal_ref,
    _handle_one_any_all_ofs,
    _streamline_schema,
    get_file_format,
    schema_contains_file,
)
from core.utils.schema_sanitation import (
    streamline_schema as safe_streamline_schema,
)
from core.utils.schemas import strip_metadata
from tests.fixtures.agent_builder_output import AgentBuilderOutput
from tests.fixtures.schemas import (
    ALL_OF,
    ALL_OF_CLEANED,
    ANY_OF,
    ANY_OF_2,
    ANY_OF_2_CLEANED,
    ANY_OF_CLEANED,
    ONE_OF,
    ONE_OF_CLEANED,
    SCHEMA_WITH_EMPTY_DEFS,
    SCHEMA_WITH_EMPTY_DEFS_CLEANED,
    SCHEMA_WITH_REQUIRED_AS_FIELD_NAME,
    SCHEMA_WITH_REQUIRED_AS_FIELD_NAME_CLEANED,
    SIMPLE_SCHEMA,
    TYPE_ARRAY,
    TYPE_ARRAY_CLEANED,
)


def streamline_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Rewraps _streamline_schema to avoid catching exceptions"""
    return _streamline_schema(schema, _INTERNAL_DEFS)


class TestStreamlineSchema:
    def test_streamline_simple(self):
        schema = {
            "type": "object",
            "properties": {
                "custom_protected": {
                    "type": "string",
                },
            },
        }
        streamlined = streamline_schema(copy.deepcopy(schema))
        assert streamlined == schema

    def test_no_warning(self, log_capture: LogCapture):
        schema = {
            "$defs": {},
            "properties": {
                "focus_areas": {
                    "description": "Specific areas of risk to focus on during analysis (optional)",
                    "items": {
                        "type": "'string'",
                    },
                    "type": "array",
                },
                "loan_data": {
                    "$ref": "#/$defs/File",
                },
            },
            "type": "object",
        }

        _ = streamline_schema(schema)
        assert not log_capture.entries

    def test_model_array(self):
        class Model1(BaseModel):
            field: list[str] = Field(default_factory=list)

        class Model2(BaseModel):
            field: list[str] | None = None

        schema_1 = streamline_schema(Model1.model_json_schema())
        del schema_1["title"]
        schema_2 = streamline_schema(Model2.model_json_schema())
        del schema_2["title"]
        assert schema_1 == schema_2

    def test_nested_refs(self):
        class Model1(BaseModel):
            field: list[str] = Field(default_factory=list)

        class Model2(BaseModel):
            model_1: Model1

        schema_1 = strip_metadata(streamline_schema(Model2.model_json_schema()))
        assert schema_1 == {
            "type": "object",
            "properties": {
                "model_1": {
                    "type": "object",
                    "properties": {
                        "field": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["model_1"],
        }

    def test_field_order(self):
        """The required array may be different in the two schemas"""

        class Model1(BaseModel):
            field1: str
            field2: int

        class Model2(BaseModel):
            field2: int
            field1: str

        assert strip_metadata(Model1.model_json_schema()) != strip_metadata(Model2.model_json_schema()), "sanity check"

        schema_1 = strip_metadata(streamline_schema(Model1.model_json_schema()))
        schema_2 = strip_metadata(streamline_schema(Model2.model_json_schema()))
        assert schema_1 == schema_2

    def test_empty_examples_are_removed(self):
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {"field": {"type": "string", "examples": []}},
        }
        assert streamline_schema(schema) == {"type": "object", "properties": {"field": {"type": "string"}}}

    def test_empty_description_are_removed(self):
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {"field": {"type": "string", "description": ""}},
        }
        assert streamline_schema(schema) == {"type": "object", "properties": {"field": {"type": "string"}}}

    def test_empty_properties_are_removed(self):
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {"field": {"type": "object", "properties": {}}},
        }
        assert streamline_schema(schema) == {"type": "object", "properties": {"field": {"type": "object"}}}

    def test_streamlined_schemas_refs(self):
        schema1: dict[str, Any] = {
            "$defs": {
                "File": {},
            },
            "type": "object",
            "properties": {
                "field": {
                    "$ref": "#/$defs/File",
                    "format": "image",
                },
            },
        }
        schema2: dict[str, Any] = {
            "$defs": {
                "Image": {},
            },
            "type": "object",
            "properties": {
                "field": {
                    "$ref": "#/$defs/Image",
                },
            },
        }
        streamlined1 = streamline_schema(schema1)
        assert streamlined1 == streamline_schema(schema2)
        assert set(streamlined1["$defs"].keys()) == {"Image"}
        assert streamlined1["properties"] == {
            "field": {
                "$ref": "#/$defs/Image",
            },
        }

    def test_streamline_schema_any_of(self):
        schema = {
            "type": "object",
            "properties": {
                "field": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"},
                    ],
                },
            },
        }
        streamlined = streamline_schema(schema)
        assert streamlined == {
            "type": "object",
            "properties": {
                "field": {"type": "string"},
            },
        }

    def test_circular_reference_detection(self, log_capture: LogCapture):
        """Test that circular references are handled without infinite recursion."""
        # Create a simple schema with circular references
        schema = {
            "type": "object",
            "properties": {
                "parent": {"$ref": "#/$defs/Node"},
            },
            "$defs": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "child": {"$ref": "#/$defs/Node"},  # Circular reference
                    },
                },
            },
        }

        # This should not cause infinite recursion
        with pytest.raises(_CircularReferenceError):
            _ = streamline_schema(schema)

        assert safe_streamline_schema(schema) == schema
        assert not log_capture.entries

    def test_complex_case(self, log_capture: LogCapture):
        raw = AgentBuilderOutput.model_json_schema()
        with pytest.raises(_CircularReferenceError):
            _ = streamline_schema(raw)

        assert safe_streamline_schema(raw) == raw
        assert not log_capture.entries

    # TODO: remove internal defs tests since we don't use them anymore
    @pytest.mark.parametrize(
        ("schema", "expected"),
        [
            pytest.param(SIMPLE_SCHEMA, SIMPLE_SCHEMA, id="Simple"),
            # Test that the File schema is added to the definitions
            # pytest.param(FILE_SCHEMA, FILE_SCHEMA_EXPECTED, id="File"),
            # Test that the ChatMessage schema is added to the definitions
            # pytest.param(CHAT_MESSAGE_SCHEMA, CHAT_MESSAGE_SCHEMA_EXPECTED, id="ChatMessage"),
            # Test that anyOf is cleaned up
            pytest.param(ANY_OF, ANY_OF_CLEANED, id="any of"),
            pytest.param(ANY_OF_2, ANY_OF_2_CLEANED, id="any of 2"),
            pytest.param(ONE_OF, ONE_OF_CLEANED, id="one of"),
            # Test that type array is cleaned up
            pytest.param(TYPE_ARRAY, TYPE_ARRAY_CLEANED, id="type array"),
            # Test that allOf is cleaned up
            pytest.param(ALL_OF, ALL_OF_CLEANED, id="all of"),
            # Test that empty $defs are removed
            pytest.param(SCHEMA_WITH_EMPTY_DEFS, SCHEMA_WITH_EMPTY_DEFS_CLEANED, id="empty defs"),
            # Test that "required" as field name is kept
            pytest.param(
                SCHEMA_WITH_REQUIRED_AS_FIELD_NAME,
                SCHEMA_WITH_REQUIRED_AS_FIELD_NAME_CLEANED,
                id="required as field name",
            ),
            pytest.param(
                {"properties": {}},
                {"type": "object"},
                id="empty properties",
            ),
        ],
    )
    def test_streamline_schemas(self, schema: dict[str, Any], expected: dict[str, Any]):
        # Check that the schemas are valid
        validator_for(schema).check_schema(schema)  # pyright: ignore [reportUnknownMemberType]
        validator_for(expected).check_schema(expected)  # pyright: ignore [reportUnknownMemberType]

        sanitized = streamline_schema(copy.deepcopy(schema))
        assert sanitized == expected

    def test_nullable_enums(self):
        """Check that null is added as a possible value for an enum"""
        schema = streamline_schema(
            {
                "properties": {
                    "success": {
                        "type": "boolean",
                    },
                    "error_origin": {
                        "oneOf": [
                            {"type": "null"},
                            {"type": "string", "enum": ["mcp_client", "our_mcp_server"]},
                        ],
                    },
                },
                "required": [
                    "error_origin",
                    "success",
                ],
                "type": "object",
            },
        )
        assert schema == {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "error_origin": {"type": ["string", "null"], "enum": ["mcp_client", "our_mcp_server", None]},
            },
            "required": ["error_origin", "success"],
        }

        validate({"success": True, "error_origin": None}, schema)


class TestHandleInternalRef:
    def setup_method(self):
        # Setup common test data
        self.internal_defs = _build_internal_defs()  # pyright: ignore [reportUninitializedInstanceVariable, reportUnannotatedClassAttribute]
        self.used_refs: set[str] = set()  # pyright: ignore [reportUninitializedInstanceVariable]

    def test_non_internal_ref_returns_none(self):
        """Test that a non-internal ref returns None."""
        ref_name = "NonExistentRef"
        ref = {"$ref": f"#/$defs/{ref_name}"}

        result = _handle_internal_ref(ref_name, ref, self.used_refs, self.internal_defs)

        assert result is None
        assert len(self.used_refs) == 0

    def test_internal_ref_without_format_returns_as_is(self):
        """Test that an internal ref without format is returned as is."""
        ref_name = "File"
        ref = {"$ref": f"#/$defs/{ref_name}"}

        result = _handle_internal_ref(ref_name, ref, self.used_refs, self.internal_defs)

        assert result == ref
        assert ref_name in self.used_refs

    def test_no_warning_for_files(self, log_capture: LogCapture):
        """Test that a non-File ref with format logs a warning and returns as is."""
        ref = {"$ref": "#/$defs/File"}

        result = _handle_internal_ref("File", ref, self.used_refs, self.internal_defs)

        assert not log_capture.entries
        assert result == ref
        assert "File" in self.used_refs

    def test_file_ref_with_image_format_returns_image_ref(self):
        """Test that a File ref with image format returns an Image ref."""
        ref_name = "File"
        ref = {"$ref": f"#/$defs/{ref_name}", "format": "image"}

        result = _handle_internal_ref(ref_name, ref, self.used_refs, self.internal_defs)

        assert result == {"$ref": "#/$defs/Image"}
        assert "Image" in self.used_refs
        assert result is not None
        assert "format" not in result

    def test_file_ref_with_audio_format_returns_audio_ref(self):
        """Test that a File ref with audio format returns an Audio ref."""
        ref_name = "File"
        ref = {"$ref": f"#/$defs/{ref_name}", "format": "audio"}

        result = _handle_internal_ref(ref_name, ref, self.used_refs, self.internal_defs)

        assert result == {"$ref": "#/$defs/Audio"}
        assert "Audio" in self.used_refs
        assert result is not None
        assert "format" not in result

    def test_file_ref_with_pdf_format_returns_pdf_ref(self):
        """Test that a File ref with pdf format returns a PDF ref."""
        ref_name = "File"
        ref = {"$ref": f"#/$defs/{ref_name}", "format": "pdf"}

        result = _handle_internal_ref(ref_name, ref, self.used_refs, self.internal_defs)

        assert result == {"$ref": "#/$defs/PDF"}
        assert "PDF" in self.used_refs
        assert result is not None
        assert "format" not in result

    def test_file_ref_with_unknown_format_logs_warning_and_returns_as_is(self, log_capture: LogCapture):
        """Test that a File ref with unknown format logs a warning and returns as is."""
        ref_name = "File"
        ref = {"$ref": f"#/$defs/{ref_name}", "format": "unknown_format"}

        result = _handle_internal_ref(ref_name, ref, self.used_refs, self.internal_defs)

        entry = log_capture.entries[0]
        assert "Unexpected format for internal ref" in entry["event"]
        assert result == {"$ref": "#/$defs/File"}
        assert "File" in self.used_refs
        assert result is not None
        assert "format" not in result

    def test_preserves_additional_properties(self):
        """Test that additional properties in the ref are preserved."""
        ref_name = "File"
        ref = {
            "$ref": f"#/$defs/{ref_name}",
            "format": "image",
            "description": "An image file",
            "examples": ["example.jpg"],
        }

        result = _handle_internal_ref(ref_name, ref, self.used_refs, self.internal_defs)

        assert result == {
            "$ref": "#/$defs/Image",
            "description": "An image file",
            "examples": ["example.jpg"],
        }
        assert "Image" in self.used_refs
        assert result is not None
        assert "format" not in result


class TestInternalDefs:
    def test_internal_defs_exhaustive(self):
        """Check the link between FILE_DEFS and the internal defs"""
        internal_defs = set(_build_internal_defs().keys())
        assert FILE_DEFS.issubset(internal_defs)


class TestGetFileFormat:
    @pytest.mark.parametrize("ref_name", [f for f in FILE_DEFS if f != FILE_REF_NAME])
    def test_get_format(self, ref_name: str):
        assert get_file_format(f"#/$defs/{ref_name}", {}) is not None

    def test_get_format_for_file_no_format(self):
        assert get_file_format("#/$defs/File", {}) is None

    def test_get_format_for_file_with_invalid_format(self):
        # The file is not a valid file
        assert get_file_format("#/$defs/File", {"format": "hello"}) is None

    def test_get_format_for_file_with_valid_format(self):
        assert get_file_format("#/$defs/File", {"format": "image"}) == "image"


class TestSchemaContainsFile:
    def test_schema_contains_file(self):
        assert schema_contains_file(
            {"$defs": {"File": {}}, "type": "object", "properties": {"file": {"$ref": "#/$defs/File"}}},
        )
        assert not schema_contains_file(
            {"type": "object", "properties": {"field": {"type": "string"}}},
        )


class TestHandleOneAnyAllOf:
    # Pretty slim tests but the whole streamline tests are more extensive
    def _ref_handler(self, _: str, __: dict[str, Any]) -> dict[str, Any] | None:
        raise AssertionError("This should not be called")

    def test_compact_nullable_types_when_required(self):
        schema = {
            "anyOf": [
                {"type": "number"},
                {"type": "null"},
            ],
        }
        assert _handle_one_any_all_ofs(schema, self._ref_handler, {}, True, set()) == {"type": ["number", "null"]}

    def test_compact_nullable_types_when_not_required(self):
        schema = {
            "anyOf": [
                {"type": "number"},
                {"type": "null"},
            ],
        }
        assert _handle_one_any_all_ofs(schema, self._ref_handler, {}, False, set()) == {"type": "number"}

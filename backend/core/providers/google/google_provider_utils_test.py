from typing import Any

import pytest

from core.providers.google.google_provider_utils import (
    capitalize_schema_types,
    prepare_google_response_schema,
    resolve_schema_refs,
    restrict_string_formats,
    splat_nulls_recursive,
)


@pytest.mark.parametrize(
    ("schema", "expected"),
    [
        ({"examples": ["example1", "example2"]}, {}),
        (
            {"properties": {"name": {"type": "string", "examples": ["example1", "example2"]}}, "type": "object"},
            {"properties": {"name": {"type": "STRING"}}, "type": "OBJECT"},
        ),
        (
            {
                "$defs": {
                    "CalendarEvent": {
                        "properties": {
                            "title": {
                                "description": "The title of the calendar event",
                                "fuzzy": True,
                                "title": "Title",
                                "type": "string",
                            },
                            "description": {
                                "anyOf": [
                                    {
                                        "format": "html",
                                        "type": "string",
                                        "nullable": True,
                                    },
                                    {
                                        "type": "null",
                                    },
                                ],
                                "description": "The description of the calendar event, in HTML or raw text.",
                                "title": "Description",
                            },
                            "location": {
                                "anyOf": [
                                    {
                                        "fuzzy": True,
                                        "type": "string",
                                    },
                                    {
                                        "type": "null",
                                    },
                                ],
                                "default": None,
                                "description": "The location of the calendar event, if any",
                                "title": "Location",
                            },
                            "start_time": {
                                "$ref": "#/$defs/DatetimeLocal",
                            },
                            "end_time": {
                                "$ref": "#/$defs/DatetimeLocal",
                            },
                        },
                        "required": [
                            "title",
                            "start_time",
                            "end_time",
                        ],
                        "title": "CalendarEvent",
                        "type": "object",
                    },
                    "DatetimeLocal": {
                        "description": "This class represents a local datetime, with a datetime and a timezone.",
                        "properties": {
                            "date": {
                                "description": "The date of the local datetime.",
                                "examples": [
                                    "2023-03-01",
                                ],
                                "format": "date",
                                "title": "Date",
                                "type": "string",
                            },
                            "local_time": {
                                "description": "The time of the local datetime without timezone info.",
                                "examples": [
                                    "12:00:00",
                                    "22:00:00",
                                ],
                                "format": "time",
                                "title": "Local Time",
                                "type": "string",
                            },
                            "timezone": {
                                "description": "The timezone of the local time.",
                                "examples": [
                                    "Europe/Paris",
                                    "America/New_York",
                                ],
                                "format": "timezone",
                                "title": "Timezone",
                                "type": "string",
                            },
                        },
                        "required": [
                            "date",
                            "local_time",
                            "timezone",
                        ],
                        "title": "DatetimeLocal",
                        "type": "object",
                    },
                },
                "properties": {
                    "extracted_events": {
                        "description": "The calendar events extracted from the transcript",
                        "items": {
                            "$ref": "#/$defs/CalendarEvent",
                        },
                        "title": "Extracted Events",
                        "type": "array",
                    },
                },
                "required": [
                    "extracted_events",
                ],
                "title": "EventExtractionByChunkTaskOutput",
                "type": "object",
            },
            {
                "properties": {
                    "extracted_events": {
                        "description": "The calendar events extracted from the transcript",
                        "items": {
                            "properties": {
                                "title": {
                                    "description": "The title of the calendar event",
                                    "type": "STRING",
                                },
                                "description": {
                                    "type": "STRING",
                                    "format": "html",
                                    "nullable": True,
                                    "description": "The description of the calendar event, in HTML or raw text.",
                                },
                                "location": {
                                    "type": "STRING",
                                    "default": None,
                                    "nullable": True,
                                    "description": "The location of the calendar event, if any",
                                },
                                "start_time": {
                                    "description": "This class represents a local datetime, with a datetime and a timezone.",
                                    "properties": {
                                        "date": {
                                            "description": "The date of the local datetime.",
                                            "format": "date",
                                            "type": "STRING",
                                        },
                                        "local_time": {
                                            "description": "The time of the local datetime without timezone info.",
                                            "format": "time",
                                            "type": "STRING",
                                        },
                                        "timezone": {
                                            "description": "The timezone of the local time.",
                                            "format": "timezone",
                                            "type": "STRING",
                                        },
                                    },
                                    "required": [
                                        "date",
                                        "local_time",
                                        "timezone",
                                    ],
                                    "type": "OBJECT",
                                },
                                "end_time": {
                                    "description": "This class represents a local datetime, with a datetime and a timezone.",
                                    "properties": {
                                        "date": {
                                            "description": "The date of the local datetime.",
                                            "format": "date",
                                            "type": "STRING",
                                        },
                                        "local_time": {
                                            "description": "The time of the local datetime without timezone info.",
                                            "format": "time",
                                            "type": "STRING",
                                        },
                                        "timezone": {
                                            "description": "The timezone of the local time.",
                                            "format": "timezone",
                                            "type": "STRING",
                                        },
                                    },
                                    "required": [
                                        "date",
                                        "local_time",
                                        "timezone",
                                    ],
                                    "type": "OBJECT",
                                },
                            },
                            "required": [
                                "title",
                                "start_time",
                                "end_time",
                            ],
                            "type": "OBJECT",
                        },
                        "type": "ARRAY",
                    },
                },
                "required": [
                    "extracted_events",
                ],
                "type": "OBJECT",
            },
        ),
        (
            {
                "$defs": {
                    "ErrorAnalysis": {
                        "properties": {
                            "explanation": {
                                "description": "A detailed analysis of the error, if any. To only fill when success is False",
                                "title": "Explanation",
                                "type": "string",
                            },
                            "origin": {
                                "description": "The origin of the error, if any. 'mcp_client' are typically wrong arguments passed etc, and are less critical. 'our_mcp_server' are more serious errors, like the server not being able to process the request. To only fill when success is False",
                                "enum": [
                                    "mcp_client",
                                    "our_mcp_server",
                                ],
                                "title": "Origin",
                                "type": "string",
                            },
                            "criticity": {
                                "description": "The criticity of the error, if any. To only fill when success is False",
                                "enum": [
                                    "low",
                                    "medium",
                                    "high",
                                    "unsure",
                                ],
                                "title": "Criticity",
                                "type": "string",
                            },
                        },
                        "required": [
                            "explanation",
                            "origin",
                            "criticity",
                        ],
                        "title": "ErrorAnalysis",
                        "type": "object",
                    },
                },
                "properties": {
                    "success": {
                        "description": "Whether the feedback was processed successfully",
                        "title": "Success",
                        "type": "boolean",
                    },
                    "error_analysis": {
                        "anyOf": [
                            {
                                "$ref": "#/$defs/ErrorAnalysis",
                            },
                            {
                                "type": "null",
                            },
                        ],
                        "default": "null",
                        "description": "The error analysis, if any. To only fill when success is False",
                    },
                },
                "required": [
                    "success",
                ],
                "title": "MCPToolCallObserverOutput",
                "type": "object",
            },
            {
                "properties": {
                    "success": {
                        "description": "Whether the feedback was processed successfully",
                        "type": "BOOLEAN",
                    },
                    "error_analysis": {
                        "nullable": True,
                        "default": "null",
                        "description": "The error analysis, if any. To only fill when success is False",
                        "properties": {
                            "explanation": {
                                "description": "A detailed analysis of the error, if any. To only fill when success is False",
                                "type": "STRING",
                            },
                            "origin": {
                                "description": "The origin of the error, if any. 'mcp_client' are typically wrong arguments passed etc, and are less critical. 'our_mcp_server' are more serious errors, like the server not being able to process the request. To only fill when success is False",
                                "enum": [
                                    "mcp_client",
                                    "our_mcp_server",
                                ],
                                "type": "STRING",
                            },
                            "criticity": {
                                "description": "The criticity of the error, if any. To only fill when success is False",
                                "enum": [
                                    "low",
                                    "medium",
                                    "high",
                                    "unsure",
                                ],
                                "type": "STRING",
                            },
                        },
                        "required": [
                            "explanation",
                            "origin",
                            "criticity",
                        ],
                        "type": "OBJECT",
                    },
                },
                "required": [
                    "success",
                ],
                "type": "OBJECT",
            },
        ),
        (
            {
                "$defs": {
                    "ErrorAnalysis": {
                        "properties": {
                            "explanation": {
                                "description": "A detailed analysis of the error, if any. To only fill when success is False",
                                "title": "Explanation",
                                "type": "string",
                            },
                            "origin": {
                                "description": "The origin of the error, if any. 'mcp_client' are typically wrong arguments passed etc, and are less critical. 'our_mcp_server' are more serious errors, like the server not being able to process the request. To only fill when success is False",
                                "enum": [
                                    "mcp_client",
                                    "our_mcp_server",
                                ],
                                "title": "Origin",
                                "type": "string",
                            },
                            "criticity": {
                                "description": "The criticity of the error, if any. To only fill when success is False",
                                "enum": [
                                    "low",
                                    "medium",
                                    "high",
                                    "unsure",
                                ],
                                "title": "Criticity",
                                "type": "string",
                            },
                        },
                        "required": [
                            "explanation",
                            "origin",
                            "criticity",
                        ],
                        "title": "ErrorAnalysis",
                        "type": "object",
                    },
                },
                "properties": {
                    "success": {
                        "description": "Whether the feedback was processed successfully",
                        "title": "Success",
                        "type": "boolean",
                    },
                    "error_analysises": {
                        "anyOf": [
                            {
                                "items": {
                                    "$ref": "#/$defs/ErrorAnalysis",
                                },
                                "type": "array",
                            },
                            {
                                "type": "null",
                            },
                        ],
                        "default": "null",
                        "description": "The error analysis, if any. To only fill when success is False",
                        "title": "Error Analysises",
                    },
                },
                "required": [
                    "success",
                ],
                "title": "MCPToolCallObserverOutput",
                "type": "object",
            },
            {
                "properties": {
                    "success": {
                        "description": "Whether the feedback was processed successfully",
                        "type": "BOOLEAN",
                    },
                    "error_analysises": {
                        "default": "null",
                        "description": "The error analysis, if any. To only fill when success is False",
                        "items": {
                            "properties": {
                                "explanation": {
                                    "description": "A detailed analysis of the error, if any. To only fill when success is False",
                                    "type": "STRING",
                                },
                                "origin": {
                                    "description": "The origin of the error, if any. 'mcp_client' are typically wrong arguments passed etc, and are less critical. 'our_mcp_server' are more serious errors, like the server not being able to process the request. To only fill when success is False",
                                    "enum": [
                                        "mcp_client",
                                        "our_mcp_server",
                                    ],
                                    "type": "STRING",
                                },
                                "criticity": {
                                    "description": "The criticity of the error, if any. To only fill when success is False",
                                    "enum": [
                                        "low",
                                        "medium",
                                        "high",
                                        "unsure",
                                    ],
                                    "type": "STRING",
                                },
                            },
                            "required": [
                                "explanation",
                                "origin",
                                "criticity",
                            ],
                            "type": "OBJECT",
                        },
                        "type": "ARRAY",
                        "nullable": True,
                    },
                },
                "required": [
                    "success",
                ],
                "type": "OBJECT",
            },
        ),
        (
            {
                "$defs": {
                    "ErrorAnalysis": {
                        "properties": {
                            "explanation": {
                                "description": "A detailed analysis of the error, if any. To only fill when success is False",
                                "title": "Explanation",
                                "type": "string",
                            },
                            "origin": {
                                "description": "The origin of the error, if any. 'mcp_client' are typically wrong arguments passed etc, and are less critical. 'our_mcp_server' are more serious errors, like the server not being able to process the request. To only fill when success is False",
                                "enum": [
                                    "mcp_client",
                                    "our_mcp_server",
                                ],
                                "title": "Origin",
                                "type": "string",
                            },
                            "criticity": {
                                "description": "The criticity of the error, if any. To only fill when success is False",
                                "enum": [
                                    "low",
                                    "medium",
                                    "high",
                                    "unsure",
                                ],
                                "title": "Criticity",
                                "type": "string",
                            },
                        },
                        "required": [
                            "explanation",
                            "origin",
                            "criticity",
                        ],
                        "title": "ErrorAnalysis",
                        "type": "object",
                    },
                },
                "properties": {
                    "success": {
                        "description": "Whether the feedback was processed successfully",
                        "title": "Success",
                        "type": "boolean",
                    },
                    "error_analysises": {
                        "anyOf": [
                            {
                                "items": {
                                    "$ref": "#/$defs/ErrorAnalysis",
                                },
                                "type": "array",
                            },
                            {
                                "$ref": "#/$defs/ErrorAnalysis",
                            },
                            {
                                "type": "null",
                            },
                        ],
                        "default": "null",
                        "description": "The error analysis, if any. To only fill when success is False",
                        "title": "Error Analysises",
                    },
                },
                "required": [
                    "success",
                ],
                "title": "MCPToolCallObserverOutput",
                "type": "object",
            },
            {
                "properties": {
                    "success": {
                        "description": "Whether the feedback was processed successfully",
                        "type": "BOOLEAN",
                    },
                    "error_analysises": {
                        "anyOf": [
                            {
                                "items": {
                                    "properties": {
                                        "explanation": {
                                            "description": "A detailed analysis of the error, if any. To only fill when success is False",
                                            "type": "STRING",
                                        },
                                        "origin": {
                                            "description": "The origin of the error, if any. 'mcp_client' are typically wrong arguments passed etc, and are less critical. 'our_mcp_server' are more serious errors, like the server not being able to process the request. To only fill when success is False",
                                            "enum": [
                                                "mcp_client",
                                                "our_mcp_server",
                                            ],
                                            "type": "STRING",
                                        },
                                        "criticity": {
                                            "description": "The criticity of the error, if any. To only fill when success is False",
                                            "enum": [
                                                "low",
                                                "medium",
                                                "high",
                                                "unsure",
                                            ],
                                            "type": "STRING",
                                        },
                                    },
                                    "required": [
                                        "explanation",
                                        "origin",
                                        "criticity",
                                    ],
                                    "type": "OBJECT",
                                },
                                "type": "ARRAY",
                            },
                            {
                                "properties": {
                                    "explanation": {
                                        "description": "A detailed analysis of the error, if any. To only fill when success is False",
                                        "type": "STRING",
                                    },
                                    "origin": {
                                        "description": "The origin of the error, if any. 'mcp_client' are typically wrong arguments passed etc, and are less critical. 'our_mcp_server' are more serious errors, like the server not being able to process the request. To only fill when success is False",
                                        "enum": [
                                            "mcp_client",
                                            "our_mcp_server",
                                        ],
                                        "type": "STRING",
                                    },
                                    "criticity": {
                                        "description": "The criticity of the error, if any. To only fill when success is False",
                                        "enum": [
                                            "low",
                                            "medium",
                                            "high",
                                            "unsure",
                                        ],
                                        "type": "STRING",
                                    },
                                },
                                "required": [
                                    "explanation",
                                    "origin",
                                    "criticity",
                                ],
                                "type": "OBJECT",
                            },
                        ],
                        "default": "null",
                        "nullable": True,
                        "description": "The error analysis, if any. To only fill when success is False",
                    },
                },
                "required": [
                    "success",
                ],
                "type": "OBJECT",
            },
        ),
    ],
)
def test_sanitize_json_schema(schema: dict[str, Any], expected: dict[str, Any]):
    assert prepare_google_response_schema(schema) == expected


def test_resolve_schema_refs():
    schema = {
        "$defs": {
            "Person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {"$ref": "#/$defs/Address"},
                },
            },
            "Address": {
                "type": "object",
                "properties": {
                    "street": {"type": "string"},
                    "city": {"type": "string"},
                },
            },
        },
        "properties": {
            "person": {"$ref": "#/$defs/Person"},
        },
    }

    expected = {
        "properties": {
            "person": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "street": {"type": "string"},
                            "city": {"type": "string"},
                        },
                    },
                },
            },
        },
    }

    assert resolve_schema_refs(schema) == expected


def test_resolve_schema_refs_invalid_ref():
    schema = {
        "properties": {
            "person": {"$ref": "invalid_ref"},
        },
    }

    with pytest.raises(ValueError, match="Unsupported reference format: invalid_ref"):
        resolve_schema_refs(schema)


def test_resolve_schema_refs_missing_def():
    schema = {
        "$defs": {},
        "properties": {
            "person": {"$ref": "#/$defs/NonExistent"},
        },
    }

    with pytest.raises(ValueError, match="Definition not found: NonExistent"):
        resolve_schema_refs(schema)


def test_capitalize_schema_types():
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "addresses": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }

    expected = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "age": {"type": "INTEGER"},
            "addresses": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
        },
    }

    assert capitalize_schema_types(schema) == expected


def test_splat_nulls_recursive():
    schema = {
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "null"},
                ],
            },
            "nested_object": {
                "type": "object",
                "properties": {
                    "optional_nested": {
                        "oneOf": [
                            {"type": "integer"},
                            {"type": "null"},
                        ],
                    },
                },
            },
            "array_field": {
                "type": "array",
                "items": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"},
                    ],
                },
            },
        },
    }

    expected = {
        "type": "object",
        "properties": {
            "required_field": {"type": "string"},
            "optional_field": {
                "type": "string",
                "nullable": True,
            },
            "nested_object": {
                "type": "object",
                "properties": {
                    "optional_nested": {
                        "type": "integer",
                        "nullable": True,
                    },
                },
            },
            "array_field": {
                "type": "array",
                "items": {
                    "type": "string",
                    "nullable": True,
                },
            },
        },
    }

    assert splat_nulls_recursive(schema) == expected


def test_splat_nulls_recursive_with_preserved_fields():
    schema = {
        "type": "object",
        "title": "Test Schema",
        "description": "Test description",
        "properties": {
            "optional_field": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "null"},
                ],
                "description": "An optional field",
            },
        },
    }

    expected = {
        "type": "object",
        "title": "Test Schema",
        "description": "Test description",
        "properties": {
            "optional_field": {
                "type": "string",
                "nullable": True,
                "description": "An optional field",
            },
        },
    }

    assert splat_nulls_recursive(schema) == expected


def test_capitalize_schema_types_with_nullable_nested_objects():
    """Test that capitalize_schema_types works correctly with nested nullable objects."""
    schema = {
        "type": "object",
        "properties": {
            "success": {
                "type": "boolean",
                "description": "Whether the operation was successful",
            },
            "error_analysis": {
                "type": ["object", "null"],
                "properties": {
                    "explanation": {
                        "type": "string",
                        "description": "Error explanation",
                    },
                    "origin": {
                        "type": "string",
                        "enum": ["client", "server"],
                    },
                },
                "required": ["explanation", "origin"],
            },
        },
        "required": ["success", "error_analysis"],
    }

    # First apply splat_nulls_recursive to convert array types to nullable
    result = splat_nulls_recursive(schema)

    # Then capitalize the types
    result = capitalize_schema_types(result)

    # Check that top-level type is capitalized
    assert result["type"] == "OBJECT"

    # Check that nested simple types are capitalized
    assert result["properties"]["success"]["type"] == "BOOLEAN"
    assert result["properties"]["error_analysis"]["properties"]["explanation"]["type"] == "STRING"
    assert result["properties"]["error_analysis"]["properties"]["origin"]["type"] == "STRING"

    # Check that nullable type is now properly converted to single type + nullable
    assert result["properties"]["error_analysis"]["type"] == "OBJECT"
    assert result["properties"]["error_analysis"]["nullable"] is True

    # Check that other fields are preserved
    assert result["properties"]["success"]["description"] == "Whether the operation was successful"
    assert result["properties"]["error_analysis"]["properties"]["origin"]["enum"] == ["client", "server"]


def test_splat_nulls_recursive_with_type_arrays():
    """Test that splat_nulls_recursive properly converts type arrays to nullable single types."""
    schema = {
        "type": "object",
        "properties": {
            "simple_nullable": {
                "type": ["string", "null"],
                "description": "A nullable string",
            },
            "complex_nullable": {
                "type": ["object", "null"],
                "properties": {
                    "nested": {
                        "type": ["integer", "null"],
                    },
                },
            },
            "multiple_types": {
                "type": ["string", "integer", "null"],
                "description": "Multiple types with null",
            },
            "only_null": {
                "type": ["null"],
                "description": "Only null type",
            },
        },
    }

    result = splat_nulls_recursive(schema)

    # Simple nullable should become single type + nullable
    assert result["properties"]["simple_nullable"]["type"] == "string"
    assert result["properties"]["simple_nullable"]["nullable"] is True

    # Complex nullable should become single type + nullable
    assert result["properties"]["complex_nullable"]["type"] == "object"
    assert result["properties"]["complex_nullable"]["nullable"] is True

    # Nested nullable should also be converted
    assert result["properties"]["complex_nullable"]["properties"]["nested"]["type"] == "integer"
    assert result["properties"]["complex_nullable"]["properties"]["nested"]["nullable"] is True

    # Multiple types should keep array but remove null and add nullable
    assert result["properties"]["multiple_types"]["type"] == ["string", "integer"]
    assert result["properties"]["multiple_types"]["nullable"] is True

    # Only null should remain unchanged
    assert result["properties"]["only_null"]["type"] == ["null"]
    assert "nullable" not in result["properties"]["only_null"]

    # Descriptions should be preserved
    assert result["properties"]["simple_nullable"]["description"] == "A nullable string"


class TestRestrictStringFormats:
    def test_restrict_string_formats_no_restrictions(self):
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "date": {"type": "string", "format": "date-time"},
            },
        }
        result = restrict_string_formats(schema, None)
        assert result == schema

    def test_restrict_string_formats_allowed_format(self):
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "date": {"type": "string", "format": "date-time"},
            },
        }
        result = restrict_string_formats(schema, {"email", "date-time"})
        assert result == schema

    def test_restrict_string_formats_disallowed_format(self):
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "date": {"type": "string", "format": "date-time"},
                "name": {"type": "string"},
            },
        }
        result = restrict_string_formats(schema, {"date-time"})
        expected = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},  # format removed
                "date": {"type": "string", "format": "date-time"},  # format kept
                "name": {"type": "string"},  # no format, unchanged
            },
        }
        assert result == expected

    def test_restrict_string_formats_enum_allowed(self):
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive"]},
            },
        }
        result = restrict_string_formats(schema, {"enum"})
        assert result == schema

    def test_restrict_string_formats_enum_disallowed(self):
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive"]},
            },
        }
        result = restrict_string_formats(schema, {"date-time"})
        expected = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Valid values: 'active', 'inactive'",
                },  # enum removed but values preserved in description
            },
        }
        assert result == expected

    def test_restrict_string_formats_enum_disallowed_with_existing_description(self):
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive"], "description": "The current status"},
            },
        }
        result = restrict_string_formats(schema, {"date-time"})
        expected = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "The current status. Valid values: 'active', 'inactive'",
                },  # enum removed but values appended to existing description
            },
        }
        assert result == expected

    def test_restrict_string_formats_nested_objects(self):
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "format": "email"},
                        "birth_date": {"type": "string", "format": "date-time"},
                    },
                },
            },
        }
        result = restrict_string_formats(schema, {"date-time"})
        expected = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},  # format removed
                        "birth_date": {"type": "string", "format": "date-time"},  # format kept
                    },
                },
            },
        }
        assert result == expected

    def test_restrict_string_formats_array_items(self):
        schema = {
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "items": {"type": "string", "format": "email"},
                },
                "dates": {
                    "type": "array",
                    "items": {"type": "string", "format": "date-time"},
                },
            },
        }
        result = restrict_string_formats(schema, {"date-time"})
        expected = {
            "type": "object",
            "properties": {
                "emails": {
                    "type": "array",
                    "items": {"type": "string"},  # format removed
                },
                "dates": {
                    "type": "array",
                    "items": {"type": "string", "format": "date-time"},  # format kept
                },
            },
        }
        assert result == expected

    def test_restrict_string_formats_capitalized_types(self):
        schema = {
            "type": "OBJECT",
            "properties": {
                "email": {"type": "STRING", "format": "email"},
                "date": {"type": "STRING", "format": "date-time"},
            },
        }
        result = restrict_string_formats(schema, {"date-time"})
        expected = {
            "type": "OBJECT",
            "properties": {
                "email": {"type": "STRING"},  # format removed
                "date": {"type": "STRING", "format": "date-time"},  # format kept
            },
        }
        assert result == expected

    def test_restrict_string_formats_union_types(self):
        schema = {
            "type": "object",
            "properties": {
                "flexible": {"type": ["string", "null"], "format": "email"},
            },
        }
        result = restrict_string_formats(schema, {"date-time"})
        expected = {
            "type": "object",
            "properties": {
                "flexible": {"type": ["string", "null"]},  # format removed
            },
        }
        assert result == expected


class TestPrepareGoogleResponseSchema:
    def test_prepare_google_response_schema_basic(self):
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
        result = prepare_google_response_schema(schema)
        expected = {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING"},
                "age": {"type": "INTEGER"},
            },
        }
        assert result == expected

    def test_prepare_google_response_schema_with_format_restriction(self):
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "date": {"type": "string", "format": "date-time"},
                "name": {"type": "string"},
            },
        }
        result = prepare_google_response_schema(schema, {"date-time"})
        expected = {
            "type": "OBJECT",
            "properties": {
                "email": {"type": "STRING"},  # format removed
                "date": {"type": "STRING", "format": "date-time"},  # format kept
                "name": {"type": "STRING"},  # no format, unchanged
            },
        }
        assert result == expected

    def test_prepare_google_response_schema_with_enum_restriction(self):
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive"]},
                "priority": {"type": "string", "format": "email"},
            },
        }
        result = prepare_google_response_schema(schema, {"enum"})
        expected = {
            "type": "OBJECT",
            "properties": {
                "status": {"type": "STRING", "enum": ["active", "inactive"]},  # enum kept
                "priority": {"type": "STRING"},  # format removed
            },
        }
        assert result == expected

    def test_prepare_google_response_schema_with_enum_disallowed(self):
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive"]},
                "priority": {"type": "string", "format": "email"},
            },
        }
        result = prepare_google_response_schema(schema, {"date-time"})
        expected = {
            "type": "OBJECT",
            "properties": {
                "status": {
                    "type": "STRING",
                    "description": "Valid values: 'active', 'inactive'",
                },  # enum removed but values preserved in description
                "priority": {"type": "STRING"},  # format removed
            },
        }
        assert result == expected

    def test_prepare_google_response_schema_no_format_restriction(self):
        schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "date": {"type": "string", "format": "date-time"},
            },
        }
        result = prepare_google_response_schema(schema, None)
        expected = {
            "type": "OBJECT",
            "properties": {
                "email": {"type": "STRING", "format": "email"},
                "date": {"type": "STRING", "format": "date-time"},
            },
        }
        assert result == expected

    def test_prepare_google_response_schema_integration_with_provider_options(self):
        """Test that the function works correctly when used with ProviderOptions"""
        # Test schema with various string formats
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive"]},
                "email": {"type": "string", "format": "email"},
                "date": {"type": "string", "format": "date-time"},
                "name": {"type": "string"},
            },
        }

        result = prepare_google_response_schema(schema, {"enum", "date-time"})
        expected = {
            "type": "OBJECT",
            "properties": {
                "status": {"type": "STRING", "enum": ["active", "inactive"]},  # enum kept
                "email": {"type": "STRING"},  # format removed
                "date": {"type": "STRING", "format": "date-time"},  # format kept
                "name": {"type": "STRING"},  # no format, unchanged
            },
        }
        assert result == expected


def test_splat_nulls_recursive_nullable_preservation_bug():
    """Test the bug where nullable status can be incorrectly overwritten by preserved fields."""
    schema = {
        "type": "object",
        "nullable": False,  # This will be preserved and could overwrite the new nullable status
        "properties": {
            "field": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "null"},
                ],
                "nullable": False,  # This should NOT overwrite the new nullable: True
            },
        },
    }

    result = splat_nulls_recursive(schema)

    # The field should be nullable=True despite the original nullable=False
    assert result["properties"]["field"]["nullable"] is True
    assert result["properties"]["field"]["type"] == "string"

    # The root object should keep its original nullable=False
    assert result["nullable"] is False


def test_splat_nulls_recursive_complex_nullable_preservation():
    """Test that nullable fields in complex nested structures are preserved correctly."""
    schema = {
        "type": "object",
        "properties": {
            "complex_field": {
                "anyOf": [
                    {
                        "type": "object",
                        "properties": {
                            "inner": {"type": "string"},
                        },
                    },
                    {"type": "null"},
                ],
                "nullable": False,  # This should be overridden
                "description": "A complex nullable field",
                "title": "Complex Field",
            },
        },
    }

    result = splat_nulls_recursive(schema)

    # The complex field should be nullable=True
    assert result["properties"]["complex_field"]["nullable"] is True
    assert result["properties"]["complex_field"]["type"] == "object"

    # Other fields should be preserved
    assert result["properties"]["complex_field"]["description"] == "A complex nullable field"
    assert result["properties"]["complex_field"]["title"] == "Complex Field"

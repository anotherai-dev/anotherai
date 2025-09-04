from typing import Any

import pytest

from core.domain.exceptions import JSONSchemaValidationError
from core.domain.version import Version


class TestValidateInput:
    """Test cases for Version.validate_input method"""

    def test_no_input_schema_no_input(self):
        """Test that validation passes when no schema and no input are provided"""
        version = Version()
        # Should not raise any exception
        version.validate_input(None)

    def test_no_input_schema_with_input_raises_error(self):
        """Test that validation fails when no schema is defined but input is provided"""
        version = Version()
        input_obj = {"key": "value"}

        with pytest.raises(JSONSchemaValidationError) as exc_info:
            version.validate_input(input_obj)

        assert "Input variables are provided but the version does not support them" in str(exc_info.value)

    def test_with_input_schema_no_input_raises_error(self):
        """Test that validation fails when schema is defined but no input is provided"""
        version = Version(
            input_variables_schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        )

        with pytest.raises(JSONSchemaValidationError) as exc_info:
            version.validate_input(None)

        assert "Input variables are not provided but the version requires them" in str(exc_info.value)

    def test_valid_input_passes_validation(self):
        """Test that valid input passes validation"""
        version = Version(
            input_variables_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                "required": ["name"],
            },
        )

        valid_input = {"name": "John", "age": 30}
        # Should not raise any exception
        version.validate_input(valid_input)

    def test_invalid_input_raises_validation_error(self):
        """Test that invalid input raises validation error with proper message"""
        version = Version(
            input_variables_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                "required": ["name", "age"],
            },
        )

        invalid_input = {"name": "John", "age": "not_a_number"}

        with pytest.raises(JSONSchemaValidationError) as exc_info:
            version.validate_input(invalid_input)

        error_message = str(exc_info.value)
        assert "Input variables are not compatible with the version's input variables schema" in error_message
        assert "[age]" in error_message

    def test_missing_required_field_raises_validation_error(self):
        """Test that missing required field raises validation error"""
        version = Version(
            input_variables_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}, "email": {"type": "string"}},
                "required": ["name", "email"],
            },
        )

        invalid_input = {"name": "John"}

        with pytest.raises(JSONSchemaValidationError) as exc_info:
            version.validate_input(invalid_input)

        error_message = str(exc_info.value)
        assert "Input variables are not compatible with the version's input variables schema" in error_message

    @pytest.mark.parametrize(
        ("input_schema", "input_obj", "should_pass"),
        [
            # Valid cases
            ({"type": "object", "properties": {"count": {"type": "integer"}}}, {"count": 42}, True),
            (
                {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "string"}}}},
                {"items": ["a", "b", "c"]},
                True,
            ),
            # Invalid cases
            ({"type": "object", "properties": {"count": {"type": "integer"}}}, {"count": "not_a_number"}, False),
            ({"type": "object", "properties": {"flag": {"type": "boolean"}}}, {"flag": "yes"}, False),
        ],
    )
    def test_various_input_types(self, input_schema: dict[str, Any], input_obj: dict[str, Any], should_pass: bool):
        """Test validation with various input types and schemas"""
        version = Version(input_variables_schema=input_schema)

        if should_pass:
            # Should not raise any exception
            version.validate_input(input_obj)
        else:
            with pytest.raises(JSONSchemaValidationError):
                version.validate_input(input_obj)


class TestValidateOutput:
    """Test cases for Version.validate_output method"""

    def test_no_output_schema_returns_unchanged(self):
        """Test that object is returned unchanged when no output schema is defined"""
        version = Version()
        obj = {"any": "value", "nested": {"data": 123}}

        result = version.validate_output(obj)
        assert result == obj
        assert result is obj  # Should return the same object

    def test_valid_output_passes_validation(self):
        """Test that valid output passes validation"""
        version = Version()
        version.output_schema = Version.OutputSchema(
            json_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}, "count": {"type": "integer"}},
                "required": ["message"],
            },
        )

        valid_output = {"message": "Hello", "count": 42}
        result = version.validate_output(valid_output)
        assert result == valid_output

    def test_invalid_output_raises_validation_error(self):
        """Test that invalid output raises validation error"""
        version = Version()
        version.output_schema = Version.OutputSchema(
            json_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}, "count": {"type": "integer"}},
                "required": ["message", "count"],
            },
        )

        invalid_output = {"message": "Hello", "count": "not_a_number"}

        with pytest.raises(JSONSchemaValidationError) as exc_info:
            version.validate_output(invalid_output)

        error_message = str(exc_info.value)
        assert "[count]" in error_message

    def test_partial_validation_with_missing_required_fields(self):
        """Test that partial=True allows missing required fields"""
        version = Version()
        version.output_schema = Version.OutputSchema(
            json_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "count": {"type": "integer"},
                },
                "required": ["title", "description", "count"],
            },
        )

        partial_output = {"title": "Test Title"}

        # Should pass with partial=True
        result = version.validate_output(partial_output, partial=True)
        assert result == partial_output

        # Should fail with partial=False (default)
        with pytest.raises(JSONSchemaValidationError):
            version.validate_output(partial_output, partial=False)

    def test_strip_extras_removes_unknown_fields(self):
        """Test that strip_extras=True removes fields not in schema"""
        version = Version()
        version.output_schema = Version.OutputSchema(
            json_schema={"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}}},
        )

        output_with_extras = {
            "name": "John",
            "age": 30,
            "extra_field": "should_be_removed",
            "another_extra": {"nested": "data"},
        }

        result = version.validate_output(output_with_extras, strip_extras=True)

        # Extra fields should be removed (object is modified in place)
        expected = {"name": "John", "age": 30}
        assert result == expected
        assert output_with_extras == expected  # Original object is modified

    def test_sanitize_empties_removes_null_optional_fields(self):
        """Test that sanitize_empties=True removes null values from optional fields"""
        version = Version()
        version.output_schema = Version.OutputSchema(
            json_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "optional_field": {"type": ["string", "null"]},
                },
                "required": ["name"],
            },
        )

        output_with_nulls = {"name": "John", "description": None, "optional_field": None}

        result = version.validate_output(output_with_nulls, sanitize_empties=True)

        # Null optional fields should be removed
        expected = {"name": "John"}
        assert result == expected

    def test_combined_strip_and_sanitize(self):
        """Test combining strip_extras and sanitize_empties"""
        version = Version()
        version.output_schema = Version.OutputSchema(
            json_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}, "description": {"type": ["string", "null"]}},
                "required": ["name"],
            },
        )

        messy_output = {"name": "John", "description": None, "extra_field": "remove_me", "another_extra": 123}

        result = version.validate_output(messy_output, strip_extras=True, sanitize_empties=True)

        expected = {"name": "John"}
        assert result == expected

    @pytest.mark.parametrize(
        ("output_schema", "output_obj", "should_pass"),
        [
            # Valid cases
            (
                {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "string"}}}},
                {"items": ["a", "b", "c"]},
                True,
            ),
            (
                {
                    "type": "object",
                    "properties": {"nested": {"type": "object", "properties": {"value": {"type": "number"}}}},
                },
                {"nested": {"value": 42.5}},
                True,
            ),
            # Invalid cases
            ({"type": "object", "properties": {"flag": {"type": "boolean"}}}, {"flag": "not_a_boolean"}, False),
            (
                {"type": "object", "properties": {"items": {"type": "array", "items": {"type": "integer"}}}},
                {"items": ["not", "integers"]},
                False,
            ),
        ],
    )
    def test_various_output_types(self, output_schema: dict[str, Any], output_obj: dict[str, Any], should_pass: bool):
        """Test validation with various output types and schemas"""
        version = Version()
        version.output_schema = Version.OutputSchema(json_schema=output_schema)

        if should_pass:
            result = version.validate_output(output_obj)
            assert result == output_obj
        else:
            with pytest.raises(JSONSchemaValidationError):
                version.validate_output(output_obj)

    def test_nested_validation_error_path(self):
        """Test that validation errors include the correct path for nested objects"""
        version = Version()
        version.output_schema = Version.OutputSchema(
            json_schema={
                "type": "object",
                "properties": {
                    "user": {
                        "type": "object",
                        "properties": {"profile": {"type": "object", "properties": {"age": {"type": "integer"}}}},
                    },
                },
            },
        )

        invalid_nested_output = {"user": {"profile": {"age": "not_a_number"}}}

        with pytest.raises(JSONSchemaValidationError) as exc_info:
            version.validate_output(invalid_nested_output)

        error_message = str(exc_info.value)
        assert "[user.profile.age]" in error_message

    def test_array_validation_error_path(self):
        """Test that validation errors include the correct path for array items"""
        version = Version()
        version.output_schema = Version.OutputSchema(
            json_schema={
                "type": "object",
                "properties": {
                    "items": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "integer"}}}},
                },
            },
        )

        invalid_array_output = {
            "items": [
                {"id": 1},
                {"id": "not_a_number"},  # Second item is invalid
                {"id": 3},
            ],
        }

        with pytest.raises(JSONSchemaValidationError) as exc_info:
            version.validate_output(invalid_array_output)

        error_message = str(exc_info.value)
        assert "[items.1.id]" in error_message


class TestVersionValidate:
    def test_validate_version(self):
        version = Version.model_validate(
            {
                "id": "d59fe7a74f094d05ca9016a1b710ea26",
                "model": "gpt-5-2025-08-07",
                "temperature": 0,
                "enabled_tools": [
                    {
                        "name": "@browser-text",
                        "input_schema": {},
                    },
                    "@search-google",
                ],
            },
        )
        assert version.id == "d59fe7a74f094d05ca9016a1b710ea26"
        assert version.enabled_tools
        assert len(version.enabled_tools) == 2

# pyright: reportPrivateUsage=false


from protocol.api._mcp_utils import _add_string_to_property_type


class TestAddStringToPropertyType:
    def test_array_type_conversion(self):
        """Test that array type gets converted to [array, string]"""
        property = {
            "type": "array",
            "items": {"type": "string"},
        }
        updated = _add_string_to_property_type(property)
        assert updated == {
            "anyOf": [
                {
                    "type": "array",
                    "items": {"type": "string"},
                },
                {"type": "string"},
            ],
        }
        assert property == {  # property should be untouched
            "type": "array",
            "items": {"type": "string"},
        }

    def test_object_type_conversion(self):
        """Test that object type gets converted to [object, string]"""
        property = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }
        updated = _add_string_to_property_type(property)
        assert updated == {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
                {"type": "string"},
            ],
        }
        assert property == {  # property should be untouched
            "type": "object",
            "properties": {"name": {"type": "string"}},
        }

    def test_idempotency_array(self):
        """Test that calling the function twice on array type gives same result"""
        property = {"type": "array", "items": {"type": "string"}}
        updated1 = _add_string_to_property_type(property)
        updated2 = _add_string_to_property_type(updated1)
        assert updated1 == updated2
        assert updated2 == {
            "anyOf": [
                {
                    "type": "array",
                    "items": {"type": "string"},
                },
                {"type": "string"},
            ],
        }

    def test_idempotency_object(self):
        """Test that calling the function twice on object type gives same result"""
        property = {"type": "object", "properties": {"name": {"type": "string"}}}
        updated1 = _add_string_to_property_type(property)
        updated2 = _add_string_to_property_type(updated1)
        assert updated1 == updated2
        assert updated2 == {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
                {"type": "string"},
            ],
        }

    def test_anyof_without_string_adds_string(self):
        """Test that anyOf without string type gets string type added"""
        property = {
            "anyOf": [
                {"type": "integer"},
                {"type": "boolean"},
            ],
        }
        updated = _add_string_to_property_type(property)
        assert updated == {
            "anyOf": [
                {"type": "integer"},
                {"type": "boolean"},
                {"type": "string"},
            ],
        }
        assert property == {  # property should be untouched
            "anyOf": [
                {"type": "integer"},
                {"type": "boolean"},
            ],
        }

    def test_anyof_with_string_unchanged(self):
        """Test that anyOf with string type already present remains unchanged"""
        property = {
            "anyOf": [
                {"type": "integer"},
                {"type": "string"},
                {"type": "boolean"},
            ],
        }
        updated = _add_string_to_property_type(property)
        assert updated == property
        assert updated is property  # Function returns same object when unchanged

    def test_anyof_idempotency(self):
        """Test that calling the function twice on anyOf gives same result"""
        property = {
            "anyOf": [
                {"type": "integer"},
                {"type": "boolean"},
            ],
        }
        updated1 = _add_string_to_property_type(property)
        updated2 = _add_string_to_property_type(updated1)
        assert updated1 == updated2
        assert updated2 == {
            "anyOf": [
                {"type": "integer"},
                {"type": "boolean"},
                {"type": "string"},
            ],
        }

    def test_non_array_object_types_unchanged(self):
        """Test that non-array/object types remain unchanged"""
        test_cases = [
            {"type": "string"},
            {"type": "integer"},
            {"type": "boolean"},
            {"type": "number"},
            {"type": "null"},
        ]

        for property in test_cases:
            updated = _add_string_to_property_type(property)
            assert updated == property
            assert updated is property  # Function returns same object when unchanged

    def test_list_type_unchanged(self):
        """Test that type already as list remains unchanged"""
        property = {"type": ["array", "string"]}
        updated = _add_string_to_property_type(property)
        assert updated == property
        assert updated is property  # Function returns same object when unchanged

    def test_empty_property_unchanged(self):
        """Test that empty property dict remains unchanged"""
        property = {}
        updated = _add_string_to_property_type(property)
        assert updated == property
        assert updated is property  # Function returns same object when unchanged

    def test_no_type_field_unchanged(self):
        """Test that property without type field remains unchanged"""
        property = {"description": "Some property", "default": "value"}
        updated = _add_string_to_property_type(property)
        assert updated == property
        assert updated is property  # Function returns same object when unchanged

    def test_invalid_anyof_structures(self):
        """Test behavior with various anyOf structures"""
        # Non-list anyOf remains unchanged
        property1 = {"anyOf": "not_a_list"}
        updated1 = _add_string_to_property_type(property1)
        assert updated1 == property1
        assert updated1 is property1

        # Empty anyOf list remains unchanged
        property2 = {"anyOf": []}
        updated2 = _add_string_to_property_type(property2)
        assert updated2 == property2
        assert updated2 is property2

        # anyOf with items without type field gets string added (this is expected behavior)
        property3 = {"anyOf": [{"invalid": "structure"}]}
        updated3 = _add_string_to_property_type(property3)
        assert updated3 == {
            "anyOf": [
                {"invalid": "structure"},
                {"type": "string"},
            ],
        }
        assert property3 == {"anyOf": [{"invalid": "structure"}]}  # Original unchanged

    def test_preserves_additional_properties(self):
        """Test that additional properties are preserved"""
        property = {
            "type": "array",
            "items": {"type": "string"},
            "description": "An array of strings",
            "minItems": 1,
            "maxItems": 10,
        }
        updated = _add_string_to_property_type(property)
        assert updated == {
            "anyOf": [
                {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "An array of strings",
                    "minItems": 1,
                    "maxItems": 10,
                },
                {"type": "string"},
            ],
        }

    def test_complex_anyof_scenario(self):
        """Test complex anyOf scenario with nested structures"""
        property = {
            "anyOf": [
                {"type": "object", "properties": {"name": {"type": "string"}}},
                {"type": "array", "items": {"type": "integer"}},
                {"type": "null"},
            ],
            "description": "Complex union type",
        }
        updated = _add_string_to_property_type(property)
        assert updated == {
            "anyOf": [
                {"type": "object", "properties": {"name": {"type": "string"}}},
                {"type": "array", "items": {"type": "integer"}},
                {"type": "null"},
                {"type": "string"},
            ],
            "description": "Complex union type",
        }

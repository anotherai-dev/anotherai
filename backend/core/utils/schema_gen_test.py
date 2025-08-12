from core.utils.schema_gen import schema_from_data


class TestSchemaFromData:
    def test_schema_from_data_all_types(self):
        schema = schema_from_data(
            {
                "a_number": 1.0,
                "a_boolean": True,
                "a_array": [1, 2, 3],
                "a_object": {"a": 1, "b": "hello"},
                "a_null": None,
            },
        )
        assert schema == {
            "type": "object",
            "properties": {
                "a_number": {"type": "number"},
                "a_boolean": {"type": "boolean"},
                "a_array": {"type": "array", "items": {"type": "integer"}},
                "a_object": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "string"}}},
                "a_null": {},
            },
        }

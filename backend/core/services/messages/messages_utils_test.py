import pytest

from core.domain.exceptions import BadRequestError
from core.domain.file import File
from core.domain.message import Message, MessageContent
from core.services.messages.messages_utils import json_schema_for_template, json_schema_for_template_and_variables


class TestJsonSchemaForTemplate:
    def test_empty_messages(self):
        """Test with empty messages list."""
        messages: list[Message] = []
        base_schema = None
        schema, last_index = json_schema_for_template(messages, base_schema)
        assert schema is None
        assert last_index == -1

    def test_no_templated_messages(self):
        """Test with messages containing no template variables."""
        messages = [
            Message.with_text("Hello world"),
            Message.with_text("This is a test"),
        ]
        base_schema = None
        schema, last_index = json_schema_for_template(messages, base_schema)
        assert schema is None
        assert last_index == -1

    def test_single_templated_message(self):
        """Test with a single message containing template variables."""
        messages = [
            Message.with_text("Hello {{name}}"),
        ]
        base_schema = None
        schema, last_index = json_schema_for_template(messages, base_schema)
        assert schema is not None
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert last_index == 0

    def test_multiple_templated_messages(self):
        """Test with multiple messages containing template variables."""
        messages = [
            Message.with_text("Hello {{name}}"),
            Message.with_text("Your age is {{age}}"),
            Message.with_text("Welcome to {{city}}"),
        ]
        base_schema = None
        schema, last_index = json_schema_for_template(messages, base_schema)
        assert schema == {
            "type": "object",
            "properties": {
                "name": {},
                "age": {},
                "city": {},
            },
        }
        assert last_index == 2

    def test_with_base_schema(self):
        """Test with a provided base schema."""
        messages = [
            Message.with_text("Hello {{name}}"),
        ]
        base_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        schema, last_index = json_schema_for_template(messages, base_schema)
        assert schema == {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        assert last_index == 0

    def test_mixed_content_messages(self):
        """Test with messages containing both templated and non-templated content."""
        messages = [
            Message.with_text("Hello world"),
            Message.with_text("Welcome {{name}}"),
            Message.with_text("This is a test"),
            Message.with_text("Your age is {{age}}"),
        ]
        base_schema = None
        schema, last_index = json_schema_for_template(messages, base_schema)
        assert schema is not None
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert last_index == 3

    def test_complex_template_variables(self):
        """Test with complex template variable patterns."""
        messages = [
            Message.with_text("User: {{user.name}}"),
            Message.with_text("Address: {{user.address.street}}"),
        ]
        base_schema = None
        schema, last_index = json_schema_for_template(messages, base_schema)
        assert schema is not None
        assert "properties" in schema
        assert "user" in schema["properties"]
        assert "properties" in schema["properties"]["user"]
        assert "name" in schema["properties"]["user"]["properties"]
        assert "address" in schema["properties"]["user"]["properties"]
        assert last_index == 1

    def test_string_only(self):
        messages = [Message.with_text("Hello, {{ name }}!")]
        schema, last_index = json_schema_for_template(messages, base_schema=None)
        assert schema == {
            "type": "object",
            "properties": {"name": {}},
        }
        assert last_index == 0

    def test_file_only(self):
        messages = Message(role="user", content=[MessageContent(file=File(url="{{a_file_url}}"))])

        schema, last_index = json_schema_for_template([messages], base_schema=None)
        assert schema == {
            "type": "object",
            "properties": {"a_file_url": {}},
        }
        assert last_index == 0

    def test_file_with_nested_key(self):
        messages = Message(role="user", content=[MessageContent(file=File(url="{{a_file_url.key}}"))])

        schema, last_index = json_schema_for_template([messages], base_schema=None)
        assert schema == {
            "type": "object",
            "properties": {
                "a_file_url": {
                    "type": "object",
                    "properties": {
                        "key": {},
                    },
                },
            },
        }
        assert last_index == 0

    def test_file_and_text(self):
        messages = [
            Message(
                role="user",
                content=[
                    MessageContent(text="Hello, {{ name }}!"),
                    MessageContent(file=File(url="{{a_file_url}}")),
                ],
            ),
        ]
        schema, _ = json_schema_for_template(messages, base_schema=None)
        assert schema == {
            "type": "object",
            "properties": {
                "name": {},
                "a_file_url": {},
            },
        }

    def test_content_type(self):
        messages = [
            Message(role="user", content=[MessageContent(file=File(url="data:image/{{ext}},base64,{{data}}"))]),
        ]
        schema, _ = json_schema_for_template(messages, base_schema=None)
        assert schema == {
            "type": "object",
            "properties": {
                "ext": {},
                "data": {},
            },
        }


class TestJsonSchemaForTemplateAndVariables:
    def test_variables_none_returns_none(self):
        """Test with variables=None should return None schema and -1 index."""
        messages = [Message.with_text("Hello {{name}}")]
        schema, last_index = json_schema_for_template_and_variables(messages, None)
        assert schema is None
        assert last_index == -1

    def test_empty_variables_with_no_template(self):
        """Test with empty variables and no template should return None."""
        messages = [Message.with_text("Hello world")]
        schema, last_index = json_schema_for_template_and_variables(messages, {})
        assert schema is None
        assert last_index == -1

    def test_variables_without_template_raises_error(self):
        """Test providing variables but no template should raise BadRequestError."""
        messages = [Message.with_text("Hello world")]
        variables = {"name": "John"}

        with pytest.raises(
            BadRequestError,
            match="Input variables are provided but the messages do not contain a valid template",
        ):
            json_schema_for_template_and_variables(messages, variables)

    def test_template_without_variables_raises_error(self):
        """Test providing template but no variables should raise BadRequestError."""
        messages = [Message.with_text("Hello {{name}}")]
        variables = {}

        with pytest.raises(BadRequestError, match="Messages are templated but no input variables are provided"):
            json_schema_for_template_and_variables(messages, variables)

    def test_simple_string_variable_match(self):
        """Test with simple string variable matching template."""
        messages = [Message.with_text("Hello {{name}}")]
        variables = {"name": "John"}

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        assert schema is not None
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert last_index == 0

    def test_multiple_variables_and_templates(self):
        """Test with multiple variables matching multiple templates."""
        messages = [
            Message.with_text("Hello {{name}}"),
            Message.with_text("You are {{age}} years old"),
            Message.with_text("Welcome to {{city}}"),
        ]
        variables = {"name": "John", "age": 25, "city": "New York"}

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        assert schema is not None
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert "city" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"
        assert schema["properties"]["city"]["type"] == "string"
        assert last_index == 2

    def test_nested_object_variables(self):
        """Test with nested object variables matching nested templates."""
        messages = [
            Message.with_text("Hello {{user.name}}"),
            Message.with_text("Your email is {{user.email}}"),
        ]
        variables = {"user": {"name": "John", "email": "john@example.com"}}

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        assert schema is not None
        assert schema["type"] == "object"
        assert "user" in schema["properties"]
        assert schema["properties"]["user"]["type"] == "object"
        user_props = schema["properties"]["user"]["properties"]
        assert "name" in user_props
        assert "email" in user_props
        assert user_props["name"]["type"] == "string"
        assert user_props["email"]["type"] == "string"
        assert last_index == 1

    def test_array_variables(self):
        """Test with array variables."""
        messages = [Message.with_text("Items: {{items}}")]
        variables = {"items": ["apple", "banana", "cherry"]}

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        assert schema is not None
        assert schema["type"] == "object"
        assert "items" in schema["properties"]
        assert schema["properties"]["items"]["type"] == "array"
        assert schema["properties"]["items"]["items"]["type"] == "string"
        assert last_index == 0

    def test_mixed_types_variables(self):
        """Test with mixed data types in variables."""
        messages = [
            Message.with_text("Name: {{name}}, Age: {{age}}, Active: {{active}}, Score: {{score}}"),
        ]
        variables = {"name": "John", "age": 25, "active": True, "score": 95.5}

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        assert schema is not None
        assert schema["type"] == "object"
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"
        assert schema["properties"]["active"]["type"] == "boolean"
        assert schema["properties"]["score"]["type"] == "number"
        assert last_index == 0

    def test_complex_nested_structure(self):
        """Test with complex nested structure in variables."""
        messages = [
            Message.with_text("User: {{person.name}}, Address: {{person.address.street}}"),
            Message.with_text("Hobbies: {{person.hobbies}}"),
        ]
        variables = {
            "person": {
                "name": "John",
                "address": {"street": "123 Main St", "city": "Anytown"},
                "hobbies": ["reading", "swimming"],
            },
        }

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        assert schema is not None
        assert schema["type"] == "object"
        assert "person" in schema["properties"]
        person_schema = schema["properties"]["person"]
        assert person_schema["type"] == "object"
        assert "name" in person_schema["properties"]
        assert "address" in person_schema["properties"]
        assert "hobbies" in person_schema["properties"]

        address_schema = person_schema["properties"]["address"]
        assert address_schema["type"] == "object"
        assert "street" in address_schema["properties"]

        assert person_schema["properties"]["hobbies"]["type"] == "array"
        assert last_index == 1

    def test_partial_template_match(self):
        """Test when template variables are subset of provided variables."""
        messages = [Message.with_text("Hello {{name}}")]
        variables = {
            "name": "John",
            "age": 25,  # Extra variable not used in template
            "city": "New York",  # Extra variable not used in template
        }

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        # Schema should only contain the variable used in template
        assert schema is not None
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert last_index == 0

    @pytest.mark.parametrize(
        "variables",
        [
            {"name": None},
            {"name": ""},
            {"items": []},
            {"config": {}},
        ],
    )
    def test_edge_case_variable_values(self, variables):
        """Test with edge case variable values like None, empty string, empty arrays."""
        key = next(iter(variables.keys()))
        messages = [Message.with_text(f"Value: {{{{{key}}}}}")]

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        assert schema is not None
        assert schema["type"] == "object"
        assert key in schema["properties"]
        assert last_index == 0

    def test_no_templated_messages_with_empty_variables(self):
        """Test with messages that have no templates and empty variables dict."""
        messages = [
            Message.with_text("Hello world"),
            Message.with_text("This is a test"),
        ]
        variables = {}

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        assert schema is None
        assert last_index == -1

    def test_mixed_templated_and_non_templated_messages(self):
        """Test with mix of templated and non-templated messages."""
        messages = [
            Message.with_text("Hello world"),  # No template
            Message.with_text("Welcome {{name}}"),  # Template
            Message.with_text("This is a test"),  # No template
            Message.with_text("Your age is {{age}}"),  # Template
        ]
        variables = {"name": "John", "age": 25}

        schema, last_index = json_schema_for_template_and_variables(messages, variables)

        assert schema is not None
        assert schema["type"] == "object"
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert last_index == 3  # Last templated message is at index 3

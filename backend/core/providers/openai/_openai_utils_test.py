from typing import Any

import pytest

from core.providers.openai._openai_utils import get_openai_json_schema_name, prepare_openai_json_schema
from tests.utils import fixtures_json


class TestSanitizeJSONSchema:
    def test_schema_1(self):
        raw = fixtures_json("jsonschemas", "schema_1.json")
        sanitized = prepare_openai_json_schema(raw)

        assert sanitized == {
            "$defs": {
                "CalendarEventCategory": {
                    "enum": ["UNSPECIFIED", "IN_PERSON_MEETING", "REMOTE_MEETING", "FLIGHT", "TO_DO", "BIRTHDAY"],
                    "type": "string",
                },
                "MeetingProvider": {
                    "enum": ["ZOOM", "GOOGLE_MEET", "MICROSOFT_TEAMS", "SKYPE", "OTHER"],
                    "type": "string",
                },
            },
            "description": 'The expected output of the EmailToCalendarProcessor. Each attribute corresponds to a question asked to the processor.\n\nThis class will be dynamically injected in the prompt as a "schema" for the LLM to enforce.',
            "properties": {
                "is_email_thread_about_an_event": {"type": "boolean"},
                "is_event_confirmed": {"anyOf": [{"type": "boolean"}, {"type": "null"}]},
                "event_category": {"anyOf": [{"$ref": "#/$defs/CalendarEventCategory"}, {"type": "null"}]},
                "is_event_all_day": {"type": "boolean"},
                "is_event_start_datetime_defined": {"anyOf": [{"type": "boolean"}, {"type": "null"}]},
                "event_start_datetime": {
                    "anyOf": [{"description": "format: date-time", "type": "string"}, {"type": "null"}],
                },
                "event_start_date": {"anyOf": [{"description": "format: date", "type": "string"}, {"type": "null"}]},
                "is_event_end_datetime_defined": {"anyOf": [{"type": "boolean"}, {"type": "null"}]},
                "event_end_datetime": {
                    "anyOf": [{"description": "format: date-time", "type": "string"}, {"type": "null"}],
                },
                "event_end_date": {"anyOf": [{"description": "format: date", "type": "string"}, {"type": "null"}]},
                "event_title": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "remote_meeting_provider": {"anyOf": [{"$ref": "#/$defs/MeetingProvider"}, {"type": "null"}]},
                "event_location_details": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "event_participants_emails_addresses": {
                    "anyOf": [{"items": {"type": "string"}, "type": "array"}, {"type": "null"}],
                },
            },
            "required": [
                "is_email_thread_about_an_event",
                "is_event_confirmed",
                "event_category",
                "is_event_all_day",
                "is_event_start_datetime_defined",
                "event_start_datetime",
                "event_start_date",
                "is_event_end_datetime_defined",
                "event_end_datetime",
                "event_end_date",
                "event_title",
                "remote_meeting_provider",
                "event_location_details",
                "event_participants_emails_addresses",
            ],
            "type": "object",
            "additionalProperties": False,
        }

    def test_schema_with_description_and_examples(self):
        raw = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the person", "examples": ["John", "Jane"]},
            },
        }
        sanitized = prepare_openai_json_schema(raw)
        assert sanitized == {
            "type": "object",
            "properties": {
                "name": {
                    "type": ["string", "null"],
                    "description": "The name of the person\nexamples: \nJohn\nJane",
                },
            },
            "required": ["name"],
            "additionalProperties": False,
        }

    def test_schema_with_non_supported_keys(self):
        raw = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the person", "format": "date-time"},
                "count": {
                    "type": "number",
                    # Using a falsy value to make sure it's included
                    "minimum": 0,
                    "maximum": 10,
                    "examples": [1, 2, 3],
                },
            },
        }
        sanitized = prepare_openai_json_schema(raw)
        assert sanitized == {
            "type": "object",
            "properties": {
                "name": {"type": ["string", "null"], "description": "The name of the person\nformat: date-time"},
                "count": {
                    "type": ["number", "null"],
                    "description": "examples: \n1\n2\n3\nminimum: 0\nmaximum: 10",
                },
            },
            "required": ["name", "count"],
            "additionalProperties": False,
        }

    def test_schema_with_description_and_examples_2(self) -> None:
        raw: dict[str, Any] = {
            "type": "object",
            "properties": {
                "animal_species": {
                    "description": "List of animal species extracted from the input text",
                    "type": "array",
                    "items": {
                        "description": "Name of an animal species",
                        "examples": ["elephant", "lion", "tiger", "snake"],
                        "type": "string",
                    },
                },
            },
        }
        sanitized: dict[str, Any] = prepare_openai_json_schema(raw)
        assert sanitized == {
            "type": "object",
            "properties": {
                "animal_species": {
                    "type": ["array", "null"],
                    "description": "List of animal species extracted from the input text",
                    "items": {
                        "description": ("Name of an animal species\nexamples: \nelephant\nlion\ntiger\nsnake"),
                        "type": "string",
                    },
                },
            },
            "required": ["animal_species"],
            "additionalProperties": False,
        }

    def test_schema_with_anyof(self) -> None:
        raw: dict[str, Any] = {
            "type": "object",
            "properties": {
                "item": {
                    "anyOf": [
                        {
                            "type": "object",
                            "description": "The user object to insert into the database",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "The name of the user",
                                },
                                "age": {
                                    "type": "number",
                                    "description": "The age of the user",
                                },
                            },
                            "additionalProperties": False,
                            "required": ["name", "age"],
                        },
                        {
                            "type": "object",
                            "description": "The address object to insert into the database",
                            "properties": {
                                "number": {
                                    "type": "string",
                                    "description": "The number of the address. Eg. for 123 main st, this would be 123",
                                },
                                "street": {
                                    "type": "string",
                                    "description": "The street name. Eg. for 123 main st, this would be main st",
                                },
                                "city": {
                                    "type": "string",
                                    "description": "The city of the address",
                                },
                            },
                            "additionalProperties": False,
                            "required": ["number", "street", "city"],
                        },
                    ],
                },
            },
            "additionalProperties": False,
            "required": ["item"],
        }

        sanitized = prepare_openai_json_schema(raw)
        expected: dict[str, Any] = {
            "type": "object",
            "properties": {
                "item": {
                    "anyOf": [
                        {
                            "type": "object",
                            "description": "The user object to insert into the database",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "The name of the user",
                                },
                                "age": {
                                    "type": "number",
                                    "description": "The age of the user",
                                },
                            },
                            "required": ["name", "age"],
                            "additionalProperties": False,
                        },
                        {
                            "type": "object",
                            "description": "The address object to insert into the database",
                            "properties": {
                                "number": {
                                    "type": "string",
                                    "description": "The number of the address. Eg. for 123 main st, this would be 123",
                                },
                                "street": {
                                    "type": "string",
                                    "description": "The street name. Eg. for 123 main st, this would be main st",
                                },
                                "city": {
                                    "type": "string",
                                    "description": "The city of the address",
                                },
                            },
                            "required": ["number", "street", "city"],
                            "additionalProperties": False,
                        },
                    ],
                },
            },
            "required": ["item"],
            "additionalProperties": False,
        }
        assert sanitized == expected

    def test_schema_with_description_and_format(self) -> None:
        raw: dict[str, Any] = {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "The date of the event", "format": "date-time"},
                "email": {"type": "string", "format": "email"},
            },
        }
        sanitized = prepare_openai_json_schema(raw)
        assert sanitized == {
            "type": "object",
            "properties": {
                "date": {"type": ["string", "null"], "description": "The date of the event\nformat: date-time"},
                "email": {"type": ["string", "null"], "description": "format: email"},
            },
            "required": ["date", "email"],
            "additionalProperties": False,
        }

    def test_schema_with_examples_and_format(self) -> None:
        raw: dict[str, Any] = {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": "string",
                    "description": "The timestamp",
                    "format": "date-time",
                    "examples": ["2024-03-14T12:00:00Z"],
                },
            },
        }
        sanitized = prepare_openai_json_schema(raw)
        assert sanitized == {
            "type": "object",
            "properties": {
                "timestamp": {
                    "type": ["string", "null"],
                    "description": "The timestamp\nformat: date-time\nexamples: \n2024-03-14T12:00:00Z",
                },
            },
            "required": ["timestamp"],
            "additionalProperties": False,
        }

    def test_schema_with_ref_and_defs_and_nested_defs(self) -> None:
        raw = {
            "type": "object",
            "properties": {
                "internal_agent_run_result": {
                    "default": None,  # FIX: delete extra params on field with $ref must be deleted
                    "description": "The status of the agent run, needs to be filled whether the run was successful or not",  # FIX: delete extra params on field with $ref must be deleted
                    "$ref": "#/$defs/AgentRunResult",
                },
                "internal_tool_calls": {
                    "description": "The list of tool calls to execute, before being able to compute the task output",
                    "items": {"$ref": "#/$defs/ToolCallResult"},
                    "title": "Internal Tool Calls",
                    "type": "array",
                },
                "answer": {"description": "The answer to the question based on the webpage content", "type": "string"},
            },
            "$defs": {
                "ToolCallResult": {
                    "properties": {
                        "tool_name": {
                            "description": "The name of the tool called",
                            "title": "Tool Name",
                            "type": "string",
                            "enum": ["@browser-text", "@search-google"],
                        },
                        "tool_input_dict": {
                            "description": "The input of the tool call",
                            "title": "Tool Input Dict",
                            "anyOf": [
                                {
                                    "type": "object",
                                    "properties": {"url": {"type": "string"}},
                                    "required": ["url"],
                                    "description": "Input for the '@browser-text' tool",
                                },
                                {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}},
                                    "required": ["query"],
                                    "description": "Input for the '@search-google' tool",
                                },
                            ],
                        },
                    },
                    "required": ["tool_name", "tool_input_dict"],
                    "title": "ToolCallResult",
                    "type": "object",
                },
                "AgentRunError": {
                    "properties": {
                        "error_code": {
                            "default": None,
                            "description": "The type of error that occurred during the agent run, 'tool_call_error' if an error occurred during a tool call, 'missing_tool' if the agent is missing a tool in order to complete the run, 'other' for any other error",
                            "title": "Error Code",
                            "enum": ["tool_call_error", "missing_tool", "other"],
                            "type": "string",
                        },
                        "error_message": {
                            "default": None,
                            "description": "A summary of the error that occurred during the agent run",
                            "title": "Error Message",
                            "type": "string",
                        },
                    },
                    "title": "AgentRunError",
                    "type": "object",
                },
                "AgentRunResult": {
                    "properties": {
                        "status": {
                            "default": None,
                            "description": "Whether the agent run was successful or not",
                            "title": "Status",
                            "enum": ["success", "failure"],
                            "type": "string",
                        },
                        "error_1": {
                            "default": None,
                            "description": "The error that occurred during the agent run, to fill in case of status='failure'",
                            "$ref": "#/$defs/AgentRunError",
                        },
                        "error_2": {
                            "default": None,
                            "description": "The error that occurred during the agent run, to fill in case of status='failure'",
                            "$ref": "#/$defs/AgentRunError",
                        },
                    },
                    "title": "AgentRunResult",
                    "type": "object",
                },
            },
        }

        expected = {
            "type": "object",
            "properties": {
                "internal_agent_run_result": {
                    # All other properties were deleted
                    "$ref": "#/$defs/AgentRunResult",
                },
                "internal_tool_calls": {
                    "description": "The list of tool calls to execute, before being able to compute the task output",
                    "items": {
                        "$ref": "#/$defs/ToolCallResult",
                    },
                    "type": [
                        "array",
                        "null",
                    ],
                },
                "answer": {
                    "description": "The answer to the question based on the webpage content",
                    "type": [
                        "string",
                        "null",
                    ],
                },
            },
            "$defs": {
                "ToolCallResult": {
                    "properties": {
                        "tool_name": {
                            "description": "The name of the tool called",
                            "type": "string",
                            "enum": [
                                "@browser-text",
                                "@search-google",
                            ],
                        },
                        "tool_input_dict": {
                            "description": "The input of the tool call",
                            "anyOf": [
                                {
                                    "type": "object",
                                    "properties": {
                                        "url": {
                                            "type": "string",
                                        },
                                    },
                                    "required": [
                                        "url",
                                    ],
                                    "description": "Input for the '@browser-text' tool",
                                    "additionalProperties": False,
                                },
                                {
                                    "type": "object",
                                    "properties": {"query": {"type": "string"}},
                                    "required": ["query"],
                                    "description": "Input for the '@search-google' tool",
                                    "additionalProperties": False,
                                },
                            ],
                        },
                    },
                    "required": [
                        "tool_name",
                        "tool_input_dict",
                    ],
                    "type": "object",
                    "additionalProperties": False,
                },  # AgentRunError was deleted
                "AgentRunResult": {
                    "properties": {
                        "status": {
                            "description": "Whether the agent run was successful or not",
                            "enum": [
                                "success",
                                "failure",
                            ],
                            "type": [
                                "string",
                                "null",
                            ],
                        },
                        "error_1": {  # AgentRunError schema was directly injected
                            "properties": {
                                "error_code": {
                                    "description": "The type of error that occurred during the agent run, 'tool_call_error' if an error occurred during a tool call, 'missing_tool' if the agent is missing a tool in order to complete the run, 'other' for any other error",
                                    "enum": [
                                        "tool_call_error",
                                        "missing_tool",
                                        "other",
                                    ],
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                                "error_message": {
                                    "description": "A summary of the error that occurred during the agent run",
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                            },
                            "type": "object",
                            "required": [
                                "error_code",
                                "error_message",
                            ],
                            "additionalProperties": False,
                        },
                        "error_2": {  # AgentRunError schema was directly injected
                            "properties": {
                                "error_code": {
                                    "description": "The type of error that occurred during the agent run, 'tool_call_error' if an error occurred during a tool call, 'missing_tool' if the agent is missing a tool in order to complete the run, 'other' for any other error",
                                    "enum": [
                                        "tool_call_error",
                                        "missing_tool",
                                        "other",
                                    ],
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                                "error_message": {
                                    "description": "A summary of the error that occurred during the agent run",
                                    "type": [
                                        "string",
                                        "null",
                                    ],
                                },
                            },
                            "type": "object",
                            "required": [
                                "error_code",
                                "error_message",
                            ],
                            "additionalProperties": False,
                        },
                    },
                    "type": "object",
                    "required": [
                        "status",
                        "error_1",
                        "error_2",
                    ],
                    "additionalProperties": False,
                },
            },
            "required": [
                "internal_agent_run_result",
                "internal_tool_calls",
                "answer",
            ],
            "additionalProperties": False,
        }

        sanitized = prepare_openai_json_schema(raw)
        assert sanitized == expected


class TestOpenAIJsonSchemaName:
    def test_schema_name_length(self) -> None:
        # Test with a very long task name
        long_task_name = "This_Is_A_Very_Long_Task_Name_That_Should_Be_Truncated_To_Fit_The_Limit"
        schema: dict[str, Any] = {"type": "object", "properties": {"test": {"type": "string"}}}

        result = get_openai_json_schema_name(long_task_name, schema)

        assert result == "this_is_a_very_long_task_na_3f333da9e73b43eb835392a798a7a667"
        assert len(result) == 60

    @pytest.mark.parametrize(
        ("task_name", "schema", "expected"),
        [
            pytest.param("test", {"type": "object"}, "test_a7515052692371909964e67c28b18a0a", id="test"),
            pytest.param(
                "[ACE] Study Notes Generation",
                {"type": "object"},
                "ace_study_notes_generation_a7515052692371909964e67c28b18a0a",
                id="ace_study_notes_generation",
            ),
        ],
    )
    def test_schema_name(self, task_name: str, schema: dict[str, Any], expected: str):
        result = get_openai_json_schema_name(task_name, schema)
        assert result == expected

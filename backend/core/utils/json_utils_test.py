from typing import Any

import pytest

from core.utils.json_utils import extract_json_str, parse_tolerant_json, safe_extract_dict_from_json


@pytest.mark.parametrize(
    ("json_str", "expected"),
    [
        (  # Unescaped quotes
            '{"hello": "hell"o"}',
            {
                "hello": 'hell"o',
            },
        ),
        (  # Unescaped quotes
            '{"text": "I said "OK""}',
            {
                "text": 'I said "OK"',
            },
        ),
        ('{"foo": "bar"}', {"foo": "bar"}),  # No quotes
    ],
)
async def test_parse_tolerant_json(json_str: str, expected: dict[str, Any]) -> None:
    assert parse_tolerant_json(json_str) == expected


class TestExtractJSONStr:
    def test_extract_properly_formatted_nested_json(self):
        input_text = 'This is some text. {"name": "John", "age": 30, "address": {"street": "Main St", "city": "Metropolis"}} More text.'
        expected_output = '{"name": "John", "age": 30, "address": {"street": "Main St", "city": "Metropolis"}}'

        result = extract_json_str(input_text)

        assert result == expected_output

    # Same as above, but with a JSON delimiter (```json) before and after the JSON block.
    def test_extract_properly_formatted_nested_json_with_json_delimiter(self):
        input_text = 'This is some text. ```json{"name": "John", "age": 30, "address": {"street": "Main St", "city": "Metropolis"}}``` More text.'
        expected_output = '{"name": "John", "age": 30, "address": {"street": "Main St", "city": "Metropolis"}}'

        result = extract_json_str(input_text)

        assert result == expected_output

    # Raises ValueError if no JSON is found in input text
    def test_raises_value_error_no_json_found(self):
        input_text = "This is some text without any JSON."

        with pytest.raises(ValueError):  # noqa: PT011
            _ = extract_json_str(input_text)

    # Handles input text with leading/trailing whitespace around nested JSON
    def test_handles_whitespace_around_nested_json(self):
        input_text = '   {"name": "John", "age": 30, "address": {"street": "Main St", "city": "Metropolis"}}   '
        expected_output = '{"name": "John", "age": 30, "address": {"street": "Main St", "city": "Metropolis"}}'

        result = extract_json_str(input_text)

        assert result == expected_output

    # Same as above, but with a JSON delimiter (```json) before and after the JSON block.
    def test_handles_whitespace_around_nested_json_with_json_delimiter(self):
        input_text = (
            '   ```json{"name": "John", "age": 30, "address": {"street": "Main St", "city": "Metropolis"}}```   '
        )
        expected_output = '{"name": "John", "age": 30, "address": {"street": "Main St", "city": "Metropolis"}}'

        result = extract_json_str(input_text)

        assert result == expected_output


class TestSafeExtractDictFromJson:
    def test_with_dict_input(self) -> None:
        input_dict = {"key": "value", 1: 2}
        expected = {"key": "value", "1": 2}

        result = safe_extract_dict_from_json(input_dict)

        assert result == expected

    def test_with_json_string_input(self) -> None:
        input_str = '{"key": "value", "num": 42}'
        expected = {"key": "value", "num": 42}

        result = safe_extract_dict_from_json(input_str)

        assert result == expected

    def test_with_non_dict_json(self) -> None:
        input_str = "[1, 2, 3]"

        result = safe_extract_dict_from_json(input_str)

        assert result is None

    def test_with_invalid_json(self) -> None:
        input_str = "{invalid json}"

        result = safe_extract_dict_from_json(input_str)

        assert result is None

    def test_with_none_input(self) -> None:
        result = safe_extract_dict_from_json(None)

        assert result is None

    def test_with_non_string_non_dict_input(self) -> None:
        result = safe_extract_dict_from_json(42)

        assert result is None

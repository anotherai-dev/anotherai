# pyright: reportPrivateUsage=false

from protocol.api._api_models import Message
from protocol.api._services.playground_service import _extract_input_from_prompts


class TestExtractInputFromPrompts:
    def test_common_system_message_extracted_as_prompt(self):
        """Test that when all prompts start with the same system message, it's extracted as version.prompt."""
        system_message = Message(role="system", content="You are a helpful assistant.")
        user_message_1 = Message(role="user", content="What is 2+2?")
        user_message_2 = Message(role="user", content="What is 3+3?")

        prompts = [
            [system_message, user_message_1],
            [system_message, user_message_2],
        ]

        extracted_prompts, inputs = _extract_input_from_prompts(prompts)

        # The common system message should be extracted as the prompt
        assert len(extracted_prompts) == 1
        assert len(extracted_prompts[0]) == 1
        assert extracted_prompts[0][0] == system_message

        # The remaining messages should be in inputs
        assert len(inputs) == 2
        assert inputs[0].messages == [user_message_1]
        assert inputs[1].messages == [user_message_2]

    def test_common_developer_message_extracted_as_prompt(self):
        """Test that when all prompts start with the same developer message, it's extracted as version.prompt."""
        developer_message = Message(role="developer", content="System configuration: debug mode enabled")
        user_message_1 = Message(role="user", content="Debug this code")
        user_message_2 = Message(role="user", content="Debug this other code")

        prompts = [
            [developer_message, user_message_1],
            [developer_message, user_message_2],
        ]

        extracted_prompts, inputs = _extract_input_from_prompts(prompts)

        # The common developer message should be extracted as the prompt
        assert len(extracted_prompts) == 1
        assert len(extracted_prompts[0]) == 1
        assert extracted_prompts[0][0] == developer_message

        # The remaining messages should be in inputs
        assert len(inputs) == 2
        assert inputs[0].messages == [user_message_1]
        assert inputs[1].messages == [user_message_2]

    def test_different_first_messages_no_extraction(self):
        """Test that when prompts have different first messages, no common prompt is extracted."""
        system_message_1 = Message(role="system", content="You are a math tutor.")
        system_message_2 = Message(role="system", content="You are a science tutor.")
        user_message_1 = Message(role="user", content="What is 2+2?")
        user_message_2 = Message(role="user", content="What is gravity?")

        prompts = [
            [system_message_1, user_message_1],
            [system_message_2, user_message_2],
        ]

        extracted_prompts, inputs = _extract_input_from_prompts(prompts)

        # No common prompt should be extracted
        assert len(extracted_prompts) == 0

        # All messages should be in inputs
        assert len(inputs) == 2
        assert inputs[0].messages == [system_message_1, user_message_1]
        assert inputs[1].messages == [system_message_2, user_message_2]

    def test_user_first_message_no_extraction(self):
        """Test that when first message is user role, no common prompt is extracted."""
        user_message_1 = Message(role="user", content="What is 2+2?")
        user_message_2 = Message(role="user", content="What is 3+3?")

        prompts = [
            [user_message_1],
            [user_message_2],
        ]

        extracted_prompts, inputs = _extract_input_from_prompts(prompts)

        # No common prompt should be extracted (first message is user, not system/developer)
        assert len(extracted_prompts) == 0

        # All messages should be in inputs
        assert len(inputs) == 2
        assert inputs[0].messages == [user_message_1]
        assert inputs[1].messages == [user_message_2]

    def test_assistant_first_message_no_extraction(self):
        """Test that when first message is assistant role, no common prompt is extracted."""
        assistant_message_1 = Message(role="assistant", content="Hello, how can I help?")
        user_message_1 = Message(role="user", content="What is 2+2?")

        prompts = [
            [assistant_message_1, user_message_1],
        ]

        extracted_prompts, inputs = _extract_input_from_prompts(prompts)

        # No common prompt should be extracted (first message is assistant, not system/developer)
        assert len(extracted_prompts) == 0

        # All messages should be in inputs
        assert len(inputs) == 1
        assert inputs[0].messages == [assistant_message_1, user_message_1]

    def test_single_prompt_with_system_message(self):
        """Test that a single prompt with system message is handled correctly."""
        system_message = Message(role="system", content="You are a helpful assistant.")
        user_message = Message(role="user", content="What is 2+2?")

        prompts = [
            [system_message, user_message],
        ]

        extracted_prompts, inputs = _extract_input_from_prompts(prompts)

        # The system message should be extracted as the prompt
        assert len(extracted_prompts) == 1
        assert len(extracted_prompts[0]) == 1
        assert extracted_prompts[0][0] == system_message

        # The remaining messages should be in inputs
        assert len(inputs) == 1
        assert inputs[0].messages == [user_message]

    def test_single_prompt_without_system_message(self):
        """Test that a single prompt without system message is handled correctly."""
        user_message = Message(role="user", content="What is 2+2?")

        prompts = [
            [user_message],
        ]

        extracted_prompts, inputs = _extract_input_from_prompts(prompts)

        # No common prompt should be extracted
        assert len(extracted_prompts) == 0

        # All messages should be in inputs
        assert len(inputs) == 1
        assert inputs[0].messages == [user_message]

    def test_partial_match_different_second_messages(self):
        """Test that only the first message needs to match for extraction."""
        system_message = Message(role="system", content="You are a helpful assistant.")
        user_message_1 = Message(role="user", content="What is 2+2?")
        user_message_2 = Message(role="user", content="What is 3+3?")
        assistant_message = Message(role="assistant", content="I can help with that.")

        prompts = [
            [system_message, user_message_1, assistant_message],
            [system_message, user_message_2],  # Different length, but same first message
        ]

        extracted_prompts, inputs = _extract_input_from_prompts(prompts)

        # The common system message should be extracted as the prompt
        assert len(extracted_prompts) == 1
        assert len(extracted_prompts[0]) == 1
        assert extracted_prompts[0][0] == system_message

        # The remaining messages should be in inputs
        assert len(inputs) == 2
        assert inputs[0].messages == [user_message_1, assistant_message]
        assert inputs[1].messages == [user_message_2]

    def test_tool_role_first_message_no_extraction(self):
        """Test that when first message is tool role, no common prompt is extracted."""
        tool_message = Message(role="tool", content="Tool result: success")
        user_message = Message(role="user", content="What happened?")

        prompts = [
            [tool_message, user_message],
        ]

        extracted_prompts, inputs = _extract_input_from_prompts(prompts)

        # No common prompt should be extracted (first message is tool, not system/developer)
        assert len(extracted_prompts) == 0

        # All messages should be in inputs
        assert len(inputs) == 1
        assert inputs[0].messages == [tool_message, user_message]

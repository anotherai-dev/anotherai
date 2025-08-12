from core.domain.message import MessageDeprecated
from core.domain.tool_call import ToolCallRequest, ToolCallResult
from core.providers.groq.groq_domain import GroqMessage, _ToolCall  # pyright: ignore [reportPrivateUsage]


class TestGroqMessageFromDomain:
    def test_groq_message_from_domain(self) -> None:
        messages = [
            MessageDeprecated(content="Hello you", role=MessageDeprecated.Role.SYSTEM),
            MessageDeprecated(content="What is the current time ?", role=MessageDeprecated.Role.USER),
            MessageDeprecated(
                content="",
                tool_call_requests=[
                    ToolCallRequest(
                        id="1",
                        tool_name="get_current_time",
                        tool_input_dict={"timezone": "Europe/Paris"},
                    ),
                ],
                role=MessageDeprecated.Role.ASSISTANT,
            ),
            MessageDeprecated(
                content="",
                tool_call_results=[
                    ToolCallResult(
                        id="1",
                        tool_name="get_current_time",
                        tool_input_dict={"timezone": "Europe/Paris"},
                        result="2021-01-01 12:00:00",
                    ),
                ],
                role=MessageDeprecated.Role.USER,
            ),
        ]
        groq_messages: list[GroqMessage] = []
        for m in messages:
            groq_messages.extend(GroqMessage.from_domain(m))
        assert groq_messages == [
            GroqMessage(content="Hello you", role="system"),
            GroqMessage(content="What is the current time ?", role="user"),
            GroqMessage(
                role="assistant",
                tool_calls=[
                    _ToolCall(
                        id="1",
                        function=_ToolCall.Function(
                            name="get_current_time",
                            arguments='{"timezone": "Europe/Paris"}',
                        ),
                    ),
                ],
            ),
            GroqMessage(
                role="tool",
                content="2021-01-01 12:00:00",
                tool_call_id="1",
            ),
        ]

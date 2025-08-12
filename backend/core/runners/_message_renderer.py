import asyncio
from typing import Any

from core.domain.message import Message, MessageContent
from core.utils.templates import TemplateManager


class MessageRenderer:
    def __init__(
        self,
        template_manager: TemplateManager,
        variables: dict[str, Any],
        prompt: list[Message],
    ):
        self._template_manager = template_manager
        self._variables = variables
        self._prompt = prompt

    async def _render_text(self, text: str | None):
        if not text:
            return None

        return await self._template_manager.render_template(text, self._variables)

    async def render_content(self, content: MessageContent):
        update: dict[str, Any] = {}

        if (text := await self._render_text(content.text)) is not None:
            update["text"] = text[0]

        if update:
            return content.model_copy(update=update)
        return content

    async def render_message(self, message: Message):
        return Message(
            role=message.role,
            content=[await self.render_content(c) for c in message.content],
        )

    async def render_prompt(self) -> list[Message]:
        try:
            return await asyncio.gather(*[self.render_message(m) for m in self._prompt])
        except* Exception as e:
            # Raise the first exception to avoid masking the underlying exception in an
            # exception group
            raise e.exceptions[0] from e

    @classmethod
    async def render(
        cls,
        template_manager: TemplateManager,
        variables: dict[str, Any] | None = None,
        prompt: list[Message] | None = None,
    ) -> list[Message]:
        if not prompt or not variables:
            return []

        return await cls(template_manager, variables, prompt).render_prompt()

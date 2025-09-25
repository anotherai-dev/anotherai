import asyncio
from typing import Any

from core.domain.exceptions import BadRequestError
from core.domain.file import File
from core.domain.message import Message, MessageContent
from core.utils.templates import TemplateManager, TemplateRenderingError


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

    async def _render_str(self, value: str | None):
        if not value:
            return None
        try:
            t, _ = await self._template_manager.render_template(value, self._variables)
            return t
        except TemplateRenderingError as e:
            raise BadRequestError(str(e)) from e

    async def _render_text(self, text: str | None):
        if not text:
            return None
        try:
            return await self._template_manager.render_template(text, self._variables)
        except TemplateRenderingError as e:
            raise BadRequestError(str(e)) from e

    async def _render_file(self, file: File):
        new_file = file.model_copy(
            update={
                "url": await self._render_str(file.url),
                "data": await self._render_str(file.data),
                "content_type": await self._render_str(file.content_type),
            },
        )
        try:
            return new_file.sanitize()
        except ValueError as e:
            raise BadRequestError(str(e)) from e

    async def render_content(self, content: MessageContent):
        update: dict[str, Any] = {}

        if (text := await self._render_str(content.text)) is not None:
            update["text"] = text
        if content.file:
            update["file"] = await self._render_file(content.file)

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

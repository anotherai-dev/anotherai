# pyright: reportPrivateUsage=false


import pytest

from core.domain.exceptions import BadRequestError
from core.domain.file import File
from core.domain.message import MessageContent
from core.runners._message_renderer import MessageRenderer
from core.utils.templates import TemplateManager


@pytest.fixture
def message_renderer():
    return MessageRenderer(
        template_manager=TemplateManager(),
        variables={"name": "hello", "data": "data", "url": "https://example.com", "image_type": "png"},
        prompt=[],
    )


class TestRenderFile:
    @pytest.mark.parametrize(
        ("incoming", "expected"),
        [
            (File(url="{{url}}"), File(url="https://example.com")),
            (File(data="{{data}}", content_type="image/{{image_type}}"), File(data="data", content_type="image/png")),
        ],
    )
    async def test_success(self, message_renderer: MessageRenderer, incoming: File, expected: File):
        assert await message_renderer._render_file(incoming) == expected

    @pytest.mark.parametrize(
        ("incoming"),
        [
            File(url="file://{{url}}"),
            File(data="b{{data}}"),
        ],
    )
    async def test_failure(self, message_renderer: MessageRenderer, incoming: File):
        with pytest.raises(BadRequestError):
            await message_renderer._render_file(incoming)


class TestRenderContent:
    @pytest.mark.parametrize(
        ("incoming", "expected"),
        [
            (
                MessageContent(text="Hello {{name}}"),
                MessageContent(text="Hello hello"),
            ),
            (
                MessageContent(text="Visit {{url}}"),
                MessageContent(text="Visit https://example.com"),
            ),
            (
                MessageContent(text="No variables here"),
                MessageContent(text="No variables here"),
            ),
            (
                MessageContent(text="{{name}} - {{data}}"),
                MessageContent(text="hello - data"),
            ),
            (
                MessageContent(
                    text="Check {{url}}",
                    file=File(url="{{url}}"),
                ),
                MessageContent(
                    text="Check https://example.com",
                    file=File(url="https://example.com"),
                ),
            ),
            (
                MessageContent(
                    text="Image {{name}}",
                    file=File(data="{{data}}", content_type="image/{{image_type}}"),
                ),
                MessageContent(
                    text="Image hello",
                    file=File(data="data", content_type="image/png"),
                ),
            ),
            (
                MessageContent(file=File(url="{{url}}")),
                MessageContent(file=File(url="https://example.com")),
            ),
            (
                MessageContent(text=None),
                MessageContent(text=None),
            ),
            (
                MessageContent(text=""),
                MessageContent(text=""),
            ),
        ],
    )
    async def test_render_content_success(
        self,
        message_renderer: MessageRenderer,
        incoming: MessageContent,
        expected: MessageContent,
    ):
        result = await message_renderer.render_content(incoming)
        assert result == expected

    async def test_render_content_with_invalid_file(self, message_renderer: MessageRenderer):
        content = MessageContent(
            text="Test {{name}}",
            file=File(url="file://{{url}}"),  # Invalid file URL
        )
        with pytest.raises(BadRequestError):
            await message_renderer.render_content(content)

    async def test_render_content_preserves_missing_variable(self):
        renderer = MessageRenderer(
            template_manager=TemplateManager(),
            variables={"name": "hello"},  # Missing 'missing_var'
            prompt=[],
        )
        content = MessageContent(text="Hello {{missing_var}}")
        result = await renderer.render_content(content)
        assert result.text == "Hello "

    async def test_render_content_no_updates(self, message_renderer: MessageRenderer):
        content = MessageContent(text=None, file=None)
        result = await message_renderer.render_content(content)
        assert result == content
        assert result is content  # Should return the same instance if no updates

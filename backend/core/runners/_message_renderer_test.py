# pyright: reportPrivateUsage=false


import pytest

from core.domain.exceptions import BadRequestError
from core.domain.file import File
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

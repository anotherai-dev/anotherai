import base64
import mimetypes
import re
from base64 import b64decode
from enum import StrEnum
from urllib.parse import parse_qs, urlparse

import httpx
import structlog
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from core.domain.exceptions import InternalError, InvalidFileError
from core.utils.files import guess_content_type

log = structlog.get_logger(__name__)


class FileKind(StrEnum):
    DOCUMENT = "document"  # includes text, pdfs and images
    IMAGE = "image"
    AUDIO = "audio"
    PDF = "pdf"
    ANY = "any"


class File(BaseModel):
    content_type: str | None = Field(
        default=None,
        description="The content type of the file",
        examples=["image/png", "image/jpeg", "audio/wav", "application/pdf"],
    )
    data: str | None = Field(default=None, description="The base64 encoded data of the file")
    url: str | None = Field(default=None, description="The URL of the image")

    format: SkipJsonSchema[FileKind | str | None] = Field(
        default=None,
    )

    storage_url: str | None = Field(default=None, description="The URL of the file in the storage")

    @property
    def is_image(self) -> bool | None:
        if self.content_type:
            return self.content_type.startswith("image/")
        if self.format is None:
            return None
        return self.format == "image"

    @property
    def is_audio(self) -> bool | None:
        if self.content_type:
            return self.content_type.startswith("audio/")
        if self.format is None:
            return None
        return self.format == "audio"

    @property
    def is_video(self) -> bool | None:
        if not self.content_type:
            return None
        return self.content_type.startswith("video/")

    @property
    def is_pdf(self) -> bool | None:
        if self.content_type:
            return self.content_type == "application/pdf"
        if self.format is None:
            return None
        return self.format == "pdf"

    @property
    def is_text(self) -> bool | None:
        if not self.content_type:
            return None
        return self.content_type in ["text/plain", "text/markdown", "text/csv", "text/json", "text/html"]

    def get_extension(self) -> str:
        if self.content_type:
            return mimetypes.guess_extension(self.content_type) or ""
        return ""

    def content_bytes(self) -> bytes | None:
        if self.data:
            return b64decode(self.data)
        return None

    def templatable_content(self) -> str:
        return " ".join(k for k in (self.url, self.data, self.content_type) if k)

    def to_url(self, default_content_type: str | None = None) -> str:
        if self.data and (self.content_type or default_content_type):
            return f"data:{self.content_type or default_content_type};base64,{self.data}"
        if self.url:
            return self.url

        raise InternalError("No data or URL provided for image")

    @classmethod
    async def _fetch_with_retries(cls, client: httpx.AsyncClient, url: str, retries: int = 2) -> httpx.Response:
        try:
            return await client.get(url)
        except (
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.ReadError,
            httpx.ConnectError,
            httpx.RemoteProtocolError,
        ) as e:
            if retries <= 0:
                raise InvalidFileError(
                    f"Failed to download file: {e}",
                    capture=False,
                ) from e
            return await cls._fetch_with_retries(client, url, retries - 1)

    async def download(self):
        if not self.url:
            raise InvalidFileError("File url is required when data is not provided")

        async with httpx.AsyncClient() as client:
            response = await self._fetch_with_retries(client, self.url)

        if response.status_code != 200:
            raise InvalidFileError(
                f"Failed to file image: {response.status_code}",
                file_url=self.url,
                details={"response_status_code": response.status_code, "response_body": response.text},
            )

        self.data = base64.b64encode(response.content).decode("utf-8")

        if self.content_type is None:
            self.content_type = guess_content_type(response.content)
            if self.content_type is None:
                log.warning("Could not guess content type of url", url=self.url)

    def _validate_url_and_set_content_type(self, url: str):
        if url.startswith("data:"):
            content_type, data = _parse_data_url(url[5:])
            self.content_type = content_type
            _validate_base64(data)
            self.data = data
            self.url = None
            return

        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid URL provided for file: {e}") from e

        if parsed.scheme not in {"http", "https"}:
            raise ValueError("URL must have a http or https scheme")

        if self.content_type:
            return

        if parsed.query:
            query_params = parse_qs(parsed.query)
            if "content_type" in query_params:
                self.content_type = query_params["content_type"][0]
                return

        if mime_type := mimetypes.guess_type(url, strict=False)[0]:
            self.content_type = mime_type

    def sanitize(self):
        if self.data:
            decoded_data = _validate_base64(self.data)
            if not self.content_type:
                self.content_type = guess_content_type(decoded_data)
            return self
        if self.url:
            self._validate_url_and_set_content_type(self.url)
            return self

        raise ValueError("No data or URL provided for image")


_template_var_regexp = re.compile(r"\{\{([^}]+)\}\}")


def _validate_base64(data: str) -> bytes:
    # TODO: maybe we do not need to decode the data here, just check the padding
    # That's a lot of memory usage for no reason
    try:
        return b64decode(data)
    except Exception as e:
        raise ValueError("Invalid base64 data in file") from e


def _parse_data_url(data_url: str) -> tuple[str, str]:
    splits = data_url.split(";base64,")
    if len(splits) != 2:
        raise ValueError("Invalid base64 data URL")
    return splits[0], splits[1]

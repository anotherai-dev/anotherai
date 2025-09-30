import base64

from fastapi import UploadFile

from core.domain.exceptions import EntityTooLargeError
from core.domain.file import File
from core.storage.file_storage import FileStorage
from protocol.api._api_models import UploadFileResponse

_1_MB = 1024 * 1024


class FilesService:
    def __init__(self, file_storage: FileStorage):
        self.file_storage = file_storage

    async def _read_with_max_size(self, file: UploadFile, chunk_size: int, max_size: int) -> bytes:
        data = b""
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            data += chunk
            if len(data) > max_size:
                raise EntityTooLargeError(f"File size exceeds the maximum allowed size of {max_size} bytes")
        return data

    async def upload_file(self, file: UploadFile) -> UploadFileResponse:
        data = await self._read_with_max_size(file, _1_MB // 2, _1_MB * 20)
        encoded = base64.b64encode(data).decode("utf-8")
        to_upload = File(
            data=encoded,
            content_type=file.content_type,
        )
        # TODO: expires at
        url = await self.file_storage.store_file(to_upload, "tmp")
        return UploadFileResponse(
            url=url,
        )

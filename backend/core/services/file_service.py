import asyncio
from collections.abc import Iterable

import structlog

from core.domain.exceptions import InvalidFileError
from core.domain.file import File
from core.storage.file_storage import FileStorage
from core.utils.coroutines import capture_errors
from core.utils.hash import hash_string

_log = structlog.get_logger(__name__)


# TODO: test
class FileService:
    def __init__(self, file_storage: FileStorage):
        self._file_storage = file_storage

    async def _download_file(self, key: str, file: File, storage_urls: dict[str, str], root_path: str):
        if not file.data:
            if not file.url:
                raise InvalidFileError("File url is required when data is not provided")

            await file.download()

        with capture_errors(_log, "Error downloading file"):
            storage_urls[key] = await self._file_storage.store_file(file, root_path)

    async def store_files(self, files: Iterable[File], root_path: str):
        unique_files: dict[str, File] = {}
        all_files: list[File] = []

        for file in files:
            if file.storage_url:
                continue

            unique_files[_file_cache_key(file)] = file
            all_files.append(file)

        _storage_urls: dict[str, str] = {}

        async with asyncio.TaskGroup() as tg:
            for key, file in unique_files.items():
                tg.create_task(self._download_file(key, file, _storage_urls, root_path))

        for file in all_files:
            if storage_url := _storage_urls.get(_file_cache_key(file)):
                file.storage_url = storage_url
                # Overriding file url if it is a data url or not set
                if not file.url or file.url.startswith("data:"):
                    file.url = file.storage_url
            if file.url:
                file.data = None


def _file_cache_key(file: File) -> str:
    return file.url or hash_string(file.data or "")

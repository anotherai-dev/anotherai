from typing import Protocol

from core.domain.file import File


class CouldNotStoreFileError(Exception):
    pass


class FileStorage(Protocol):
    async def store_file(self, file: File, folder: str) -> str: ...

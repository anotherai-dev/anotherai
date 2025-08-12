import base64
import hashlib
import mimetypes
from typing import override

from azure.core.exceptions import ResourceExistsError
from azure.core.pipeline.transport import AioHttpTransport
from azure.storage.blob.aio import BlobClient, BlobServiceClient

from core.domain.file import File
from core.storage.file_storage import CouldNotStoreFileError, FileStorage


class AzureBlobFileStorage(FileStorage):
    def __init__(self, connection_string: str, container_name: str, tenant_uid: int):
        self.connection_string = connection_string
        self.container_name = container_name
        self.tenant_uid = tenant_uid

    async def _get_blob_service_client(self) -> BlobServiceClient:
        return BlobServiceClient.from_connection_string(
            self.connection_string,
            # TODO: refine these settings after monitoring performance
            transport=AioHttpTransport(
                connection_timeout=300.0,
                read_timeout=300.0,
                retries=3,
                maximum_valid_request_size=500 * 1024 * 1024,
            ),
        )

    @override
    async def store_file(self, file: File, folder: str) -> str:
        if not file.data:
            await file.download()
        if not file.data:
            raise CouldNotStoreFileError("File data is required")

        bs = base64.b64decode(file.data.encode())
        content_hash = hashlib.sha256(bs).hexdigest()
        extension = mimetypes.guess_extension(file.content_type) if file.content_type else None
        blob_name = f"{self.tenant_uid}/{folder}/{content_hash}{extension or ''}"

        async with await self._get_blob_service_client() as blob_service_client:
            try:
                blob_client: BlobClient = blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=blob_name,
                )

                try:
                    await blob_client.upload_blob(
                        bs,
                        content_type=file.content_type,
                        overwrite=False,
                    )
                    return blob_client.url  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
                except ResourceExistsError:
                    # If the file already exists, we don't need to do anything
                    return blob_client.url  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            except Exception as e:
                raise CouldNotStoreFileError("Error while uploading blob") from e

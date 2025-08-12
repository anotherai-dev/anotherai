import asyncio
import base64
import hashlib
import logging
import mimetypes
from typing import override
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError

from core.domain.file import File
from core.storage.file_storage import CouldNotStoreFileError, FileStorage


class S3FileStorage(FileStorage):
    def __init__(self, connection_string: str, tenant_uid: int):
        parsed = urlparse(connection_string)
        host = parsed.hostname
        port = parsed.port
        insecure = "secure=false" in parsed.query.lower()
        self.host = f"{'http' if insecure else 'https'}://{host}"
        if port:
            self.host += f":{port}"
        self.bucket_name = parsed.path.lstrip("/")
        self._logger = logging.getLogger(__name__)
        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self.host,
            aws_access_key_id=parsed.username,
            aws_secret_access_key=parsed.password,
        )
        self._tenant_uid = tenant_uid

    def _put_object(self, key: str, body: bytes, content_type: str):
        self._s3_client.put_object(
            Bucket=self.bucket_name,
            Key=f"{self._tenant_uid}/{key}",
            Body=body,
            ContentType=content_type,
        )

    @override
    async def store_file(self, file: File, folder: str) -> str:
        # Generate a unique filename using content hash
        if not file.data:
            await file.download()
        if not file.data:
            raise CouldNotStoreFileError("File data is required")

        bs = base64.b64decode(file.data.encode())
        content_hash = hashlib.sha256(bs).hexdigest()

        extension = mimetypes.guess_extension(file.content_type) if file.content_type else None
        key = f"{folder}/{content_hash}{extension or ''}"

        try:
            await asyncio.get_running_loop().run_in_executor(
                None,
                self._put_object,
                key,
                bs,
                file.content_type or "application/octet-stream",
            )

            return f"{self.host}/{self.bucket_name}/{self._tenant_uid}/{key}"
        except ClientError as e:
            raise CouldNotStoreFileError("Failed to store file in S3") from e

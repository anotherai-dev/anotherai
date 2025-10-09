import asyncio
import base64
import hashlib
import mimetypes
from typing import NamedTuple, override
from urllib.parse import parse_qs, urlparse

import boto3
import structlog
from botocore.exceptions import ClientError

from core.domain.file import File
from core.storage.file_storage import CouldNotStoreFileError, FileStorage

_log = structlog.get_logger(__name__)


class S3FileStorage(FileStorage):
    def __init__(self, connection_string: str, tenant_uid: int):
        self._config = _parse_connection_string(connection_string)

        self._s3_client = boto3.client(
            "s3",
            endpoint_url=self._config.host,
            aws_access_key_id=self._config.username,
            aws_secret_access_key=self._config.password,
        )
        self._tenant_uid = tenant_uid

    def _put_object(self, key: str, body: bytes, content_type: str):
        self._s3_client.put_object(
            Bucket=self._config.bucket_name,
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

            return self._url(key)
        except ClientError as e:
            raise CouldNotStoreFileError("Failed to store file in S3") from e

    def _url(self, key: str) -> str:
        return f"{self._config.external_host}/{self._config.bucket_name}/{self._tenant_uid}/{key}"


class _S3Config(NamedTuple):
    host: str
    bucket_name: str
    username: str | None
    password: str | None
    external_host: str


def _first_query_param(query_dict: dict[str, list[str]], param: str) -> str | None:
    if p := query_dict.get(param):
        return p[0]
    return None


def _parse_connection_string(connection_string: str) -> _S3Config:
    parsed = urlparse(connection_string)
    host = parsed.hostname
    if not host:
        raise ValueError("Host is required")
    port = parsed.port

    query_dict = parse_qs(parsed.query) if parsed.query else {}
    insecure = _first_query_param(query_dict, "secure") == "false"

    host = f"{'http' if insecure else 'https'}://{host}"
    if port:
        host += f":{port}"

    return _S3Config(
        host,
        parsed.path.lstrip("/"),
        username=parsed.username,
        password=parsed.password,
        external_host=_first_query_param(query_dict, "external_host") or host,
    )

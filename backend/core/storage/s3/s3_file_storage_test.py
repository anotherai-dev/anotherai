# pyright: reportPrivateUsage=false


import base64
import json
import os
from typing import Any

import httpx
import pytest

from core.domain.file import File
from core.storage.s3.s3_file_storage import S3FileStorage, _parse_connection_string


@pytest.fixture
def s3_file_storage():
    store = S3FileStorage(
        connection_string=os.getenv(
            "FILE_STORAGE_DSN_TEST",
            "s3://minio:miniosecret@localhost:9000/anotherai-tests?secure=false",
        ),
        tenant_uid=1,
    )

    return store


@pytest.fixture
def setup_public_bucket(s3_file_storage: S3FileStorage, store: S3FileStorage):
    clt: Any = store._s3_client  # pyright: ignore[reportPrivateUsage]

    try:
        clt.head_bucket(Bucket=store._config.bucket_name)
    except Exception:  # noqa: BLE001
        # Create bucket if it doesn't exist
        clt.create_bucket(Bucket=store._config.bucket_name)

        # Make bucket public

        clt.put_bucket_policy(
            Bucket=store._config.bucket_name,
            Policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadGetObject",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{store._config.bucket_name}/*"],
                        },
                    ],
                },
            ),
        )


@pytest.mark.skip(reason="Skipping S3 file storage test for now")
async def test_store_file(s3_file_storage: S3FileStorage, setup_public_bucket: None):
    file = File(
        data=base64.b64encode(b"Hello, world!").decode(),
        content_type="text/plain",
    )

    url = await s3_file_storage.store_file(file, "test")
    assert url is not None

    async with httpx.AsyncClient() as client:
        content = await client.get(url)
        assert content.status_code == 200
        assert content.content == b"Hello, world!"


class TestURL:
    def test_url_basic(self, s3_file_storage: S3FileStorage):
        url = s3_file_storage._url("test/test.txt")
        assert url == "http://localhost:9000/anotherai-tests/1/test/test.txt"

    def test_with_external_host(self):
        store = S3FileStorage(
            connection_string="s3://minio:miniosecret@localhost:9000/anotherai-tests?secure=false&external_host=http://minio:9000",
            tenant_uid=1,
        )
        url = store._url("test/test.txt")
        assert url == "http://minio:9000/anotherai-tests/1/test/test.txt"


class TestParseConnectionString:
    def test_basic_parsing_with_all_fields(self):
        connection_string = "s3://minio:miniosecret@localhost:9000/anotherai-tests?secure=false"
        config = _parse_connection_string(connection_string)
        assert config.host == "http://localhost:9000"
        assert config.bucket_name == "anotherai-tests"
        assert config.username == "minio"
        assert config.password == "miniosecret"  # noqa: S105
        assert config.external_host == "http://localhost:9000"

    def test_secure_true_uses_https(self):
        connection_string = "s3://user:pass@host.com:443/bucket?secure=true"
        config = _parse_connection_string(connection_string)
        assert config.host == "https://host.com:443"
        assert config.external_host == "https://host.com:443"

    def test_secure_false_uses_http(self):
        connection_string = "s3://user:pass@host.com:9000/bucket?secure=false"
        config = _parse_connection_string(connection_string)
        assert config.host == "http://host.com:9000"

    def test_default_secure_uses_https(self):
        connection_string = "s3://user:pass@host.com/bucket"
        config = _parse_connection_string(connection_string)
        assert config.host == "https://host.com"

    def test_without_port(self):
        connection_string = "s3://user:pass@host.com/bucket"
        config = _parse_connection_string(connection_string)
        assert config.host == "https://host.com"
        assert ":" not in config.host.split("//")[1]

    def test_with_port(self):
        connection_string = "s3://user:pass@host.com:9000/bucket"
        config = _parse_connection_string(connection_string)
        assert config.host == "https://host.com:9000"

    def test_without_credentials(self):
        connection_string = "s3://host.com:9000/bucket"
        config = _parse_connection_string(connection_string)
        assert config.username is None
        assert config.password is None

    def test_with_external_host(self):
        connection_string = (
            "s3://minio:miniosecret@localhost:9000/anotherai-tests?secure=false&external_host=http://minio:9000"
        )
        config = _parse_connection_string(connection_string)
        assert config.external_host == "http://minio:9000"
        assert config.host == "http://localhost:9000"

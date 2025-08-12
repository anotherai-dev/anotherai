import base64
import json
import os
from typing import Any

import httpx
import pytest

from core.domain.file import File
from core.storage.s3.s3_file_storage import S3FileStorage


@pytest.fixture
def s3_file_storage():
    store = S3FileStorage(
        connection_string=os.getenv(
            "FILE_STORAGE_DSN_TEST",
            "s3://minio:miniosecret@localhost:9000/anotherai-tests?secure=false",
        ),
        tenant_uid=1,
    )
    clt: Any = store._s3_client  # pyright: ignore[reportPrivateUsage]

    try:
        clt.head_bucket(Bucket=store.bucket_name)
    except Exception:  # noqa: BLE001
        # Create bucket if it doesn't exist
        clt.create_bucket(Bucket=store.bucket_name)

        # Make bucket public

        clt.put_bucket_policy(
            Bucket=store.bucket_name,
            Policy=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadGetObject",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{store.bucket_name}/*"],
                        },
                    ],
                },
            ),
        )

    return store


@pytest.mark.skip(reason="Skipping S3 file storage test for now")
async def test_store_file(s3_file_storage: S3FileStorage):
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

import base64

import httpx
import pytest

from core.domain.file import File
from core.storage.azure.azure_blob_file_storage import AzureBlobFileStorage
from tests.utils import fixture_bytes

_TEST_AZURE_BLOB_DSN_TEST = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
_TEST_AZURE_BLOB_CONTAINER = "test-container"


@pytest.fixture
async def azure_blob_storage(
    # Using global fixture to make sure the container is created
    test_blob_storage: tuple[str, str],
) -> AzureBlobFileStorage:
    storage = AzureBlobFileStorage(
        connection_string=test_blob_storage[1],
        container_name=test_blob_storage[0],
        tenant_uid=1,
    )
    return storage


async def test_connection_established(azure_blob_storage: AzureBlobFileStorage):
    # Test that we can establish a connection and get container client
    blob_service_client = await azure_blob_storage._get_blob_service_client()  # pyright: ignore[reportPrivateUsage]
    assert blob_service_client is not None

    # Test that we can get a blob client
    blob_client_properties = await blob_service_client.get_service_properties()
    assert blob_client_properties is not None

    container_properties = await blob_service_client.get_container_client(
        azure_blob_storage.container_name,
    ).get_container_properties()
    assert container_properties is not None


async def test_store_file(azure_blob_storage: AzureBlobFileStorage):
    blob_service_client = await azure_blob_storage._get_blob_service_client()  # pyright: ignore[reportPrivateUsage]
    assert blob_service_client is not None
    assert hasattr(blob_service_client, "url")

    file_data = fixture_bytes("files", "test.png")

    folder_path = "test/local"

    blob_name = f"1/{folder_path}/52bcf683da5693c81ce5d748bd2e158971dc0abbe5f8500440240c64569c0ca4.png"
    url = await azure_blob_storage.store_file(
        File(data=base64.b64encode(file_data).decode("utf-8"), content_type="image/png"),
        folder_path,
    )

    container_url = f"{blob_service_client.url}{azure_blob_storage.container_name}"  # pyright: ignore[reportUnknownMemberType]
    assert url == f"{container_url}/{blob_name}"

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    response = response.raise_for_status()
    assert response.content == file_data

import asyncio
import time
from collections.abc import Callable, Sequence
from typing import Any, final

import structlog

from core.domain.exceptions import InvalidFileError
from core.domain.file import File
from core.domain.message import Message
from core.domain.models.models import Model
from core.providers._base.abstract_provider import AbstractProvider

log = structlog.get_logger(__name__)


@final
class RunnerFileHandler:
    def __init__(
        self,
        model: Model,
        provider: AbstractProvider[Any, Any],
        record_file_download_seconds: Callable[[float], None],
    ):
        self._provider = provider
        self._model = model
        self._record_file_download_seconds = record_file_download_seconds

    def _should_download_file(self, file: File) -> bool:
        if file.data:
            return False

        return self._provider.requires_downloading_file(file, self._model)

    async def handle_files_in_messages(
        self,
        messages: Sequence[Message],
    ):
        # Not using file iterator here as it creates a copy of files
        files: list[File] = []
        for m in messages:
            files.extend(m.file_iterator())

        if not files:
            return

        download_start_time = time.time()
        # TODO:
        # files = await self._convert_pdf_to_images(files, model_data)
        # self._check_support_for_files(model_data, files)

        files_to_download = self._extract_files_to_download(
            files,
        )
        if files_to_download:
            try:
                async with asyncio.TaskGroup() as tg:
                    for file in files_to_download:
                        # We want to update the provided input because file data
                        # should be propagated upstream to avoid having to download files twice
                        _ = tg.create_task(file.download())
            except* InvalidFileError as e:
                raise InvalidFileError(
                    f"Failed to download {len(e.exceptions)} files: {e.exceptions}",
                    capture=False,
                ) from e
            # Here we update the input copy instead of the provided input
            # Since the data will just be provided to the provider

            download_duration = time.time() - download_start_time
            self._record_file_download_seconds(download_duration)

    def _extract_files_to_download(
        self,
        files: list[File],
    ):
        max_number_of_file_urls = self._provider.max_number_of_file_urls
        # Files that should not be downloaded and that will be passed as links
        files_as_links: list[File] = []
        # files that should be downloaded
        files_to_download: list[File] = []

        for f in files:
            if self._should_download_file(f):
                files_to_download.append(f)
                continue
            if not f.data:
                # File does not contain data so we will pass it as a link
                files_as_links.append(f)

        if max_number_of_file_urls is not None and len(files_as_links) > max_number_of_file_urls:
            # If limit we need to make sure we
            files_to_download.extend(files_as_links[max_number_of_file_urls:])

        return files_to_download

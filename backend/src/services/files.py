import mimetypes
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.core.config import settings
from src.core.exceptions import EmptyFile, StoredFileMissing
from src.domain.enums import ProcessingStatus
from src.domain.models import StoredFile
from src.repositories.files import FileRepository
from src.services.metadata import make_accumulator
from src.storage.base import FileStorage


class FileService:
    def __init__(self, files: FileRepository, storage: FileStorage) -> None:
        self._files = files
        self._storage = storage

    async def list(self, limit: int = 100, offset: int = 0) -> list[StoredFile]:
        return await self._files.list(limit=limit, offset=offset)

    async def get(self, file_id: str) -> StoredFile:
        return await self._files.get_or_raise(file_id)

    async def rename(self, file_id: str, title: str) -> StoredFile:
        item = await self._files.get_or_raise(file_id)
        item.title = title
        return item

    async def remove(self, file_id: str) -> None:
        item = await self._files.get_or_raise(file_id)
        stored_name = item.stored_name
        await self._files.delete(item)
        await self._files.flush()
        self._storage.delete(stored_name)

    async def path_for_download(self, file_id: str) -> tuple[StoredFile, Path]:
        item = await self._files.get_or_raise(file_id)
        if not self._storage.exists(item.stored_name):
            raise StoredFileMissing()
        return item, self._storage.path(item.stored_name)

    async def create(self, title: str, upload_file: UploadFile) -> StoredFile:
        file_id = str(uuid4())
        original_name = upload_file.filename or file_id
        suffix = Path(original_name).suffix
        stored_name = f"{file_id}{suffix}"
        mime_type = (
            upload_file.content_type
            or mimetypes.guess_type(stored_name)[0]
            or "application/octet-stream"
        )

        accumulator = make_accumulator(original_name, 0, mime_type)
        size = await self._storage.save_stream(
            stored_name, self._iter_chunks(upload_file), observer=accumulator
        )

        if size == 0:
            self._storage.delete(stored_name)
            raise EmptyFile()

        metadata = accumulator.result()
        # size is only known once the stream is fully drained, so the
        # accumulator was built with size=0; patch in the real value here.
        metadata["size_bytes"] = size

        item = StoredFile(
            id=file_id,
            title=title,
            original_name=original_name,
            stored_name=stored_name,
            mime_type=mime_type,
            size=size,
            processing_status=ProcessingStatus.UPLOADED,
            pending_metadata_json=metadata,
        )
        await self._files.add(item)
        return item

    async def _iter_chunks(self, upload_file: UploadFile) -> AsyncIterator[bytes]:
        while chunk := await upload_file.read(settings.upload_chunk_size):
            yield chunk

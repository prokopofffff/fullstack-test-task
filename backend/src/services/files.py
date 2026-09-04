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
        # Unit of work — сервис сам коммитит и не оставляет это маршруту (см.
        # get_session в src/core/db.py). Коммит обязан произойти ДО ответа
        # клиенту, иначе следующий быстрый GET может обогнать запись.
        await self._files.commit()
        # updated_at считается на стороне БД (onupdate=func.now()), и после
        # UPDATE SQLAlchemy помечает это поле как требующее перечитывания даже
        # при expire_on_commit=False. Без явного refresh сериализация ответа
        # (она идёт вне async-контекста) падает с MissingGreenlet при попытке
        # лениво подгрузить значение.
        await self._files.refresh(item)
        return item

    async def remove(self, file_id: str) -> None:
        item = await self._files.get_or_raise(file_id)
        stored_name = item.stored_name
        await self._files.delete(item)
        # Коммит вместо flush: без него удаление откатится при закрытии
        # сессии, и клиент получит 204, хотя запись осталась на месте.
        await self._files.commit()
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

        accumulator = make_accumulator(original_name, mime_type)
        size = await self._storage.save_stream(
            stored_name, self._iter_chunks(upload_file), observer=accumulator
        )

        if size == 0:
            self._storage.delete(stored_name)
            raise EmptyFile()

        # Размер известен только после того, как поток дочитан до конца,
        # поэтому передаётся в result(), а не в конструктор — там его брать
        # неоткуда.
        metadata = accumulator.result(size)

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
        # Unit of work — сервис сам коммитит (см. rename/remove выше и
        # src/core/db.py::get_session): без коммита server_default-поля
        # (created_at, updated_at, requires_attention) не заполнены на
        # момент сериализации ответа, а воркер не увидит строку вовсе.
        await self._files.commit()
        return item

    async def _iter_chunks(self, upload_file: UploadFile) -> AsyncIterator[bytes]:
        while chunk := await upload_file.read(settings.upload_chunk_size):
            yield chunk

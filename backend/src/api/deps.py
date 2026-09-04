from dataclasses import dataclass

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.db import get_session
from src.repositories.files import FileRepository
from src.services.files import FileService
from src.storage.local import LocalFileStorage

_storage = LocalFileStorage(
    root=settings.storage_dir,
    max_size=settings.max_upload_size,
)


def get_file_service(session: AsyncSession = Depends(get_session)) -> FileService:
    return FileService(FileRepository(session), _storage)


@dataclass
class Pagination:
    limit: int
    offset: int


def get_pagination(
    limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)
) -> Pagination:
    return Pagination(limit=limit, offset=offset)

from fastapi import Depends
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

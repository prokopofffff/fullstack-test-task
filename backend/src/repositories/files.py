from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import FileNotFound
from src.domain.enums import ProcessingStatus
from src.domain.models import StoredFile


class FileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, file_id: str) -> StoredFile | None:
        return await self._session.get(StoredFile, file_id)

    async def get_or_raise(self, file_id: str) -> StoredFile:
        found = await self.get(file_id)
        if found is None:
            raise FileNotFound()
        return found

    # list_stale встаёт перед list(): начиная со следующего def в теле класса имя
    # `list` в области видимости класса уже указывает на сам метод list() ниже, а
    # не на builtin — mypy резолвит аннотации типов по этой области видимости и
    # ругается "Function is not valid as a type". Порядок объявления здесь важен.
    async def list_stale(
        self, older_than: datetime, statuses: list[ProcessingStatus]
    ) -> list[StoredFile]:
        result = await self._session.execute(
            select(StoredFile).where(
                StoredFile.processing_status.in_([s.value for s in statuses]),
                StoredFile.updated_at < older_than,
            )
        )
        return list(result.scalars().all())

    async def list(self, limit: int = 100, offset: int = 0) -> list[StoredFile]:
        result = await self._session.execute(
            select(StoredFile).order_by(StoredFile.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def add(self, file: StoredFile) -> None:
        self._session.add(file)

    async def delete(self, file: StoredFile) -> None:
        await self._session.delete(file)

    async def flush(self) -> None:
        await self._session.flush()

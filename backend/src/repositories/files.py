from datetime import datetime

from sqlalchemy import func, select, update
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
        self, older_than: datetime, statuses: list[ProcessingStatus], limit: int = 100
    ) -> list[str]:
        # order_by(updated_at) + limit: без него один и тот же самый старый
        # хвост зависших записей монополизировал бы выборку каждый тик, а
        # остальные никогда бы не подобрались.
        # Реконсилятору нужны только id — select(StoredFile) тянул бы целые
        # строки (width=266) ради одного поля (width=45) на запросе, который
        # крутится каждые 60 секунд вечно.
        result = await self._session.execute(
            select(StoredFile.id)
            .where(
                StoredFile.processing_status.in_([s.value for s in statuses]),
                StoredFile.updated_at < older_than,
            )
            .order_by(StoredFile.updated_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def touch(self, ids: list[str]) -> None:
        """Сдвигает `updated_at` без изменения статуса.

        Нужен реконсилятору сразу после переотправки застрявших записей в
        Celery: без этого `updated_at` не меняется до завершения задачи, и та
        же запись снова попадёт в `list_stale` на следующем тике `beat`,
        прежде чем воркер успеет её обработать.
        """
        if not ids:
            return
        await self._session.execute(
            update(StoredFile).where(StoredFile.id.in_(ids)).values(updated_at=func.now())
        )

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

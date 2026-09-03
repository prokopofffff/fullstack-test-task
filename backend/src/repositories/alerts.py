from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AlertLevel
from src.domain.models import Alert


class AlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, limit: int = 100, offset: int = 0) -> list[Alert]:
        result = await self._session.execute(
            select(Alert).order_by(Alert.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def exists(self, file_id: str, level: AlertLevel) -> bool:
        result = await self._session.execute(
            select(Alert.id).where(Alert.file_id == file_id, Alert.level == level.value).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def add(self, file_id: str, level: AlertLevel, message: str) -> Alert:
        # Flush first: without an ORM relationship() between StoredFile and
        # Alert, SQLAlchemy's unit of work has no dependency edge between the
        # two mappers and does not order their INSERTs by the FK column, so a
        # pending StoredFile in the same session can otherwise be flushed
        # after the Alert that references it, violating the FK constraint.
        await self._session.flush()
        alert = Alert(file_id=file_id, level=level.value, message=message)
        self._session.add(alert)
        return alert

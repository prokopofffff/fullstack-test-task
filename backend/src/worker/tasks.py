import asyncio
from typing import Any

from billiard.einfo import ExceptionInfo
from celery import Task
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.core.config import settings
from src.domain.enums import TERMINAL_STATUSES, AlertLevel, ProcessingStatus, ScanStatus
from src.repositories.alerts import AlertRepository
from src.repositories.files import FileRepository
from src.services.scanner import scan
from src.worker.celery_app import celery_app

# Воркер запускает каждую задачу через asyncio.run(), то есть в НОВОМ цикле событий.
# Процесс-широкий пул из src/core/db.py привязывается к первому циклу и на второй
# задаче падает с RuntimeError: attached to a different loop. NullPool не хранит
# соединения между задачами и снимает проблему целиком.
engine = create_async_engine(settings.db_url, poolclass=NullPool)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def _process(file_id: str) -> None:
    async with async_session_maker() as session:
        files = FileRepository(session)
        alerts = AlertRepository(session)

        item = await files.get(file_id)
        if item is None:
            return
        if item.processing_status in TERMINAL_STATUSES:
            return

        verdict = scan(item.original_name, item.size, item.mime_type)
        item.scan_status = verdict.status.value
        item.scan_details = verdict.details
        item.requires_attention = verdict.requires_attention
        # pending_metadata_json всегда заполнен словарём (FileService.create
        # кладёт минимум extension/size_bytes/mime_type) — фолбэк на
        # make_accumulator(...).result(...) здесь был недостижим, а при
        # срабатывании молча подставил бы нули вместо реальных метаданных.
        item.metadata_json = item.pending_metadata_json
        item.pending_metadata_json = None
        item.processing_status = ProcessingStatus.PROCESSED

        level = AlertLevel.WARNING if verdict.requires_attention else AlertLevel.INFO
        message = (
            f"File requires attention: {verdict.details}"
            if verdict.requires_attention
            else "File processed successfully"
        )
        if not await alerts.exists(file_id, level):
            await alerts.add(file_id, level, message)

        await session.commit()


async def _mark_failed(file_id: str) -> None:
    async with async_session_maker() as session:
        files = FileRepository(session)
        alerts = AlertRepository(session)
        item = await files.get(file_id)
        if item is None:
            return
        item.processing_status = ProcessingStatus.FAILED
        item.scan_status = item.scan_status or ScanStatus.FAILED.value
        if not await alerts.exists(file_id, AlertLevel.CRITICAL):
            await alerts.add(file_id, AlertLevel.CRITICAL, "File processing failed")
        await session.commit()


# celery-types объявляет Task как Generic для проверки типов, но сам класс
# celery.Task в рантайме __class_getitem__ не поддерживает — Task[..., None]
# падает с "TypeError: type 'Task' is not subscriptable" при импорте воркером
# и celery beat. Поэтому не параметризуем и точечно снимаем это требование mypy.
class ProcessFileTask(Task):  # type: ignore[type-arg]
    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: ExceptionInfo,
    ) -> None:
        file_id = args[0] if args else kwargs.get("file_id")
        if file_id:
            asyncio.run(_mark_failed(file_id))


@celery_app.task(base=ProcessFileTask, bind=True, name="src.worker.tasks.process_file")
def process_file(self: ProcessFileTask, file_id: str) -> None:
    asyncio.run(_process(file_id))

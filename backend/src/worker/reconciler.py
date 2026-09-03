import asyncio
from datetime import UTC, datetime, timedelta

from src.core.config import settings
from src.domain.enums import ProcessingStatus
from src.repositories.files import FileRepository
from src.worker.celery_app import celery_app
from src.worker.tasks import async_session_maker, process_file

STUCK_STATUSES = [ProcessingStatus.UPLOADED, ProcessingStatus.PROCESSING]


async def _reconcile() -> int:
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.stale_after_seconds)
    async with async_session_maker() as session:
        stale = await FileRepository(session).list_stale(cutoff, STUCK_STATUSES)
        ids = [item.id for item in stale]
    for file_id in ids:
        process_file.delay(file_id)
    return len(ids)


@celery_app.task(name="src.worker.reconciler.reconcile_stuck_files")
def reconcile_stuck_files() -> int:
    return asyncio.run(_reconcile())

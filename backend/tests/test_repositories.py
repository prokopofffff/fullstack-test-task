from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.core.db import async_session_maker
from src.core.exceptions import FileNotFound
from src.domain.enums import AlertLevel, ProcessingStatus
from src.domain.models import StoredFile
from src.repositories.alerts import AlertRepository
from src.repositories.files import FileRepository

# Все тесты в этом модуле работают в одном цикле событий. `engine`/
# `async_session_maker` — процесс-широкие синглтоны (src/core/db.py), чьи
# пулcированные соединения asyncpg привязаны к циклу, в котором были открыты;
# при дефолтном для pytest-asyncio цикле на каждый тест соединение, взятое из
# пула одним тестом и переиспользованное следующим (уже в новом цикле),
# падает с "Future attached to a different loop".
pytestmark = pytest.mark.asyncio(loop_scope="module")


def make_file(**overrides) -> StoredFile:
    file_id = str(uuid4())
    defaults = dict(
        id=file_id,
        title="t",
        original_name="a.txt",
        stored_name=f"{file_id}.txt",
        mime_type="text/plain",
        size=1,
        processing_status=ProcessingStatus.UPLOADED,
    )
    return StoredFile(**{**defaults, **overrides})


async def test_get_or_raise_raises_domain_error():
    async with async_session_maker() as session:
        with pytest.raises(FileNotFound):
            await FileRepository(session).get_or_raise("nope")


async def test_add_then_get_roundtrip():
    item = make_file()
    async with async_session_maker() as session:
        repo = FileRepository(session)
        await repo.add(item)
        await session.commit()
    async with async_session_maker() as session:
        found = await FileRepository(session).get_or_raise(item.id)
        assert found.original_name == "a.txt"


async def test_list_is_newest_first_and_paginated():
    async with async_session_maker() as session:
        repo = FileRepository(session)
        for _ in range(3):
            await repo.add(make_file())
        await session.commit()
    async with async_session_maker() as session:
        rows = await FileRepository(session).list(limit=2, offset=0)
        assert len(rows) == 2
        assert rows[0].created_at >= rows[1].created_at


async def test_list_stale_finds_only_old_non_terminal_rows():
    fresh = make_file(processing_status=ProcessingStatus.PROCESSING)
    done = make_file(processing_status=ProcessingStatus.PROCESSED)
    async with async_session_maker() as session:
        repo = FileRepository(session)
        await repo.add(fresh)
        await repo.add(done)
        await session.commit()
    async with async_session_maker() as session:
        stale = await FileRepository(session).list_stale(
            older_than=datetime.now(UTC) + timedelta(minutes=1),
            statuses=[ProcessingStatus.UPLOADED, ProcessingStatus.PROCESSING],
        )
        ids = {row.id for row in stale}
        assert fresh.id in ids
        assert done.id not in ids


async def test_list_stale_respects_limit():
    async with async_session_maker() as session:
        repo = FileRepository(session)
        for _ in range(3):
            await repo.add(make_file(processing_status=ProcessingStatus.UPLOADED))
        await session.commit()
    async with async_session_maker() as session:
        # cutoff в будущем — приём из соседнего теста, чтобы не ждать
        # реального времени: свежедобавленные строки уже "старше" cutoff.
        stale = await FileRepository(session).list_stale(
            older_than=datetime.now(UTC) + timedelta(minutes=1),
            statuses=[ProcessingStatus.UPLOADED],
            limit=2,
        )
        # В базе к этому моменту как минимум 3 подходящие строки (свои плюс,
        # возможно, от других тестов) — limit обязан обрезать выборку, а не
        # просто оказаться не меньше её размера.
        assert len(stale) == 2


async def test_touch_bumps_updated_at():
    item = make_file(processing_status=ProcessingStatus.UPLOADED)
    async with async_session_maker() as session:
        repo = FileRepository(session)
        await repo.add(item)
        await session.commit()
        await session.refresh(item)
        original_updated_at = item.updated_at

    async with async_session_maker() as session:
        await FileRepository(session).touch([item.id])
        await session.commit()

    async with async_session_maker() as session:
        refreshed = await FileRepository(session).get_or_raise(item.id)
        assert refreshed.updated_at > original_updated_at


async def test_alert_exists_guards_duplicates():
    item = make_file()
    async with async_session_maker() as session:
        files = FileRepository(session)
        await files.add(item)
        # flush() файла до добавления алерта: у StoredFile и Alert нет
        # ORM relationship(), поэтому порядок их INSERT внутри одного flush
        # ничем не гарантирован, а вставка алерта первым нарушила бы его FK.
        await files.flush()
        await AlertRepository(session).add(item.id, AlertLevel.INFO, "ok")
        await session.commit()
    async with async_session_maker() as session:
        repo = AlertRepository(session)
        assert await repo.exists(item.id, AlertLevel.INFO) is True
        assert await repo.exists(item.id, AlertLevel.CRITICAL) is False

import subprocess
from pathlib import Path

import pytest

# Этот файл запускается с хоста (`cd backend && uv run pytest
# tests/test_failure_modes.py -v`, см. README), то есть CWD — backend/. Но
# docker-compose.dev.yml лежит на уровень выше, в корне репозитория, поэтому
# относительный путь "docker-compose.dev.yml" не резолвится из backend/.
# Считаем путь от расположения самого файла теста, а не от CWD.
COMPOSE_FILE = Path(__file__).resolve().parent.parent.parent / "docker-compose.dev.yml"


def _docker_unavailable() -> bool:
    # Внутри контейнера backend docker CLI не установлен вообще, поэтому
    # subprocess.run(["docker", ...]) падает с FileNotFoundError, а не просто
    # возвращает ненулевой код — это валит сбор ВСЕГО модуля (и всего прогона
    # `pytest tests/`), а не только пропускает этот файл. Ловим оба случая:
    # бинарник отсутствует (контейнер) и демон недоступен (сеть/права).
    try:
        return subprocess.run(["docker", "ps"], capture_output=True).returncode != 0
    except FileNotFoundError:
        return True


pytestmark = pytest.mark.skipif(_docker_unavailable(), reason="требует docker")


def compose(*args: str) -> None:
    subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), *args], check=True)


def _run_in_backend(script: str, *, env: dict[str, str] | None = None) -> None:
    cmd = ["docker", "exec"]
    for key, value in (env or {}).items():
        cmd += ["-e", f"{key}={value}"]
    cmd += ["backend", "uv", "run", "python", "-c", script]
    subprocess.run(cmd, check=True)


_BLOCK_PROCESSED_SQL = """
import asyncio, os
from sqlalchemy import text
from src.worker.tasks import engine

FILE_ID = os.environ["FILE_ID"]

async def main():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE files ADD CONSTRAINT test_block_processed "
            f"CHECK (NOT (id = '{FILE_ID}' AND processing_status = 'processed')) NOT VALID"
        ))

asyncio.run(main())
"""

_UNBLOCK_PROCESSED_SQL = """
import asyncio
from sqlalchemy import text
from src.worker.tasks import engine

async def main():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE files DROP CONSTRAINT IF EXISTS test_block_processed"))

asyncio.run(main())
"""


async def test_exception_mid_pipeline_drives_row_to_failed(client, upload, wait_terminal):
    """Отказ A: исключение в середине `_process()` не должно оставлять запись
    в `processing`/`uploaded` навсегда — `on_failure` обязан довести её до `failed`
    с одним critical-алертом.

    Классический триггер такого отказа — подменить сохранённый файл каталогом
    (`IsADirectoryError` при чтении). Он больше не работает: после перехода на
    однопроходные потоковые метаданные (`pending_metadata_json`) `process_file`
    ни разу не открывает файл на диске — `scan()` и сборка метаданных работают
    только с уже сохранёнными в строке полями (см. `src/worker/tasks.py::_process`,
    `src/services/scanner.py`, `src/services/metadata.py`). Проверено эмпирически:
    rm + mkdir на месте файла всё равно заканчивается `processed`, а не `failed`.

    Чтобы всё равно доказать, что путь `on_failure` жив, вызываем исключение
    иначе — CHECK-констрейнтом на таблице `files`, который запрещает ИМЕННО
    этой записи стать `processed` (сработает на `UPDATE` внутри `_process()`,
    ровно там, где раньше падало чтение файла). NOT VALID не проверяет
    существующие строки, поэтому не трогает ничего, кроме одной записи по id;
    constraint снимается в finally независимо от исхода теста. IntegrityError
    не входит в `autoretry_for = (OSError, OperationalError)` из celery_app.py,
    поэтому ретраев нет — `on_failure` срабатывает сразу.
    """
    compose("stop", "backend-worker")
    try:
        item = await upload("Сломанный", "broken.txt", b"a\nb\n", "text/plain")
        _run_in_backend(_BLOCK_PROCESSED_SQL, env={"FILE_ID": item["id"]})
    finally:
        compose("start", "backend-worker")

    try:
        final = await wait_terminal(item["id"], timeout=60)
        assert final["processing_status"] == "failed"

        alerts = (await client.get("/alerts")).json()
        mine = [a for a in alerts if a["file_id"] == item["id"]]
        assert [a["level"] for a in mine] == ["critical"]
    finally:
        _run_in_backend(_UNBLOCK_PROCESSED_SQL)


async def test_orphan_from_broker_outage_is_reconciled(client, upload, wait_terminal, monkeypatch):
    """Отказ B: брокер лежит в момент постановки задачи."""
    compose("stop", "backend-redis")
    try:
        response = await client.post(
            "/files",
            data={"title": "Осиротевший"},
            files={"file": ("orphan.txt", b"x\n", "text/plain")},
        )
    finally:
        compose("start", "backend-redis")

    assert response.status_code == 201

    files = (await client.get("/files")).json()
    orphan = next(f for f in files if f["title"] == "Осиротевший")
    assert orphan["processing_status"] == "uploaded"

    # STALE_AFTER_SECONDS=0 только для этого разового вызова: иначе запись,
    # только что созданная, ещё не считается зависшей и реконсилятор её не
    # подберёт. Передаём через `docker exec -e`, а не через переменную
    # окружения контейнера — так не нужно пересобирать образ и не остаётся
    # побочных эффектов для остальных тестов (сам backend-worker и beat
    # продолжают жить с settings.stale_after_seconds по умолчанию).
    subprocess.run(
        [
            "docker",
            "exec",
            "-e",
            "STALE_AFTER_SECONDS=0",
            "backend-worker",
            "uv",
            "run",
            "python",
            "-c",
            "from src.worker.reconciler import _reconcile; import asyncio;"
            " print(asyncio.run(_reconcile()))",
        ],
        check=True,
    )
    final = await wait_terminal(orphan["id"], timeout=60)
    assert final["processing_status"] == "processed"

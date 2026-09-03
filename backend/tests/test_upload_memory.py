import os
import subprocess

import pytest

SMALL = 3 * 1024 * 1024
LARGE = 300 * 1024 * 1024


def anon_bytes() -> int:
    """Анонимная память контейнера — куча процессов, без page cache.

    memory.peak и memory.current включают `file` (page cache от записи на диск),
    который растёт с размером файла при любой корректной реализации и
    реклеймится ядром. Утечку, которую чинит эта задача, видно только по `anon`.
    """
    out = subprocess.run(
        ["docker", "exec", "backend", "cat", "/sys/fs/cgroup/memory.stat"],
        capture_output=True, text=True, check=True,
    )
    for line in out.stdout.splitlines():
        key, _, value = line.partition(" ")
        if key == "anon":
            return int(value)
    raise AssertionError("memory.stat не содержит anon")


@pytest.mark.skipif(
    os.environ.get("RUN_MEMORY_TEST") != "1",
    reason="требует docker и ~300 МБ трафика; включается RUN_MEMORY_TEST=1",
)
async def test_upload_memory_does_not_scale_with_file_size(client, wait_terminal):
    """Куча не должна расти пропорционально размеру файла.

    До рефакторинга service.py читал файл целиком: `await upload_file.read()`
    плюс `write_bytes(content)` держали в куче несколько копий, и она росла
    линейно от размера. Потоковая запись делает рост постоянным.
    """
    async def upload(size: int) -> int:
        before = anon_bytes()
        response = await client.post(
            "/files",
            data={"title": f"Память {size}"},
            files={"file": (f"mem{size}.bin", b"\0" * size, "application/octet-stream")},
        )
        assert response.status_code == 201, response.text
        await wait_terminal(response.json()["id"], timeout=120)
        return anon_bytes() - before

    small_growth = await upload(SMALL)
    large_growth = await upload(LARGE)

    # Файл в 100 раз больше не должен давать пропорционального роста кучи.
    # Порог намеренно щедрый: важен порядок величины, а не точное число.
    assert large_growth < SMALL, (
        f"куча выросла на {large_growth / 1024 ** 2:.1f} MiB при загрузке "
        f"{LARGE / 1024 ** 2:.0f} MiB (на {SMALL / 1024 ** 2:.0f} MiB файле было "
        f"{small_growth / 1024 ** 2:.1f} MiB) — похоже, файл снова буферизуется целиком"
    )

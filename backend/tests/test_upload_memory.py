import os
import subprocess

import pytest

PEAK_PATH = "/sys/fs/cgroup/memory.peak"
LARGE = 300 * 1024 * 1024


def container_peak_bytes() -> int:
    out = subprocess.run(
        ["docker", "exec", "backend", "cat", PEAK_PATH],
        capture_output=True, text=True, check=True,
    )
    return int(out.stdout.strip())


@pytest.mark.skipif(
    os.environ.get("RUN_MEMORY_TEST") != "1",
    reason="требует docker и ~300 МБ трафика; включается RUN_MEMORY_TEST=1",
)
async def test_large_upload_does_not_scale_memory_with_file_size(client, wait_terminal):
    before = container_peak_bytes()
    response = await client.post(
        "/files",
        data={"title": "Большой"},
        files={"file": ("big.bin", b"\0" * LARGE, "application/octet-stream")},
    )
    assert response.status_code == 201
    await wait_terminal(response.json()["id"], timeout=60)
    after = container_peak_bytes()

    # До рефакторинга: 300 МБ файл поднимал пик со 124 МиБ до 1.03 ГиБ.
    # Потоковая запись должна держать прирост в пределах десятков мегабайт.
    assert after - before < 64 * 1024 * 1024, (
        f"peak grew by {(after - before) / 1024 ** 2:.0f} MiB"
    )

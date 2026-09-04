import asyncio
import os
import time

import httpx
import pytest

from src.domain.enums import TERMINAL_STATUSES

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return API_BASE_URL


@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=60.0) as c:
        yield c


@pytest.fixture
def upload(client):
    async def _upload(
        title: str, filename: str, content: bytes, content_type: str = "application/octet-stream"
    ) -> dict:
        response = await client.post(
            "/files",
            data={"title": title},
            files={"file": (filename, content, content_type)},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _upload


@pytest.fixture
def wait_terminal(client):
    async def _wait(file_id: str, timeout: float = 30.0) -> dict:
        deadline = time.monotonic() + timeout
        last = None
        while time.monotonic() < deadline:
            response = await client.get(f"/files/{file_id}")
            assert response.status_code == 200, response.text
            last = response.json()
            if last["processing_status"] in TERMINAL_STATUSES:
                return last
            await asyncio.sleep(0.2)
        raise AssertionError(
            f"file {file_id} did not reach a terminal status in {timeout}s: {last}"
        )

    return _wait

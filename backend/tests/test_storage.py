import pytest

from src.core.exceptions import FileTooLarge
from src.storage.local import LocalFileStorage


async def achunks(*parts: bytes):
    for part in parts:
        yield part


class Collector:
    def __init__(self) -> None:
        self.seen: list[bytes] = []

    def feed(self, chunk: bytes) -> None:
        self.seen.append(chunk)


async def test_writes_stream_and_returns_size(tmp_path):
    storage = LocalFileStorage(root=tmp_path, max_size=1024)
    written = await storage.save_stream("a.bin", achunks(b"abc", b"de"))
    assert written == 5
    assert (tmp_path / "a.bin").read_bytes() == b"abcde"


async def test_observer_sees_every_chunk(tmp_path):
    storage = LocalFileStorage(root=tmp_path, max_size=1024)
    collector = Collector()
    await storage.save_stream("b.bin", achunks(b"12", b"345"), observer=collector)
    assert b"".join(collector.seen) == b"12345"


async def test_over_limit_raises_and_removes_partial_file(tmp_path):
    storage = LocalFileStorage(root=tmp_path, max_size=4)
    with pytest.raises(FileTooLarge):
        await storage.save_stream("c.bin", achunks(b"12", b"345"))
    assert not (tmp_path / "c.bin").exists()


async def test_delete_is_idempotent(tmp_path):
    storage = LocalFileStorage(root=tmp_path, max_size=1024)
    await storage.save_stream("d.bin", achunks(b"x"))
    storage.delete("d.bin")
    storage.delete("d.bin")
    assert storage.exists("d.bin") is False

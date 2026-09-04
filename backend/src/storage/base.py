from collections.abc import AsyncIterator
from pathlib import Path
from typing import Protocol


class ChunkObserver(Protocol):
    def feed(self, chunk: bytes) -> None: ...


class FileStorage(Protocol):
    async def save_stream(
        self,
        stored_name: str,
        chunks: AsyncIterator[bytes],
        observer: ChunkObserver | None = None,
    ) -> int: ...

    def path(self, stored_name: str) -> Path: ...

    def exists(self, stored_name: str) -> bool: ...

    def delete(self, stored_name: str) -> None: ...

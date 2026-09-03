from collections.abc import AsyncIterator
from pathlib import Path

from src.core.exceptions import FileTooLarge
from src.storage.base import ChunkObserver


class LocalFileStorage:
    def __init__(self, root: Path, max_size: int, chunk_size: int) -> None:
        self._root = Path(root)
        self._max_size = max_size
        self._chunk_size = chunk_size
        self._root.mkdir(parents=True, exist_ok=True)

    def path(self, stored_name: str) -> Path:
        return self._root / stored_name

    def exists(self, stored_name: str) -> bool:
        return self.path(stored_name).is_file()

    def delete(self, stored_name: str) -> None:
        self.path(stored_name).unlink(missing_ok=True)

    async def save_stream(
        self,
        stored_name: str,
        chunks: AsyncIterator[bytes],
        observer: ChunkObserver | None = None,
    ) -> int:
        target = self.path(stored_name)
        written = 0
        try:
            with target.open("wb") as handle:
                async for chunk in chunks:
                    if not chunk:
                        continue
                    written += len(chunk)
                    if written > self._max_size:
                        raise FileTooLarge(limit=self._max_size)
                    handle.write(chunk)
                    if observer is not None:
                        observer.feed(chunk)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return written

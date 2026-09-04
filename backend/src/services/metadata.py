import codecs
from pathlib import Path
from typing import Any, Protocol

PDF_PAGE_MARKER = b"/Type /Page"

# Разделители строк, которые распознаёт str.splitlines() (плюс \r —
# он не входит в набор ниже, но тоже завершает строку в TextAccumulator).
_SPLITLINES_SEPARATORS = "\n\v\f\x1c\x1d\x1e\x85  "
_LINE_SEPARATORS = _SPLITLINES_SEPARATORS + "\r"


def _is_separator(char: str) -> bool:
    return char in _LINE_SEPARATORS


class MetadataAccumulator(Protocol):
    def feed(self, chunk: bytes) -> None: ...
    def result(self, size: int) -> dict[str, Any]: ...


class _Base:
    def __init__(self, original_name: str, mime_type: str) -> None:
        self._extension = Path(original_name).suffix.lower()
        self._mime_type = mime_type

    def feed(self, chunk: bytes) -> None:
        return None

    def result(self, size: int) -> dict[str, Any]:
        return {
            "extension": self._extension,
            "size_bytes": size,
            "mime_type": self._mime_type,
        }


class NullAccumulator(_Base):
    pass


class TextAccumulator(_Base):
    """Повторяет len(text.splitlines()) и len(text) без удержания файла в памяти."""

    def __init__(self, original_name: str, mime_type: str) -> None:
        super().__init__(original_name, mime_type)
        self._decoder = codecs.getincrementaldecoder("utf-8")("ignore")
        self._char_count = 0
        self._sep_count = 0
        self._pending_cr = False
        self._trailing_content = False

    def _consume(self, text: str) -> None:
        if not text:
            return
        # Считаем разделители С-уровневым str.splitlines() вместо цикла по
        # символам: для любой строки s число разделителей равно
        # len((s + "\x00").splitlines()) - 1, т.к. "\x00" не является
        # разделителем и гарантирует непустой хвост.
        # этот \n уже учтён как часть \r\n предыдущего чанка
        starts_with_pending_lf = self._pending_cr and text[0] == "\n"
        text_for_seps = text[1:] if starts_with_pending_lf else text
        self._sep_count += len((text_for_seps + "\x00").splitlines()) - 1
        self._pending_cr = text.endswith("\r")
        self._trailing_content = not _is_separator(text[-1])
        self._char_count += len(text)

    def feed(self, chunk: bytes) -> None:
        self._consume(self._decoder.decode(chunk))

    def result(self, size: int) -> dict[str, Any]:
        self._consume(self._decoder.decode(b"", final=True))
        data = super().result(size)
        data["line_count"] = self._sep_count + (1 if self._trailing_content else 0)
        data["char_count"] = self._char_count
        return data


class PdfAccumulator(_Base):
    """Считает вхождения маркера страницы, не теряя их на границах чанков."""

    def __init__(self, original_name: str, mime_type: str) -> None:
        super().__init__(original_name, mime_type)
        self._count = 0
        self._tail = b""

    def feed(self, chunk: bytes) -> None:
        window = self._tail + chunk
        self._count += window.count(PDF_PAGE_MARKER)
        self._tail = window[-(len(PDF_PAGE_MARKER) - 1) :]

    def result(self, size: int) -> dict[str, Any]:
        data = super().result(size)
        data["approx_page_count"] = max(self._count, 1)
        return data


def make_accumulator(original_name: str, mime_type: str) -> MetadataAccumulator:
    if mime_type.startswith("text/"):
        return TextAccumulator(original_name, mime_type)
    if mime_type == "application/pdf":
        return PdfAccumulator(original_name, mime_type)
    return NullAccumulator(original_name, mime_type)

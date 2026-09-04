import pytest

from src.services.metadata import make_accumulator

TEXT_SAMPLES = [
    b"",
    b"a",
    b"a\nb",
    b"line1\nline2\nline3\n",
    b"\n\n\n",
    b"a\r\nb\r\n",
    b"a\rb",
    "привет\nмир\n".encode(),
    "многобайтный \U0001f600 символ\n".encode(),
    b"x" * 5000 + b"\n",
]


def feed_in_chunks(accumulator, payload: bytes, chunk_size: int) -> None:
    for start in range(0, len(payload), chunk_size):
        accumulator.feed(payload[start : start + chunk_size])


@pytest.mark.parametrize("payload", TEXT_SAMPLES)
@pytest.mark.parametrize("chunk_size", [1, 2, 3, 7, 4096])
def test_text_counts_match_whole_file_computation(payload, chunk_size):
    decoded = payload.decode("utf-8", errors="ignore")
    expected_lines = len(decoded.splitlines())
    expected_chars = len(decoded)

    accumulator = make_accumulator("a.txt", len(payload), "text/plain")
    feed_in_chunks(accumulator, payload, chunk_size)
    result = accumulator.result()

    assert result["line_count"] == expected_lines
    assert result["char_count"] == expected_chars


@pytest.mark.parametrize("chunk_size", [1, 5, 11, 4096])
def test_pdf_page_count_survives_chunk_boundaries(chunk_size):
    payload = b"%PDF\n/Type /Page\nxx\n/Type /Page\ntrailer"
    accumulator = make_accumulator("a.pdf", len(payload), "application/pdf")
    feed_in_chunks(accumulator, payload, chunk_size)
    assert accumulator.result()["approx_page_count"] == 2


def test_pdf_without_pages_reports_one():
    accumulator = make_accumulator("a.pdf", 4, "application/pdf")
    accumulator.feed(b"%PDF")
    assert accumulator.result()["approx_page_count"] == 1


def test_common_fields_always_present():
    accumulator = make_accumulator("a.bin", 42, "application/octet-stream")
    accumulator.feed(b"\0" * 42)
    assert accumulator.result() == {
        "extension": ".bin",
        "size_bytes": 42,
        "mime_type": "application/octet-stream",
    }

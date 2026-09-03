from src.domain.enums import ScanStatus
from src.services.scanner import scan

BIG = 10 * 1024 * 1024 + 1


def test_clean_file():
    result = scan("notes.txt", 10, "text/plain")
    assert result.status is ScanStatus.CLEAN
    assert result.details == "no threats found"
    assert result.requires_attention is False


def test_suspicious_extension():
    result = scan("evil.exe", 6, "application/x-msdownload")
    assert result.status is ScanStatus.SUSPICIOUS
    assert result.details == "suspicious extension .exe"
    assert result.requires_attention is True


def test_size_over_threshold():
    assert scan("big.bin", BIG, "application/octet-stream").details == (
        "file is larger than 10 MB"
    )


def test_size_exactly_at_threshold_is_clean():
    assert scan("edge.bin", 10 * 1024 * 1024, "application/octet-stream").status is ScanStatus.CLEAN


def test_pdf_mime_mismatch():
    assert scan("doc.pdf", 10, "text/plain").details == (
        "pdf extension does not match mime type"
    )


def test_pdf_with_octet_stream_is_allowed():
    assert scan("doc.pdf", 10, "application/octet-stream").status is ScanStatus.CLEAN


def test_reason_order_is_extension_then_size_then_mime():
    assert scan("big.exe", BIG, "application/x-msdownload").details == (
        "suspicious extension .exe, file is larger than 10 MB"
    )


def test_extension_matching_is_case_insensitive():
    assert scan("EVIL.EXE", 6, "application/x-msdownload").details == (
        "suspicious extension .exe"
    )

from dataclasses import dataclass
from pathlib import Path

from src.core.config import settings
from src.domain.enums import ScanStatus

PDF_ALLOWED_MIME = frozenset({"application/pdf", "application/octet-stream"})


@dataclass(frozen=True)
class ScanResult:
    status: ScanStatus
    details: str
    requires_attention: bool


def scan(original_name: str, size: int, mime_type: str) -> ScanResult:
    reasons: list[str] = []
    extension = Path(original_name).suffix.lower()

    if extension in settings.suspicious_extensions:
        reasons.append(f"suspicious extension {extension}")

    if size > settings.suspicious_size_threshold:
        reasons.append("file is larger than 10 MB")

    if extension == ".pdf" and mime_type not in PDF_ALLOWED_MIME:
        reasons.append("pdf extension does not match mime type")

    return ScanResult(
        status=ScanStatus.SUSPICIOUS if reasons else ScanStatus.CLEAN,
        details=", ".join(reasons) if reasons else "no threats found",
        requires_attention=bool(reasons),
    )

from src.domain.enums import AlertLevel, ProcessingStatus, ScanStatus


def test_enum_values_match_database_strings():
    assert [s.value for s in ProcessingStatus] == [
        "uploaded",
        "processing",
        "processed",
        "failed",
    ]
    assert [s.value for s in ScanStatus] == ["clean", "suspicious", "failed"]
    assert [s.value for s in AlertLevel] == ["info", "warning", "critical"]


def test_enums_are_plain_strings_for_sqlalchemy():
    assert ProcessingStatus.PROCESSED == "processed"
    assert f"{AlertLevel.WARNING}" == "warning"
    assert isinstance(ScanStatus.CLEAN, str)

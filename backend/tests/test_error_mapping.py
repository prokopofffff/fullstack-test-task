from src.core.exceptions import DomainError, EmptyFile, FileNotFound, FileTooLarge


def test_domain_errors_carry_status_and_detail():
    assert isinstance(FileNotFound(), DomainError)
    assert (FileNotFound().status_code, FileNotFound().detail) == (404, "File not found")
    assert (EmptyFile().status_code, EmptyFile().detail) == (400, "File is empty")

    too_large = FileTooLarge(limit=1024)
    assert too_large.status_code == 413
    assert too_large.detail == "File exceeds the 1024 byte limit"


def test_domain_errors_do_not_depend_on_fastapi():
    import src.core.exceptions as module

    source = module.__file__
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    assert "fastapi" not in text.lower()

from src.core.exceptions import DomainError, EmptyFile, FileNotFound, FileTooLarge


def test_domain_errors_carry_kind_and_detail():
    assert isinstance(FileNotFound(), DomainError)
    assert (FileNotFound().kind, FileNotFound().detail) == ("not_found", "File not found")
    assert (EmptyFile().kind, EmptyFile().detail) == ("invalid_input", "File is empty")

    too_large = FileTooLarge(limit=1024)
    assert too_large.kind == "too_large"
    assert too_large.detail == "File exceeds the 1024 byte limit"


def test_domain_errors_do_not_depend_on_fastapi():
    import src.core.exceptions as module

    source = module.__file__
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    assert "fastapi" not in text.lower()

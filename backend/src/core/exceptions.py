class DomainError(Exception):
    """Базовое доменное исключение.

    `kind` — транспортно-нейтральный признак ошибки (не HTTP-код): перевод
    в конкретный код ответа делает api/errors.py, домен про HTTP не знает.
    """

    kind: str = "internal"
    detail: str = "Internal error"


class FileNotFound(DomainError):
    kind = "not_found"
    detail = "File not found"


class StoredFileMissing(DomainError):
    kind = "not_found"
    detail = "Stored file not found"


class EmptyFile(DomainError):
    kind = "invalid_input"
    detail = "File is empty"


class FileTooLarge(DomainError):
    kind = "too_large"

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.detail = f"File exceeds the {limit} byte limit"
        super().__init__(self.detail)

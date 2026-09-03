class DomainError(Exception):
    status_code: int = 500
    detail: str = "Internal error"


class FileNotFound(DomainError):
    status_code = 404
    detail = "File not found"


class StoredFileMissing(DomainError):
    status_code = 404
    detail = "Stored file not found"


class EmptyFile(DomainError):
    status_code = 400
    detail = "File is empty"


class FileTooLarge(DomainError):
    status_code = 413

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.detail = f"File exceeds the {limit} byte limit"
        super().__init__(self.detail)

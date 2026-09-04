from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import DomainError


async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Starlette типизирует обработчики как Callable[[Request, Exception], ...]
    # (параметр коллбэка контравариантен, поэтому уже сигнатура с DomainError
    # не подходит по типам), но реально сюда попадает только DomainError —
    # Starlette диспетчеризует по классу, зарегистрированному ниже.
    assert isinstance(exc, DomainError)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import DomainError

# Таблица "kind -> HTTP-статус" — единственное место, где доменная ошибка
# превращается в конкретный код ответа. src/core/exceptions.py транспортно
# нейтрален и HTTP не знает.
_STATUS_BY_KIND: dict[str, int] = {
    "not_found": 404,
    "invalid_input": 400,
    "too_large": 413,
}


async def domain_error_handler(_: Request, exc: Exception) -> JSONResponse:
    # Starlette типизирует обработчики как Callable[[Request, Exception], ...]
    # (параметр коллбэка контравариантен, поэтому уже сигнатура с DomainError
    # не подходит по типам), но реально сюда попадает только DomainError —
    # Starlette диспетчеризует по классу, зарегистрированному ниже.
    assert isinstance(exc, DomainError)
    status_code = _STATUS_BY_KIND.get(exc.kind, 500)
    return JSONResponse(status_code=status_code, content={"detail": exc.detail})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)

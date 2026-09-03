from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.exceptions import DomainError


async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)

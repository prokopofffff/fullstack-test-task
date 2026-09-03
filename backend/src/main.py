from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.errors import register_error_handlers
from src.api.v1.alerts import router as alerts_router
from src.api.v1.files import router as files_router
from src.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="File exchange")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(files_router)
    app.include_router(alerts_router)
    return app


app = create_app()

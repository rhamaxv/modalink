from fastapi import FastAPI

from app.api.v1 import health
from app.errors import register_error_handlers
from app.logging import catat_request


def create_app() -> FastAPI:
    app = FastAPI(title="Modalink API", version="0.1.0")
    app.include_router(health.router)
    register_error_handlers(app)
    app.middleware("http")(catat_request)
    return app


app = create_app()

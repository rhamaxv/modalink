from fastapi import FastAPI

from app.api.v1 import auth, campaigns, health, proposals
from app.errors import register_error_handlers
from app.logging import log_request


def create_app() -> FastAPI:
    app = FastAPI(title="Modalink API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(campaigns.router)
    app.include_router(proposals.router)
    register_error_handlers(app)
    app.middleware("http")(log_request)
    return app


app = create_app()

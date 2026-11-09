from fastapi import FastAPI

from app.api.v1 import auth, campaigns, health, internal, pledges, proposals
from app.config import settings
from app.errors import register_error_handlers
from app.logging import log_request


def create_app() -> FastAPI:
    app = FastAPI(title="Modalink API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(campaigns.router)
    app.include_router(proposals.router)
    app.include_router(pledges.router)
    # BR-63: router internal tidak didaftarkan sama sekali di ENV=prod,
    # sehingga setiap endpoint di bawahnya mengembalikan 404 murni dari
    # routing, bukan dari pemeriksaan di dalam handler yang bisa lupa dipasang.
    if settings.env != "prod":
        app.include_router(internal.router)
    register_error_handlers(app)
    app.middleware("http")(log_request)
    return app


app = create_app()

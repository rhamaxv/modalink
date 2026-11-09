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
    if settings.env == "dev":
        # Router internal tidak pernah ada di produksi, bukan sekadar
        # menolak request-nya (BR-63): include_router di luar blok ini
        # berarti ia terdaftar di app.routes apa pun ENV-nya.
        app.include_router(internal.router)
    register_error_handlers(app)
    app.middleware("http")(log_request)
    return app


app = create_app()

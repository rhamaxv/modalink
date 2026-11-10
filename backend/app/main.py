from fastapi import FastAPI

from app.api.v1 import (
    auth,
    campaigns,
    community,
    covers,
    health,
    internal,
    milestones,
    pledges,
    proposals,
)
from app.config import settings
from app.errors import register_error_handlers
from app.logging import log_request
from app.middleware import build_rate_limit_middleware


def create_app() -> FastAPI:
    app = FastAPI(title="Modalink API", version="0.1.0")
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(campaigns.router)
    app.include_router(proposals.router)
    app.include_router(pledges.router)
    app.include_router(milestones.router)
    app.include_router(community.router)
    app.include_router(covers.router)
    if settings.env == "dev":
        # Router internal tidak pernah ada di produksi, bukan sekadar menolak
        # request-nya (BR-63): include_router di luar blok ini berarti ia
        # terdaftar di app.routes apa pun ENV-nya. `== "dev"`, bukan
        # `!= "prod"`, karena BR-63 menyebut ENV=dev secara eksplisit.
        app.include_router(internal.router)
    register_error_handlers(app)
    # Urutan pendaftaran penting: Starlette menjadikan middleware yang
    # terdaftar BELAKANGAN sebagai lapisan TERLUAR. rate_limit didaftarkan
    # lebih dulu supaya log_request tetap jadi lapisan terluar dan ikut
    # mencatat respons 429 juga (review keamanan Finding 2), bukan
    # dilewati begitu rate_limit menolak sebuah request lebih dulu.
    app.middleware("http")(build_rate_limit_middleware())
    app.middleware("http")(log_request)
    return app


app = create_app()

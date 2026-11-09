"""Review keamanan Finding 2: limiter yang didorong sampai ke batasnya dan
sedikit lewat, bukan sekadar dua request yang kebetulan sama-sama lolos.

Tidak butuh database: ini middleware ASGI murni di atas aplikasi FastAPI
mini yang dibuat test ini sendiri, bukan `create_app()` produksi.
"""

import re

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.middleware import (
    DEFAULT_RATE_RULES,
    InMemoryRateLimiter,
    RateRule,
    build_rate_limit_middleware,
)
from app.services.auth import issue_token


def _buat_app(rules, limiter=None):
    app = FastAPI()
    app.middleware("http")(build_rate_limit_middleware(rules, limiter))

    dipanggil = {"n": 0}

    @app.post("/x")
    async def handler_x():
        dipanggil["n"] += 1
        return {"ok": True}

    app.state.dipanggil = dipanggil
    return app


async def _client(app):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_rate_limit_allows_up_to_the_limit_and_rejects_the_next_one():
    """Dipukul sampai batas lalu satu lagi lewat batas: limit=3 harus
    meloloskan tepat tiga request pertama dan menolak yang keempat dengan
    429, bukan sekadar mengirim dua request dan melihat dua 200."""
    rule = RateRule(
        name="x",
        method="POST",
        path=re.compile(r"^/x$"),
        ip_limit=3,
        window_s=60,
    )
    app = _buat_app((rule,))
    async with await _client(app) as client:
        kode = [(await client.post("/x")).status_code for _ in range(5)]

    assert kode == [200, 200, 200, 429, 429]
    assert app.state.dipanggil["n"] == 3, (
        "handler tidak boleh terpanggil untuk request yang ditolak"
    )


async def test_rate_limit_resets_after_the_window_passes():
    rule = RateRule(
        name="x",
        method="POST",
        path=re.compile(r"^/x$"),
        ip_limit=1,
        window_s=10,
    )
    jam = {"t": 0.0}
    limiter = InMemoryRateLimiter(time_fn=lambda: jam["t"])
    app = _buat_app((rule,), limiter)
    async with await _client(app) as client:
        pertama = await client.post("/x")
        kedua = await client.post("/x")
        jam["t"] += 10.0  # lewat satu jendela penuh
        ketiga = await client.post("/x")

    assert [pertama.status_code, kedua.status_code, ketiga.status_code] == [
        200,
        429,
        200,
    ]


async def test_rate_limit_is_scoped_per_ip_bucket_independent_of_other_rules():
    """Dua rule berbeda (dua path) pada IP yang sama punya bucket terpisah:
    menghabiskan limit salah satu tidak ikut menolak yang lain."""
    rule_a = RateRule(
        name="a",
        method="POST",
        path=re.compile(r"^/a$"),
        ip_limit=1,
        window_s=60,
    )
    rule_b = RateRule(
        name="b",
        method="POST",
        path=re.compile(r"^/b$"),
        ip_limit=1,
        window_s=60,
    )
    app = FastAPI()
    app.middleware("http")(build_rate_limit_middleware((rule_a, rule_b)))

    @app.post("/a")
    async def a():
        return {"ok": True}

    @app.post("/b")
    async def b():
        return {"ok": True}

    async with await _client(app) as client:
        a1 = await client.post("/a")
        a2 = await client.post("/a")
        b1 = await client.post("/b")

    assert a1.status_code == 200
    assert a2.status_code == 429
    assert b1.status_code == 200, "bucket /b tidak boleh ikut habis karena /a habis"


async def test_rate_limit_scopes_account_bucket_by_jwt_subject_not_just_ip():
    """Dua akun berbeda dari IP yang sama (httpx ASGITransport memakai IP
    klien yang sama untuk semua request) masing-masing punya jatah akun
    sendiri, selama limit per-IP cukup longgar untuk tidak ikut menolak
    lebih dulu."""
    rule = RateRule(
        name="submit",
        method="POST",
        path=re.compile(r"^/submit$"),
        ip_limit=100,  # longgar: yang diuji di sini jatah PER AKUN, bukan IP
        window_s=60,
        account_limit=1,
    )
    app = FastAPI()
    app.middleware("http")(build_rate_limit_middleware((rule,)))

    @app.post("/submit")
    async def submit():
        return {"ok": True}

    import uuid

    token_a = issue_token(uuid.uuid4(), "umkm")
    token_b = issue_token(uuid.uuid4(), "umkm")

    async with await _client(app) as client:
        akun_a_pertama = await client.post(
            "/submit", headers={"Authorization": f"Bearer {token_a}"}
        )
        akun_a_kedua = await client.post(
            "/submit", headers={"Authorization": f"Bearer {token_a}"}
        )
        akun_b_pertama = await client.post(
            "/submit", headers={"Authorization": f"Bearer {token_b}"}
        )

    assert akun_a_pertama.status_code == 200
    assert akun_a_kedua.status_code == 429, "akun a sudah habis jatahnya"
    assert akun_b_pertama.status_code == 200, "akun b punya jatah sendiri"


async def test_rate_limit_fails_closed_when_the_check_itself_breaks():
    """Membuktikan klaim 'gagal tertutup' di docstring app/middleware.py:
    limiter yang pemeriksaannya sendiri melempar exception harus membuat
    request DITOLAK (bukan 200, dan handler tidak boleh terpanggil), bukan
    diam-diam meloloskannya seolah limiter tidak pernah ada."""

    class LimiterRusak(InMemoryRateLimiter):
        def hit(self, key, limit, window_s):
            raise RuntimeError("state limiter korup")

    rule = RateRule(
        name="x",
        method="POST",
        path=re.compile(r"^/x$"),
        ip_limit=100,
        window_s=60,
    )
    app = _buat_app((rule,), LimiterRusak())
    async with await _client(app) as client:
        respons = await client.post("/x")

    assert respons.status_code == 429
    assert app.state.dipanggil["n"] == 0, (
        "handler tidak boleh terpanggil saat limiter gagal"
    )


def test_default_rate_rules_cover_the_five_routes_named_in_the_review():
    """Finding 2 menyebut lima jalur eksplisit: registrasi, login, submit
    proposal, pledge, dan komentar. Test ini gagal kalau salah satu hilang
    dari DEFAULT_RATE_RULES tanpa seorang pun sadar."""
    dicocokkan = {
        ("POST", "/api/v1/auth/register"): "register",
        ("POST", "/api/v1/auth/login"): "login",
        ("POST", "/api/v1/campaigns/11111111-1111-1111-1111-111111111111/proposals"): (
            "proposal_submit"
        ),
        ("POST", "/api/v1/proposals/11111111-1111-1111-1111-111111111111/pledges"): (
            "pledge_create"
        ),
        ("POST", "/api/v1/proposals/11111111-1111-1111-1111-111111111111/comments"): (
            "comment_create"
        ),
    }
    for (method, path), nama_diharapkan in dicocokkan.items():
        cocok = [
            r for r in DEFAULT_RATE_RULES if r.method == method and r.path.match(path)
        ]
        assert len(cocok) == 1, f"{method} {path} tidak cocok tepat satu rule"
        assert cocok[0].name == nama_diharapkan

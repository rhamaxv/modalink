"""R5: setiap endpoint kali setiap peran, plus kasus peran benar tapi bukan pemilik."""

from typing import Any

import pytest

# (method, path, peran atau None, status yang diharapkan)
# {campaign_id} di path diganti id campaign fixture sungguhan saat dikirim;
# campaign itu selalu milik akun "investor", jadi "investor_lain" di baris
# manapun berarti peran benar tapi bukan pemilik.
RBAC_MATRIX: list[tuple[str, str, str | None, int]] = [
    ("POST", "/api/v1/auth/register", None, 422),  # 422 karena body kosong
    ("POST", "/api/v1/auth/login", None, 422),  # 422 karena body kosong
    ("GET", "/api/v1/auth/me", None, 401),
    ("GET", "/api/v1/auth/me", "investor", 200),
    ("GET", "/api/v1/auth/me", "umkm", 200),
    ("GET", "/api/v1/auth/me", "community", 200),
    # POST tanpa token: peran belum diketahui, jadi 401 lebih dulu dari validasi body.
    ("POST", "/api/v1/campaigns", None, 401),
    ("POST", "/api/v1/campaigns", "umkm", 403),
    ("POST", "/api/v1/campaigns", "community", 403),
    # Investor lolos pagar peran; 422 di sini membuktikan itu, bukan body kosong.
    ("POST", "/api/v1/campaigns", "investor", 422),
    ("GET", "/api/v1/campaigns", None, 200),
    ("GET", "/api/v1/campaigns/{campaign_id}", None, 200),
    ("PATCH", "/api/v1/campaigns/{campaign_id}", None, 401),
    ("PATCH", "/api/v1/campaigns/{campaign_id}", "umkm", 403),  # peran salah
    ("PATCH", "/api/v1/campaigns/{campaign_id}", "investor_lain", 403),  # bukan pemilik
    ("PATCH", "/api/v1/campaigns/{campaign_id}", "investor", 200),
    ("POST", "/api/v1/campaigns/{campaign_id}/close", None, 401),
    ("POST", "/api/v1/campaigns/{campaign_id}/close", "umkm", 403),  # peran salah
    (
        "POST",
        "/api/v1/campaigns/{campaign_id}/close",
        "investor_lain",
        403,
    ),  # bukan pemilik
    ("POST", "/api/v1/campaigns/{campaign_id}/close", "investor", 200),
    ("GET", "/api/v1/campaigns/{campaign_id}/proposals", None, 200),
    ("POST", "/api/v1/campaigns/{campaign_id}/proposals", None, 401),
    (
        "POST",
        "/api/v1/campaigns/{campaign_id}/proposals",
        "investor",
        403,
    ),  # peran salah
    # 422 karena body kosong, sama seperti POST /campaigns; umkm lolos pagar peran.
    ("POST", "/api/v1/campaigns/{campaign_id}/proposals", "umkm", 422),
    ("GET", "/api/v1/proposals", None, 200),
    # Matriks ini cuma mengganti {campaign_id}, bukan {proposal_id}; literal
    # "{proposal_id}" gagal di-parse sebagai UUID sebelum dependency apa pun
    # jalan, jadi 422 di sini untuk peran manapun. Cakupan aturan akses baca
    # proposal yang sesungguhnya ada di tests/integration/test_proposal_akses.py.
    ("GET", "/api/v1/proposals/{proposal_id}", None, 422),
    # Beda dari baris di atas: dua endpoint ini dijaga require_role, dan
    # dependency itu gagal (401) sebelum literal "{proposal_id}" sempat
    # dicoba divalidasi sebagai UUID. Cakupan peran dan status sungguhan
    # (403 komunitas, 202/409 rescore) ada di tests/integration/test_scoring_flow.py
    # dan tests/regression/test_r6_ai_failure.py.
    ("POST", "/api/v1/proposals/{proposal_id}/rescore", None, 401),
    # H-4: require_role di dalam ambil_proposal_untuk_rescore_milik_sendiri
    # tetap sub-dependency, jadi peran yang salah (community, bukan UMKM
    # atau INVESTOR) ditolak 403 sebelum literal "{proposal_id}" dicoba
    # divalidasi sebagai UUID, sama seperti baris 401 di atas. Kasus peran
    # benar tapi bukan pemilik (404) ada di tests/integration/test_scoring_flow.py.
    ("POST", "/api/v1/proposals/{proposal_id}/rescore", "community", 403),
    ("GET", "/api/v1/proposals/{proposal_id}/scoring", None, 401),
    ("POST", "/api/v1/proposals/{proposal_id}/pledges", None, 401),
    # BR-28: peran salah ditolak 403 sebelum literal "{proposal_id}" dicoba
    # divalidasi sebagai UUID, dibuktikan empiris sama seperti baris rescore
    # di atas, bukan ditebak dari urutan dependency FastAPI.
    ("POST", "/api/v1/proposals/{proposal_id}/pledges", "umkm", 403),
    ("POST", "/api/v1/proposals/{proposal_id}/pledges", "community", 403),
    # Investor lolos pagar peran; 422 di sini membuktikan itu (literal
    # "{proposal_id}" gagal UUID sekaligus body kosong kehilangan `amount`),
    # bukan body kosong semata. Cakupan BR-20/21/22/25/26/27 sungguhan ada
    # di tests/integration/test_pledge.py dan test_pledge_amount.py.
    ("POST", "/api/v1/proposals/{proposal_id}/pledges", "investor", 422),
    ("DELETE", "/api/v1/pledges/{pledge_id}", None, 401),
    ("DELETE", "/api/v1/pledges/{pledge_id}", "umkm", 403),
    ("DELETE", "/api/v1/pledges/{pledge_id}", "community", 403),
    # Investor lolos pagar peran; 422 karena literal "{pledge_id}" gagal
    # divalidasi sebagai UUID. Kasus peran benar tapi bukan pemilik (403) dan
    # pembatalan sungguhan ada di tests/integration/test_pledge.py.
    ("DELETE", "/api/v1/pledges/{pledge_id}", "investor", 422),
    # Fase 08 (komunitas): vote dan komentar. Peran salah ditolak sebelum
    # literal "{proposal_id}" dicoba divalidasi sebagai UUID, sama seperti
    # pola pledges/rescore di atas; peran benar lolos ke 422 karena literal
    # itu. Toggle, BR-31, BR-30, dan kasus peran salah/benar sungguhan ada
    # di tests/integration/test_vote.py.
    ("POST", "/api/v1/proposals/{proposal_id}/vote", None, 401),
    ("POST", "/api/v1/proposals/{proposal_id}/vote", "investor", 403),  # peran salah
    ("POST", "/api/v1/proposals/{proposal_id}/vote", "umkm", 403),  # peran salah
    ("POST", "/api/v1/proposals/{proposal_id}/vote", "community", 422),
    # Publik tanpa pagar peran: literal "{proposal_id}" gagal UUID untuk
    # peran manapun, jadi satu baris saja cukup (pola yang sama dengan
    # GET /proposals/{proposal_id}). Cakupan isi daftar ada di
    # tests/integration/test_comment.py.
    ("GET", "/api/v1/proposals/{proposal_id}/comments", None, 422),
    ("POST", "/api/v1/proposals/{proposal_id}/comments", None, 401),
    (
        "POST",
        "/api/v1/proposals/{proposal_id}/comments",
        "investor",
        403,
    ),  # peran salah
    ("POST", "/api/v1/proposals/{proposal_id}/comments", "umkm", 403),  # peran salah
    ("POST", "/api/v1/proposals/{proposal_id}/comments", "community", 422),
    ("DELETE", "/api/v1/comments/{comment_id}", None, 401),
    ("DELETE", "/api/v1/comments/{comment_id}", "investor", 403),  # peran salah
    ("DELETE", "/api/v1/comments/{comment_id}", "umkm", 403),  # peran salah
    # Komunitas lolos pagar peran; 422 karena literal "{comment_id}" gagal
    # divalidasi sebagai UUID. Kasus peran benar tapi bukan penulis (403) dan
    # penghapusan sungguhan ada di tests/integration/test_comment.py.
    ("DELETE", "/api/v1/comments/{comment_id}", "community", 422),
    # Baris ditambahkan oleh setiap fase yang menambah endpoint.
]


@pytest.mark.parametrize("method,path,peran,harapan", RBAC_MATRIX)
async def test_r5_matriks_rbac(client, akun, campaign, method, path, peran, harapan):
    headers = akun[peran].headers if peran else {}
    url = path.replace("{campaign_id}", str(campaign.id))
    res = await client.request(method, url, headers=headers, json={})
    assert res.status_code == harapan, (
        f"{method} {path} sebagai {peran or 'anonim'}: "
        f"dapat {res.status_code}, harusnya {harapan}"
    )


def _semua_route(routes: list[Any]) -> list[Any]:
    """Masuk ke dalam setiap sub-router yang disertakan lewat include_router.

    Starlette membungkus router yang disertakan sebagai objek pembungkus yang
    tidak punya `.methods` sendiri; tanpa turun ke `original_router`, test di
    bawah ini memeriksa kumpulan route yang selalu kosong dan tidak pernah bisa
    merah, apa pun yang ditambahkan ke RBAC_MATRIX.
    """
    hasil: list[Any] = []
    for route in routes:
        if getattr(route, "methods", None):
            hasil.append(route)
        sub_router = getattr(route, "original_router", None)
        if sub_router is not None:
            hasil.extend(_semua_route(getattr(sub_router, "routes", [])))
    return hasil


def test_r5_setiap_route_punya_baris_di_matriks(app):
    """Endpoint baru tanpa baris baru di matriks membuat test ini merah."""
    DIKECUALIKAN = {
        "/health",
        "/openapi.json",
        "/docs",
        "/docs/oauth2-redirect",
        "/redoc",
    }
    terdaftar = {
        (metode, route.path)
        for route in _semua_route(app.routes)
        for metode in route.methods
        if metode not in {"HEAD", "OPTIONS"} and route.path not in DIKECUALIKAN
    }
    di_matriks = {(m, p) for m, p, _, _ in RBAC_MATRIX}
    belum_diuji = terdaftar - di_matriks
    assert not belum_diuji, (
        "Endpoint berikut belum punya baris di RBAC_MATRIX:\n  "
        + "\n  ".join(f"{m} {p}" for m, p in sorted(belum_diuji))
    )

"""R5: setiap endpoint kali setiap peran, plus kasus peran benar tapi bukan pemilik."""

import pytest

# (method, path, peran atau None, status yang diharapkan)
RBAC_MATRIX: list[tuple[str, str, str | None, int]] = [
    ("POST", "/api/v1/auth/register", None, 422),  # 422 karena body kosong
    ("POST", "/api/v1/auth/login", None, 422),  # 422 karena body kosong
    ("GET", "/api/v1/auth/me", None, 401),
    ("GET", "/api/v1/auth/me", "investor", 200),
    ("GET", "/api/v1/auth/me", "umkm", 200),
    ("GET", "/api/v1/auth/me", "community", 200),
    # Baris ditambahkan oleh setiap fase yang menambah endpoint.
]


@pytest.mark.parametrize("method,path,peran,harapan", RBAC_MATRIX)
async def test_r5_matriks_rbac(client, akun, method, path, peran, harapan):
    headers = akun[peran].headers if peran else {}
    res = await client.request(method, path, headers=headers, json={})
    assert res.status_code == harapan, (
        f"{method} {path} sebagai {peran or 'anonim'}: "
        f"dapat {res.status_code}, harusnya {harapan}"
    )


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
        for route in app.routes
        if getattr(route, "methods", None)
        for metode in route.methods
        if metode not in {"HEAD", "OPTIONS"} and route.path not in DIKECUALIKAN
    }
    di_matriks = {(m, p) for m, p, _, _ in RBAC_MATRIX}
    belum_diuji = terdaftar - di_matriks
    assert not belum_diuji, (
        "Endpoint berikut belum punya baris di RBAC_MATRIX:\n  "
        + "\n  ".join(f"{m} {p}" for m, p in sorted(belum_diuji))
    )

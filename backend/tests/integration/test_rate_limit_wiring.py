"""Review keamanan Finding 2: membuktikan rate limiter benar-benar terpasang
di `create_app()` produksi lewat app/main.py, bukan hanya diuji terisolasi
di tests/unit/test_rate_limit.py.

Memakai fixture `client`/`app`/`db` biasa dari conftest.py: middleware tidak
menyentuh database sama sekali (lihat app/middleware.py), jadi fixture
transaksi yang sama dengan test lain cukup. Setiap test dapat `app` baru
dari `create_app()`, jadi setiap test juga dapat limiter baru -- tidak ada
hitungan yang bocor antar test.
"""


async def test_rf2_register_endpoint_is_rate_limited_per_ip(client):
    """DEFAULT_RATE_RULES membatasi POST /api/v1/auth/register 5 per menit
    per IP (app/middleware.py). Enam percobaan dari "IP" yang sama (semua
    lewat ASGITransport yang sama) harus menyisakan yang keenam sebagai 429,
    bukan 201/400."""
    kode = []
    for i in range(6):
        r = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"ratelimit-register-{i}@contoh.id",
                "password": "rahasia123",
                "name": "Uji Rate Limit",
                "role": "umkm",
            },
        )
        kode.append(r.status_code)

    assert kode[:5] == [201, 201, 201, 201, 201]
    assert kode[5] == 429


async def test_rf2_login_endpoint_is_rate_limited_per_ip(client):
    """Limit login (10/menit/IP) tidak peduli kredensialnya benar atau
    salah -- keduanya tetap satu permintaan yang dihitung, sama seperti
    yang reviewer ingin dicegah (brute force credential)."""
    kode = [
        (
            await client.post(
                "/api/v1/auth/login",
                json={"email": "siapa-saja@contoh.id", "password": "salah-terus"},
            )
        ).status_code
        for _ in range(11)
    ]

    assert all(k == 401 for k in kode[:10]), "sepuluh percobaan pertama tetap diproses"
    assert kode[10] == 429

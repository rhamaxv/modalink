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


async def test_rf2_kyc_endpoint_is_rate_limited_to_close_the_nik_oracle(
    client, investor
):
    """POST /kyc membalas 409 untuk NIK yang sudah terdaftar dan 200 untuk
    yang belum. Tanpa batas, perbedaan itu adalah ORACLE: seseorang bisa
    menebak NIK satu per satu dan mengetahui siapa saja yang punya akun di
    sini. Tiga per menit per IP cukup longgar untuk orang yang salah
    mengetik nomornya sendiri, dan terlalu sempit untuk menyisir.
    """
    kode = []
    for i in range(4):
        r = await client.post(
            "/api/v1/kyc",
            headers=investor.headers,
            json={
                "full_name": "Penyisir NIK",
                "nik": f"32010117089{i:05d}",
                "bank_code": "bca",
                "account_holder_name": "Penyisir NIK",
                "account_number": "1234567890",
            },
        )
        kode.append(r.status_code)

    assert kode[3] == 429, kode
    # Tiga yang pertama tidak ditolak oleh limiter: yang dijaga di sini
    # adalah batasnya menyala di percobaan keempat, bukan bahwa seluruhnya
    # gagal karena sebab lain.
    assert 429 not in kode[:3], kode

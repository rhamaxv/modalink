import pytest

import app.services.auth as auth_service
from app.schemas.auth import LoginIn
from app.services.auth import KredensialSalah, authenticate_user


async def test_register_lalu_login(client):
    daftar = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "investor@contoh.id",
            "password": "rahasia123",
            "name": "Sari",
            "role": "investor",
        },
    )
    assert daftar.status_code == 201

    masuk = await client.post(
        "/api/v1/auth/login",
        json={"email": "investor@contoh.id", "password": "rahasia123"},
    )
    assert masuk.status_code == 200
    assert masuk.json()["token_type"] == "bearer"


async def test_br03_password_hash_tidak_pernah_dikembalikan(client):
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "a@contoh.id",
            "password": "rahasia123",
            "name": "A",
            "role": "umkm",
        },
    )
    assert "password_hash" not in res.text
    assert "rahasia123" not in res.text


async def test_login_salah_password_tidak_membocorkan_apakah_email_ada(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "a@contoh.id",
            "password": "rahasia123",
            "name": "A",
            "role": "umkm",
        },
    )
    ada = await client.post(
        "/api/v1/auth/login", json={"email": "a@contoh.id", "password": "salah"}
    )
    tidak_ada = await client.post(
        "/api/v1/auth/login", json={"email": "z@contoh.id", "password": "salah"}
    )
    assert ada.status_code == tidak_ada.status_code == 401
    assert ada.json() == tidak_ada.json()


async def test_br05_endpoint_me_butuh_token(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_me_mengembalikan_profil_tanpa_password_hash(client):
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "sari@contoh.id",
            "password": "rahasia123",
            "name": "Sari",
            "role": "investor",
        },
    )
    masuk = await client.post(
        "/api/v1/auth/login",
        json={"email": "sari@contoh.id", "password": "rahasia123"},
    )
    token = masuk.json()["access_token"]

    res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200
    isi = res.json()
    assert isi["email"] == "sari@contoh.id"
    assert isi["role"] == "investor"
    assert "password_hash" not in res.text
    assert "rahasia123" not in res.text


async def test_br02_email_duplikat_ditolak_400_bukan_500(client):
    """Menutup celah balapan: pemeriksaan di Python bisa dilewati dua registrasi
    bersamaan, dan constraint database yang menangkapnya harus diterjemahkan
    menjadi error yang rapi, bukan bocor sebagai 500."""
    isi = {
        "email": "kembar@contoh.id",
        "password": "rahasia123",
        "name": "Kembar",
        "role": "umkm",
    }
    assert (await client.post("/api/v1/auth/register", json=isi)).status_code == 201
    kedua = await client.post("/api/v1/auth/register", json=isi)
    assert kedua.status_code == 400
    assert kedua.json()["error"]["code"] == "email_terpakai"


async def test_login_argon2_tetap_jalan_untuk_email_tak_dikenal(db, monkeypatch):
    """Oracle waktu: tanpa HASH_UMPAN, email tak dikenal melewati argon2 lewat
    short-circuit `user is None`, sehingga responsnya terukur lebih cepat
    daripada password salah. Menghitung panggilan verify_password membuktikan
    argon2 tetap jalan pada kedua jalur."""
    panggilan = 0
    asli = auth_service.verify_password

    def terhitung(raw: str, hashed: str) -> bool:
        nonlocal panggilan
        panggilan += 1
        return asli(raw, hashed)

    monkeypatch.setattr(auth_service, "verify_password", terhitung)

    with pytest.raises(KredensialSalah):
        await authenticate_user(
            db, LoginIn(email="tidak-ada@contoh.id", password="apa saja")
        )
    assert panggilan == 1

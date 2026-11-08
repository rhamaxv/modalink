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

from pydantic import BaseModel

from app.errors import ConflictError


async def test_domain_error_jadi_bentuk_seragam(client, app):
    @app.get("/_boom")
    async def boom():
        raise ConflictError(
            "transisi_tidak_sah",
            "Proposal sudah funded.",
            detail={"current_status": "funded"},
        )

    res = await client.get("/_boom")
    assert res.status_code == 409
    assert res.json() == {
        "error": {
            "code": "transisi_tidak_sah",
            "message": "Proposal sudah funded.",
            "detail": {"current_status": "funded"},
        }
    }


async def test_request_validation_error_jadi_bentuk_seragam(client, app):
    class Body(BaseModel):
        nama: str

    @app.post("/_validasi")
    async def validasi(body: Body) -> dict[str, str]:
        return {"nama": body.nama}

    res = await client.post("/_validasi", json={})
    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "payload_tidak_valid"
    assert data["error"]["detail"]["errors"]


async def test_http_exception_jadi_bentuk_seragam(client, app):
    from fastapi import HTTPException

    @app.get("/_unauthorized")
    async def unauthorized() -> None:
        raise HTTPException(status_code=401, detail="Token tidak valid.")

    res = await client.get("/_unauthorized")
    assert res.status_code == 401
    assert res.json() == {
        "error": {
            "code": "kesalahan_permintaan",
            "message": "Token tidak valid.",
            "detail": {},
        }
    }


async def test_http_exception_meneruskan_header(client, app):
    from fastapi import HTTPException

    @app.get("/_unauthorized_header")
    async def unauthorized() -> None:
        raise HTTPException(
            status_code=401,
            detail="Token tidak valid.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    res = await client.get("/_unauthorized_header")
    assert res.status_code == 401
    assert res.headers["WWW-Authenticate"] == "Bearer"


async def test_http_exception_204_tidak_memuat_body(client, app):
    from fastapi import HTTPException

    @app.get("/_no_content")
    async def no_content() -> None:
        raise HTTPException(status_code=204)

    res = await client.get("/_no_content")
    assert res.status_code == 204
    assert res.content == b""

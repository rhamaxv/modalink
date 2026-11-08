import pytest

from app.errors import ConflictError


async def test_domain_error_jadi_bentuk_seragam(client, app):
    @app.get("/_boom")
    async def boom():
        raise ConflictError("transisi_tidak_sah", "Proposal sudah funded.",
                            detail={"current_status": "funded"})

    res = await client.get("/_boom")
    assert res.status_code == 409
    assert res.json() == {
        "error": {
            "code": "transisi_tidak_sah",
            "message": "Proposal sudah funded.",
            "detail": {"current_status": "funded"},
        }
    }

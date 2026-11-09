"""Guard peran: require_role memverifikasi ulang ke database, tidak percaya klaim token.

/api/v1/campaigns belum ada sebelum fase 03, jadi test di sini memasang route
uji coba sendiri lewat fixture `app` (pola yang sama dipakai
tests/integration/test_error_shape.py), sekadar untuk melatih require_role.
"""

from fastapi import Depends

from app.api.deps import require_role
from app.models.user import Role


async def test_br04_role_reverified_against_database(client, app, db, investor):
    """Token lama dengan role yang sudah berubah tidak boleh lolos."""

    @app.post("/_hanya_investor")
    async def hanya_investor(
        user=Depends(require_role(Role.INVESTOR)),
    ) -> dict[str, str]:
        return {"ok": "ya"}

    investor.user.role = Role.COMMUNITY
    await db.flush()

    res = await client.post("/_hanya_investor", headers=investor.headers, json={})
    assert res.status_code == 403


async def test_wrong_role_rejected_403_not_401(client, app, umkm):
    @app.post("/_hanya_investor")
    async def hanya_investor(
        user=Depends(require_role(Role.INVESTOR)),
    ) -> dict[str, str]:
        return {"ok": "ya"}

    res = await client.post("/_hanya_investor", headers=umkm.headers, json={})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "peran_tidak_berhak"


async def test_without_token_rejected_401(client, app):
    @app.post("/_hanya_investor")
    async def hanya_investor(
        user=Depends(require_role(Role.INVESTOR)),
    ) -> dict[str, str]:
        return {"ok": "ya"}

    res = await client.post("/_hanya_investor", json={})
    assert res.status_code == 401

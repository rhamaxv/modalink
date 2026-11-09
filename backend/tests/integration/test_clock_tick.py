"""Jam virtual tersimpan: ambil_clock, majukan_jam, reset_jam (D-06, BR-60, BR-63)."""

from datetime import timedelta
from typing import Any


def _semua_path(routes: list[Any]) -> set[str]:
    """Starlette membungkus setiap include_router() sebagai satu
    `_IncludedRouter` tanpa `.path` sendiri (lihat helper serupa
    `_semua_route` di tests/regression/test_r5_rbac.py); tanpa turun ke
    `original_router`, test di bawah memeriksa kumpulan path yang selalu
    kosong dan tidak pernah bisa merah."""
    hasil: set[str] = set()
    for route in routes:
        path = getattr(route, "path", None)
        if path is not None:
            hasil.add(path)
        sub_router = getattr(route, "original_router", None)
        if sub_router is not None:
            hasil |= _semua_path(getattr(sub_router, "routes", []))
    return hasil


async def test_without_offset_uses_real_clock(db):
    from app.domain.clock import SystemClock
    from app.services.clock_service import ambil_clock

    selisih = abs((await ambil_clock(db)).now() - SystemClock().now())
    assert selisih < timedelta(seconds=2)


async def test_tick_advances_clock(db):
    from app.services.clock_service import ambil_clock, majukan_jam

    sebelum = (await ambil_clock(db)).now()
    await majukan_jam(db, hari=30)
    sesudah = (await ambil_clock(db)).now()
    assert (
        timedelta(days=29, hours=23) < sesudah - sebelum < timedelta(days=30, hours=1)
    )


async def test_tick_is_cumulative(db):
    from app.services.clock_service import ambil_clock, majukan_jam

    sebelum = (await ambil_clock(db)).now()
    await majukan_jam(db, hari=10)
    await majukan_jam(db, hari=10)
    assert (await ambil_clock(db)).now() - sebelum > timedelta(days=19)


async def test_reset_returns_to_real_clock(db):
    from app.domain.clock import SystemClock
    from app.services.clock_service import ambil_clock, majukan_jam, reset_jam

    await majukan_jam(db, hari=100)
    await reset_jam(db)
    assert abs((await ambil_clock(db)).now() - SystemClock().now()) < timedelta(
        seconds=2
    )


async def test_br63_tick_endpoint_not_registered_when_env_prod(monkeypatch):
    """BR-63 ditegakkan secara struktural: endpointnya tidak sekadar
    mengembalikan 404, melainkan tidak pernah didaftarkan ke app.routes."""
    from app.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "env", "prod")
    rute = _semua_path(create_app().routes)
    assert "/api/v1/internal/clock/tick" not in rute


async def test_tick_endpoint_registered_when_env_dev(monkeypatch):
    """Pelengkap test di atas: pagar tidak boleh menyembunyikan endpoint di
    ENV manapun selain prod, atau test di atas bisa hijau karena alasan yang
    salah (endpoint tidak pernah terdaftar sama sekali)."""
    from app.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "env", "dev")
    rute = _semua_path(create_app().routes)
    assert "/api/v1/internal/clock/tick" in rute


async def test_tick_endpoint_advances_clock_seen_by_real_proposal_read(
    client, db, listed_proposal
):
    """D-06 hanya bermanfaat untuk demo juri kalau tick sungguhan lewat HTTP
    ikut mempengaruhi get_clock produksi, bukan cuma fixture test `majukan`
    yang memasang FrozenClock langsung lewat dependency_overrides."""
    res = await client.post("/api/v1/internal/clock/tick", json={"hari": 30})
    assert res.status_code == 200

    detail = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert detail["status"] == "failed"

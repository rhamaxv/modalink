"""Endpoint debug untuk demo juri: memajukan jam virtual tanpa menunggu (BR-63, D-06).

Router ini sendiri tidak pernah terdaftar di produksi (lihat app/main.py,
`if settings.env == "dev"`), jadi tidak ada pagar role atau auth di sini --
siapa pun yang bisa mencapai endpoint ini sudah berarti ENV=dev.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.internal import ClockOut, TickIn
from app.services.clock_service import ambil_clock, majukan_jam

router = APIRouter(prefix="/api/v1/internal/clock", tags=["internal"])


@router.post("/tick", response_model=ClockOut)
async def tick_endpoint(
    body: TickIn,
    session: AsyncSession = Depends(get_session),
) -> ClockOut:
    await majukan_jam(session, body.hari)
    clock = await ambil_clock(session)
    return ClockOut(virtual_now=clock.now())

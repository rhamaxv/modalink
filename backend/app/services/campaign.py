"""Orkestrasi campaign: validasi deadline, pembuatan, dan daftar (BR-64)."""

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.clock import Clock
from app.errors import UnprocessableError
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.campaign import CampaignIn


def validasi_deadline(body: CampaignIn, clock: Clock) -> None:
    sekarang = clock.now()
    if body.apply_deadline <= sekarang:
        raise UnprocessableError(
            "apply_deadline_lampau", "Deadline pengajuan harus di masa depan."
        )
    if body.funding_deadline <= body.apply_deadline:
        raise UnprocessableError(
            "urutan_deadline_salah",
            "Deadline pendanaan harus setelah deadline pengajuan.",
            detail={"apply_deadline": body.apply_deadline.isoformat()},
        )


async def buat_campaign(
    session: AsyncSession, investor: User, body: CampaignIn, clock: Clock
) -> Campaign:
    validasi_deadline(body, clock)
    campaign = Campaign(
        investor_id=investor.id,
        title=body.title,
        description=body.description,
        sector=body.sector,
        target_amount=body.target_amount,
        apply_deadline=body.apply_deadline,
        funding_deadline=body.funding_deadline,
        score_threshold=body.score_threshold,
        created_at=clock.now(),
    )
    session.add(campaign)
    await session.flush()
    return campaign


async def daftar_campaign(session: AsyncSession) -> list[Campaign]:
    # Urutan diputus created_at lalu id supaya daftar deterministik (BR-05):
    # dua campaign dengan created_at identik tidak boleh bertukar posisi
    # antar-request.
    # Nama kolom sebagai string, bukan Campaign.created_at.desc(): atribut kelas
    # SQLModel diketik sebagai datetime/UUID biasa oleh mypy (tidak ada plugin
    # sqlmodel), sehingga .desc() di atasnya dianggap tidak ada.
    hasil = await session.scalars(
        select(Campaign).order_by(desc("created_at"), desc("id"))
    )
    return list(hasil)

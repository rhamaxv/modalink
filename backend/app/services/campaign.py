"""Orkestrasi campaign: validasi deadline, pembuatan, daftar, ubah, dan tutup
(BR-64, BR-77, T-40, T-41)."""

from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.domain.clock import Clock
from app.domain.transitions import CampaignEvent, IllegalTransition, apply_campaign
from app.domain.transitions import CampaignStatus as DomainCampaignStatus
from app.errors import ConflictError, UnprocessableError
from app.models.campaign import Campaign, CampaignStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.user import User
from app.schemas.campaign import CampaignIn, CampaignUpdateIn

# Status proposal yang dianggap publik: "listed ke atas" menurut
# 03-feature-investor.md. submitted (belum dinilai) dan rejected disembunyikan
# dari siapa pun selain pembuat campaign.
STATUS_PROPOSAL_PUBLIK = frozenset(ProposalStatus) - {
    ProposalStatus.SUBMITTED,
    ProposalStatus.REJECTED,
}


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


def _tutup(campaign: Campaign, event: CampaignEvent) -> None:
    # Jembatan nilai, bukan assignment langsung: CampaignStatus di models/
    # berbeda kelas dari CampaignStatus di domain/transitions.py (lihat
    # docstring modul campaign.py), tapi nilai stringnya sama sehingga
    # apply_campaign tetap bisa dipanggil (D-04).
    baru = apply_campaign(DomainCampaignStatus(campaign.status.value), event)
    campaign.status = CampaignStatus(baru.value)


async def ambil_campaign_detail(
    session: AsyncSession, campaign_id: UUID, clock: Clock
) -> Campaign | None:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        return None
    if campaign.status is CampaignStatus.OPEN and clock.now() > campaign.apply_deadline:
        # Penutupan lambat (T-41): tidak ada job terjadwal di fase ini, jadi
        # status disesuaikan begitu campaign ini dibaca lagi setelah lewat.
        _tutup(campaign, CampaignEvent.APPLY_DEADLINE_LEWAT)
        await session.flush()
    return campaign


async def tutup_campaign_manual(session: AsyncSession, campaign: Campaign) -> Campaign:
    try:
        _tutup(campaign, CampaignEvent.TUTUP_MANUAL)
    except IllegalTransition:
        raise ConflictError(
            "campaign_sudah_tertutup", "Campaign ini sudah tertutup."
        ) from None
    await session.flush()
    return campaign


async def ubah_campaign(
    session: AsyncSession, campaign: Campaign, body: CampaignUpdateIn
) -> Campaign:
    if (
        body.score_threshold is not None
        and body.score_threshold != campaign.score_threshold
    ):
        ada_proposal = await session.scalar(
            select(func.count())
            .select_from(Proposal)
            .where(Proposal.campaign_id == campaign.id)
        )
        if ada_proposal:
            # Mengubah ambang setelah penilaian berjalan membuat skor antar
            # proposal tidak lagi sebanding (BR-77).
            raise ConflictError(
                "threshold_terkunci",
                "Ambang skor tidak bisa diubah setelah ada proposal masuk.",
                detail={"jumlah_proposal": ada_proposal},
            )
        campaign.score_threshold = body.score_threshold
    if body.title is not None:
        campaign.title = body.title
    if body.description is not None:
        campaign.description = body.description
    await session.flush()
    return campaign


async def daftar_proposal_campaign(
    session: AsyncSession, campaign: Campaign, pemilik: bool
) -> list[Proposal]:
    kueri = select(Proposal).where(Proposal.campaign_id == campaign.id)
    if not pemilik:
        # Publik hanya melihat yang listed ke atas; submitted dan rejected
        # hanya boleh dilihat pembuat campaign (03-feature-investor.md).
        kueri = kueri.where(col(Proposal.status).in_(STATUS_PROPOSAL_PUBLIK))
    hasil = await session.scalars(kueri.order_by(desc("created_at"), desc("id")))
    return list(hasil)

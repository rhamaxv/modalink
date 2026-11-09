"""Orkestrasi proposal: submission dan aturan akses baca (BR-10 sampai BR-18)."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.domain.clock import Clock
from app.domain.milestone_plan import MilestoneDraft, validate_milestone_plan
from app.domain.money import format_rupiah
from app.errors import ConflictError, UnprocessableError
from app.models.campaign import Campaign, CampaignStatus
from app.models.milestone_report import MilestoneReport
from app.models.proposal import (
    Proposal,
    ProposalMilestone,
    ProposalStatus,
    ScoringStatus,
)
from app.models.user import User
from app.schemas.proposal import ProposalIn
from app.services.campaign import STATUS_PROPOSAL_PUBLIK
from app.services.expiry import evaluasi_kedaluwarsa_banyak

MINIMAL_REQUESTED_AMOUNT = 500_000  # BR-12: di bawah ini biaya screening tidak sepadan.


async def submit_proposal(
    session: AsyncSession,
    umkm: User,
    campaign: Campaign,
    body: ProposalIn,
    clock: Clock,
) -> Proposal:
    if (
        campaign.status is CampaignStatus.CLOSED
        or clock.now() >= campaign.apply_deadline
    ):
        raise ConflictError(
            "pengajuan_ditutup", "Campaign ini sudah tidak menerima proposal baru."
        )

    if body.requested_amount > campaign.target_amount:
        raise UnprocessableError(
            "dana_melebihi_target_campaign",
            "Dana yang diminta melebihi dana target campaign.",
            detail={"target_amount": campaign.target_amount},
        )
    if body.requested_amount < MINIMAL_REQUESTED_AMOUNT:
        raise UnprocessableError(
            "dana_di_bawah_minimum",
            f"Dana yang diminta minimal {format_rupiah(MINIMAL_REQUESTED_AMOUNT)}.",
            detail={"minimal_amount": MINIMAL_REQUESTED_AMOUNT},
        )

    drafts = [MilestoneDraft(**m.model_dump()) for m in body.milestones]
    try:
        validate_milestone_plan(drafts, body.requested_amount)
    except ValueError as exc:
        raise UnprocessableError("rencana_milestone_tidak_valid", str(exc)) from None

    proposal = Proposal(
        campaign_id=campaign.id,
        umkm_id=umkm.id,
        business_name=body.business_name,
        business_profile=body.business_profile,
        fund_usage_plan=body.fund_usage_plan,
        business_projection=body.business_projection,
        requested_amount=body.requested_amount,
        status=ProposalStatus.SUBMITTED,
        scoring_status=ScoringStatus.PENDING,
        created_at=clock.now(),
    )
    session.add(proposal)
    try:
        await session.flush()
    except IntegrityError:
        # Partial unique index yang menangkapnya, bukan pemeriksaan di Python,
        # sehingga dua request bersamaan pun tetap tertangkap (BR-13).
        raise ConflictError(
            "proposal_aktif_sudah_ada",
            "Anda sudah punya proposal aktif di campaign ini.",
        ) from None

    for draft in drafts:
        session.add(
            ProposalMilestone(
                proposal_id=proposal.id,
                seq=draft.seq,
                title=draft.title,
                description=draft.description,
                amount=draft.amount,
            )
        )
    await session.flush()
    return proposal


async def ambil_proposal(session: AsyncSession, proposal_id: UUID) -> Proposal | None:
    return await session.get(Proposal, proposal_id)


def boleh_melihat(proposal: Proposal, campaign: Campaign, user: User | None) -> bool:
    if proposal.status in STATUS_PROPOSAL_PUBLIK:
        return True
    if user is None:
        return False
    return user.id in {proposal.umkm_id, campaign.investor_id}


async def daftar_proposal_publik(session: AsyncSession, clock: Clock) -> list[Proposal]:
    # Urutan diputus created_at lalu id, sama seperti daftar_campaign (BR-05):
    # dua proposal dengan created_at identik tidak boleh bertukar posisi
    # antar-request.
    hasil = list(
        await session.scalars(
            select(Proposal)
            .where(col(Proposal.status).in_(STATUS_PROPOSAL_PUBLIK))
            .order_by(desc("created_at"), desc("id"))
        )
    )
    # D-06/BR-61: daftar ini juga "pembacaan proposal", jadi proposal yang
    # funding_deadline-nya lewat harus ikut direkonsiliasi di sini, bukan
    # hanya saat dibaca satu-satu lewat GET /proposals/{id}. Lewat fungsi
    # _banyak, bukan loop per baris dalam urutan tampil di atas: urutan
    # tampil created_at DESC, id DESC bukan urutan yang aman dipakai mengunci
    # baris (review keamanan Finding 1, lihat docstring evaluasi_kedaluwarsa_banyak).
    await evaluasi_kedaluwarsa_banyak(session, hasil, clock)
    return hasil


async def daftar_proposal_milik(session: AsyncSession, umkm_id: UUID) -> list[Proposal]:
    """GET /proposals/mine (10-api-contract.md:57). Tidak menyaring status:
    pemiliknya boleh melihat seluruh proposalnya sendiri termasuk rejected
    dan failed, beda dari daftar_proposal_publik yang menyaring
    STATUS_PROPOSAL_PUBLIK untuk pengunjung yang bukan pemilik."""
    hasil = await session.scalars(
        select(Proposal)
        .where(Proposal.umkm_id == umkm_id)
        .order_by(desc("created_at"), desc("id"))
    )
    return list(hasil)


@dataclass
class MilestoneDenganLaporanTerbaru:
    """Milestone dibungkus laporan terbarunya, khusus bentuk balik
    `daftar_milestone_proposal`. `ProposalMilestone` sengaja tidak boleh
    dititipi atribut bebas seperti `.latest_report` langsung (SQLModel/
    Pydantic v2 menolaknya), sama alasannya dengan `ProposalDenganSinyal`
    di services/campaign.py."""

    milestone: ProposalMilestone
    latest_report: MilestoneReport | None

    def __getattr__(self, name: str):
        return getattr(self.milestone, name)


async def daftar_milestone_proposal(
    session: AsyncSession, proposal_id: UUID
) -> list[MilestoneDenganLaporanTerbaru]:
    """GET /proposals/{id}/milestones (10-api-contract.md:73), diurutkan
    per tahap (seq), bukan per waktu dibuat: urutan tahap pendanaan memang
    seq, bukan kapan baris itu ditulis ke database.

    Laporan terbaru per milestone diambil lewat satu query DISTINCT ON,
    bukan satu query per milestone: pola yang sama dengan skor terbaru di
    daftar_proposal_campaign (services/campaign.py). milestone_reports tidak
    punya kolom proposal_id (hanya milestone_id), jadi join ke
    proposal_milestones yang menyaring proposalnya.
    """
    milestones = list(
        await session.scalars(
            select(ProposalMilestone)
            .where(ProposalMilestone.proposal_id == proposal_id)
            .order_by("seq")
        )
    )

    laporan_terbaru = (
        select(MilestoneReport)
        .join(
            ProposalMilestone,
            col(MilestoneReport.milestone_id) == col(ProposalMilestone.id),
        )
        .where(ProposalMilestone.proposal_id == proposal_id)
        .ext(distinct_on(col(MilestoneReport.milestone_id)))
        .order_by(
            col(MilestoneReport.milestone_id), desc(col(MilestoneReport.submitted_at))
        )
    )
    oleh_milestone = {
        laporan.milestone_id: laporan
        for laporan in await session.scalars(laporan_terbaru)
    }

    return [
        MilestoneDenganLaporanTerbaru(
            milestone=m, latest_report=oleh_milestone.get(m.id)
        )
        for m in milestones
    ]

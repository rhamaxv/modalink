"""Orkestrasi proposal: submission dan aturan akses baca (BR-10 sampai BR-18)."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import desc, func
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
from app.services.campaign import PUBLIC_PROPOSAL_STATUSES
from app.services.expiry import evaluate_expiry_many
from app.services.ledger import collected_amount_subquery

MINIMAL_REQUESTED_AMOUNT = 500_000  # BR-12: di bawah ini biaya screening tidak sepadan.

# Server-enforced, bukan sekadar default klien (Task 4 review keamanan):
# GET /proposals mengembalikan 7.2 MB untuk dua belas proposal seeded karena
# tidak ada batas atas sama sekali. 50 cukup untuk satu halaman penuh
# landing page publik tanpa membuka jalan request page_size=100000 yang
# sama parahnya dengan tidak ada paginasi sama sekali.
PROPOSAL_PAGE_SIZE_DEFAULT = 20
PROPOSAL_PAGE_SIZE_MAX = 50


@dataclass
class ProposalWithCollectedAmount:
    """Proposal dibungkus total dana terkumpul (BR-51, Task 1), khusus
    bentuk balik `list_public_proposals`/`list_own_proposals`/endpoint
    detail dan submit. Pola yang sama dengan `ProposalWithSignals` di
    services/campaign.py: Proposal sengaja tidak boleh dititipi atribut
    bebas langsung (SQLModel/Pydantic v2 menolaknya)."""

    proposal: Proposal
    collected_amount: int

    def __getattr__(self, name: str):
        return getattr(self.proposal, name)

    @property
    def business_profile_excerpt(self) -> str:
        """Cuplikan profil usaha untuk kartu di endpoint daftar.

        Dipotong di sini, bukan di browser: memotong di klien berarti seluruh
        rencana bisnis tetap dikirim, dan itu justru yang membuat respons
        daftar mencapai 7,2 MB untuk dua belas proposal."""
        penuh = self.proposal.business_profile
        return penuh if len(penuh) <= 200 else penuh[:200].rstrip() + "..."


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


async def get_proposal(session: AsyncSession, proposal_id: UUID) -> Proposal | None:
    return await session.get(Proposal, proposal_id)


def can_view(proposal: Proposal, campaign: Campaign, user: User | None) -> bool:
    if proposal.status in PUBLIC_PROPOSAL_STATUSES:
        return True
    if user is None:
        return False
    return user.id in {proposal.umkm_id, campaign.investor_id}


async def list_public_proposals(
    session: AsyncSession,
    clock: Clock,
    page: int = 1,
    page_size: int = PROPOSAL_PAGE_SIZE_DEFAULT,
) -> tuple[list[ProposalWithCollectedAmount], int]:
    """GET /proposals (Task 4, perluasan kontrak): paginasi server-enforced,
    bukan sekadar klien yang sopan -- `page_size` sudah diklem di
    api/v1/proposals.py lewat Query(le=PROPOSAL_PAGE_SIZE_MAX) sebelum sampai
    sini, jadi baris ini tidak lagi memanggil satu query SELECT COUNT per
    baris maupun mengambil seluruh tabel ke memori.

    `collected_amount` ikut di-JOIN lewat `collected_amount_subquery()`
    (Task 1), bukan dipanggil satu-satu per baris proposal: dengan dua belas
    proposal publik, memanggil `collected_amount_for_proposal` di dalam loop
    berarti tiga belas query (satu daftar + dua belas ledger), dan jumlah itu
    bertambah linear seiring proposal baru (N+1 klasik).
    """
    terkumpul = collected_amount_subquery()
    kueri_dasar = select(Proposal).where(
        col(Proposal.status).in_(PUBLIC_PROPOSAL_STATUSES)
    )
    total = await session.scalar(
        select(func.count()).select_from(kueri_dasar.subquery())
    )

    # Urutan diputus created_at lalu id, sama seperti list_campaigns (BR-05):
    # dua proposal dengan created_at identik tidak boleh bertukar posisi
    # antar-request/antar-halaman.
    baris = (
        await session.execute(
            select(Proposal, func.coalesce(terkumpul.c.collected_amount, 0))
            .outerjoin(terkumpul, terkumpul.c.proposal_id == Proposal.id)
            .where(col(Proposal.status).in_(PUBLIC_PROPOSAL_STATUSES))
            .order_by(desc("created_at"), desc("id"))
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).all()

    # D-06/BR-61: daftar ini juga "pembacaan proposal", jadi proposal yang
    # funding_deadline-nya lewat harus ikut direkonsiliasi di sini, bukan
    # hanya saat dibaca satu-satu lewat GET /proposals/{id}. Lewat fungsi
    # _banyak, bukan loop per baris dalam urutan tampil di atas: urutan tampil
    # created_at DESC, id DESC bukan urutan yang aman dipakai mengunci baris
    # (review keamanan Finding 1, lihat docstring evaluate_expiry_many).
    # Hanya baris di halaman ini, bukan seluruh tabel, konsisten dengan
    # tujuan paginasi.
    await evaluate_expiry_many(session, [p for p, _ in baris], clock)

    return [
        ProposalWithCollectedAmount(proposal=p, collected_amount=int(jumlah))
        for p, jumlah in baris
    ], int(total or 0)


async def list_own_proposals(
    session: AsyncSession, umkm_id: UUID
) -> list[ProposalWithCollectedAmount]:
    """GET /proposals/mine (10-api-contract.md:57). Tidak menyaring status:
    pemiliknya boleh melihat seluruh proposalnya sendiri termasuk rejected
    dan failed, beda dari list_public_proposals yang menyaring
    PUBLIC_PROPOSAL_STATUSES untuk pengunjung yang bukan pemilik.

    `collected_amount` di-JOIN sama seperti list_public_proposals, dengan
    alasan N+1 yang sama persis."""
    terkumpul = collected_amount_subquery()
    baris = (
        await session.execute(
            select(Proposal, func.coalesce(terkumpul.c.collected_amount, 0))
            .outerjoin(terkumpul, terkumpul.c.proposal_id == Proposal.id)
            .where(Proposal.umkm_id == umkm_id)
            .order_by(desc("created_at"), desc("id"))
        )
    ).all()
    return [
        ProposalWithCollectedAmount(proposal=p, collected_amount=int(jumlah))
        for p, jumlah in baris
    ]


@dataclass
class MilestoneWithLatestReport:
    """Milestone dibungkus laporan terbarunya, khusus bentuk balik
    `list_proposal_milestones`. `ProposalMilestone` sengaja tidak boleh
    dititipi atribut bebas seperti `.latest_report` langsung (SQLModel/
    Pydantic v2 menolaknya), sama alasannya dengan `ProposalWithSignals`
    di services/campaign.py."""

    milestone: ProposalMilestone
    latest_report: MilestoneReport | None

    def __getattr__(self, name: str):
        return getattr(self.milestone, name)


async def list_proposal_milestones(
    session: AsyncSession, proposal_id: UUID
) -> list[MilestoneWithLatestReport]:
    """GET /proposals/{id}/milestones (10-api-contract.md:73), diurutkan
    per tahap (seq), bukan per waktu dibuat: urutan tahap pendanaan memang
    seq, bukan kapan baris itu ditulis ke database.

    Laporan terbaru per milestone diambil lewat satu query DISTINCT ON,
    bukan satu query per milestone: pola yang sama dengan skor terbaru di
    list_campaign_proposals (services/campaign.py). milestone_reports tidak
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
        MilestoneWithLatestReport(milestone=m, latest_report=oleh_milestone.get(m.id))
        for m in milestones
    ]

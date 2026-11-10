"""Orkestrasi campaign: validasi deadline, pembuatan, daftar, ubah, dan tutup
(BR-64, BR-77, T-40, T-41)."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.domain.clock import Clock
from app.domain.transitions import CampaignEvent, IllegalTransition
from app.errors import ConflictError, UnprocessableError
from app.models.campaign import Campaign, CampaignStatus, Sector
from app.models.proposal import Proposal, ProposalStatus
from app.models.scoring import ScoringResult
from app.models.user import User
from app.models.vote import Vote
from app.schemas.campaign import CampaignIn, CampaignUpdateIn
from app.services.expiry import evaluate_expiry_many
from app.services.ledger import collected_amount_subquery
from app.services.status import advance_campaign

# Status proposal yang dianggap publik: "listed ke atas" menurut
# 03-feature-investor.md. submitted (belum dinilai) dan rejected disembunyikan
# dari siapa pun selain pembuat campaign.
PUBLIC_PROPOSAL_STATUSES = frozenset(ProposalStatus) - {
    ProposalStatus.SUBMITTED,
    ProposalStatus.REJECTED,
}


def validate_deadline(body: CampaignIn, clock: Clock) -> None:
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


async def create_campaign(
    session: AsyncSession, investor: User, body: CampaignIn, clock: Clock
) -> Campaign:
    validate_deadline(body, clock)
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


# Sama seperti proposal (services/proposal.py): tanpa batas atas, satu
# request bisa menarik seluruh tabel. Endpoint ini sebelumnya tidak
# berparameter `page` sama sekali walau kontrak menyebutnya
# (10-api-contract.md:44), jadi daftar campaign publik mengirim setiap baris
# yang ada ke setiap pengunjung.
CAMPAIGN_PAGE_SIZE_DEFAULT = 20
CAMPAIGN_PAGE_SIZE_MAX = 50


@dataclass
class CampaignWithCover:
    """Campaign dibungkus waktu pembaruan sampulnya.

    Pola yang sama dengan ProposalWithCollectedAmount di services/proposal.py,
    dan alasannya sama: Campaign adalah model SQLModel/Pydantic v2 yang
    menolak dititipi atribut bebas.
    """

    campaign: Campaign
    cover_updated_at: datetime | None = None

    def __getattr__(self, name: str):
        return getattr(self.campaign, name)


async def list_campaigns(
    session: AsyncSession,
    pemilik: User | None = None,
    sector: Sector | None = None,
    page: int = 1,
    page_size: int = CAMPAIGN_PAGE_SIZE_DEFAULT,
) -> tuple[list[Campaign], int]:
    """Daftar campaign publik, atau campaign milik satu investor.

    `10-api-contract.md:44` menyebut endpoint publiknya mengembalikan campaign
    `open`, dan sebelumnya tidak ada penyaring status sama sekali sehingga
    campaign yang sudah ditutup ikut muncul di penelusuran. Tapi menyaringnya
    begitu saja memutus kebutuhan lain: investor harus tetap bisa melihat
    campaign miliknya sendiri yang sudah ditutup di halaman "Campaign saya".

    Karena itu dua jalur, bukan satu filter: tanpa `pemilik` ia daftar publik
    dan hanya `open`; dengan `pemilik` ia seluruh campaign milik orang itu apa
    pun statusnya. Jalur kedua sekaligus menutup temuan review keamanan bahwa
    setiap investor mengunduh seluruh campaign investor lain lalu
    menyembunyikannya di browser.

    Mengembalikan pasangan (baris, total), bukan daftar saja: tanpa total,
    antarmuka tidak bisa membedakan "ini memang semua" dari "ini dua puluh
    pertama dari delapan puluh", dan diam-diam menyembunyikan sisanya.
    """
    # Urutan diputus created_at lalu id supaya daftar deterministik (BR-05):
    # dua campaign dengan created_at identik tidak boleh bertukar posisi
    # antar-request, dan dengan paginasi seri yang tidak diputus berarti satu
    # campaign bisa muncul di dua halaman sekaligus.
    kueri = select(Campaign)
    if pemilik is None:
        kueri = kueri.where(Campaign.status == CampaignStatus.OPEN)
    else:
        kueri = kueri.where(Campaign.investor_id == pemilik.id)
    if sector is not None:
        kueri = kueri.where(Campaign.sector == sector)

    total = await session.scalar(select(func.count()).select_from(kueri.subquery()))
    hasil = await session.scalars(
        kueri.order_by(col(Campaign.created_at).desc(), col(Campaign.id).desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return list(hasil), int(total or 0)


async def get_campaign(session: AsyncSession, campaign_id: UUID) -> Campaign | None:
    return await session.get(Campaign, campaign_id)


async def get_campaign_detail(
    session: AsyncSession, campaign_id: UUID, clock: Clock
) -> Campaign | None:
    campaign = await get_campaign(session, campaign_id)
    if campaign is None:
        return None
    if campaign.status is CampaignStatus.OPEN and clock.now() > campaign.apply_deadline:
        # Penutupan lambat (T-41): tidak ada job terjadwal di fase ini, jadi
        # status disesuaikan begitu campaign ini dibaca lagi setelah lewat.
        advance_campaign(campaign, CampaignEvent.APPLY_DEADLINE_LEWAT)
        await session.flush()
    return campaign


async def close_campaign_manually(
    session: AsyncSession, campaign: Campaign
) -> Campaign:
    try:
        advance_campaign(campaign, CampaignEvent.TUTUP_MANUAL)
    except IllegalTransition:
        raise ConflictError(
            "campaign_sudah_tertutup", "Campaign ini sudah tertutup."
        ) from None
    await session.flush()
    return campaign


async def update_campaign(
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


@dataclass
class ProposalWithSignals:
    """Proposal dibungkus skor AI terbaru dan jumlah vote, khusus bentuk
    balik `list_campaign_proposals`. `ProposalWithSignalsOut` membacanya
    lewat `from_attributes`, yang memanggil getattr apa adanya -- __getattr__
    di sini meneruskan kolom Proposal asli, sama seperti ProposalWithPledge
    di tests/conftest.py. Proposal tidak boleh dititipi atribut bebas secara
    langsung (lihat docstring di sana): SQLModel/Pydantic v2 menolaknya."""

    proposal: Proposal
    total_score: int
    vote_count: int
    # Task 1: ProposalOut (yang ProposalWithSignalsOut mewarisi) sekarang
    # wajib punya collected_amount, jadi baris ini wajib ikut diisi di sini
    # juga, bukan hanya di services/proposal.py.
    collected_amount: int

    def __getattr__(self, name: str):
        return getattr(self.proposal, name)


async def list_campaign_proposals(
    session: AsyncSession, campaign: Campaign, pemilik: bool, clock: Clock
) -> list[ProposalWithSignals]:
    """Skor lalu vote lalu waktu submit (10-api-contract.md). `created_at`
    lalu `id` di akhir yang membuat urutan ini benar-benar deterministik:
    tanpa itu, dua proposal yang identik di seluruh kolom pengurut bisa
    bertukar posisi antar-request.

    Skor yang dipakai adalah baris terbaru per proposal lewat `DISTINCT ON`,
    bukan baris pertama atau penjumlahan semua baris -- scoring_results
    append-only (BR-76), jadi satu proposal bisa punya banyak baris dari
    rescore.
    """
    # col(...), bukan ScoringResult.proposal_id langsung: atribut kelas
    # SQLModel diketik sebagai UUID/datetime biasa oleh mypy (tidak ada
    # plugin sqlmodel), sehingga distinct_on/.desc()/group_by di atasnya
    # dianggap tidak ada (sama seperti catatan desc("created_at") di
    # list_campaigns).
    skor_terbaru = (
        select(ScoringResult.proposal_id, ScoringResult.total_score)
        .ext(distinct_on(col(ScoringResult.proposal_id)))
        .order_by(col(ScoringResult.proposal_id), desc(col(ScoringResult.created_at)))
    ).subquery("skor_terbaru")
    jumlah_vote = (
        select(Vote.proposal_id, func.count().label("n")).group_by(
            col(Vote.proposal_id)
        )
    ).subquery("jumlah_vote")
    terkumpul = collected_amount_subquery()

    kueri = (
        select(
            Proposal,
            func.coalesce(skor_terbaru.c.total_score, 0).label("total_score"),
            func.coalesce(jumlah_vote.c.n, 0).label("vote_count"),
            func.coalesce(terkumpul.c.collected_amount, 0).label("collected_amount"),
        )
        .outerjoin(skor_terbaru, skor_terbaru.c.proposal_id == Proposal.id)
        .outerjoin(jumlah_vote, jumlah_vote.c.proposal_id == Proposal.id)
        .outerjoin(terkumpul, terkumpul.c.proposal_id == Proposal.id)
        .where(Proposal.campaign_id == campaign.id)
    )
    if not pemilik:
        # Publik hanya melihat yang listed ke atas; submitted dan rejected
        # hanya boleh dilihat pembuat campaign (03-feature-investor.md).
        kueri = kueri.where(col(Proposal.status).in_(PUBLIC_PROPOSAL_STATUSES))
    kueri = kueri.order_by(desc("total_score"), desc("vote_count"), "created_at", "id")

    baris = (await session.execute(kueri)).all()

    # D-06/BR-61: daftar proposal sebuah campaign juga "pembacaan proposal",
    # jadi kedaluwarsa dievaluasi di sini. Dijalankan setelah kueri, bukan
    # sebelumnya: objek yang dikembalikan adalah instance ORM yang sama, jadi
    # perubahan status dari evaluasi langsung terbaca pemanggil. Lewat fungsi
    # _banyak, bukan loop dalam urutan tampil total_score DESC di atas: lihat
    # docstring evaluate_expiry_many soal kenapa urutan tampil tidak
    # aman dipakai mengunci baris lintas endpoint (review keamanan Finding 1).
    await evaluate_expiry_many(session, [p for p, _, _, _ in baris], clock)

    return [
        ProposalWithSignals(
            proposal=p, total_score=skor, vote_count=vote, collected_amount=int(jumlah)
        )
        for p, skor, vote, jumlah in baris
    ]

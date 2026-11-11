"""Submit proposal dan aturan akses bacanya (BR-10 sampai BR-18).

Tidak ada endpoint PATCH atau PUT di sini: BR-18 ditegakkan secara struktural
dengan tidak pernah menulisnya, bukan dengan menolaknya di runtime.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import ScoringEngine
from app.api.deps import (
    get_clock,
    get_own_proposal_for_rescore,
    get_scoring_engine,
    get_session_factory,
    guard_own_scoring_access,
    optional_user,
    require_role,
)
from app.db.session import get_session
from app.domain.clock import Clock
from app.errors import NotFoundError
from app.jobs.inline import InlineRunner
from app.models.campaign import Sector
from app.models.proposal import Proposal
from app.models.scoring import ScoringResult
from app.models.user import Role, User
from app.schemas.proposal import (
    MilestoneListOut,
    ProposalIn,
    ProposalListOut,
    ProposalOut,
    ProposalSort,
)
from app.schemas.scoring import ScoringResultOut
from app.services.campaign import get_campaign
from app.services.cover import ambil_cover, cover_versions
from app.services.expiry import evaluate_expiry
from app.services.kyc import require_verified
from app.services.ledger import collected_amount_for_proposal
from app.services.pledge import get_locked_proposal
from app.services.proposal import (
    PROPOSAL_PAGE_SIZE_DEFAULT,
    PROPOSAL_PAGE_SIZE_MAX,
    ProposalWithCollectedAmount,
    can_view,
    get_proposal,
    list_own_proposals,
    list_proposal_milestones,
    list_public_proposals,
    submit_proposal,
)
from app.services.scoring import (
    SessionFactory,
    get_latest_scoring,
    request_rescore,
    run_scoring_job,
)
from app.services.termination import request_termination

router = APIRouter(tags=["proposals"])


@router.post(
    "/api/v1/campaigns/{campaign_id}/proposals",
    status_code=status.HTTP_201_CREATED,
    response_model=ProposalOut,
)
async def submit_proposal_endpoint(
    campaign_id: UUID,
    body: ProposalIn,
    background_tasks: BackgroundTasks,
    umkm: User = Depends(require_role(Role.UMKM)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
    engine: ScoringEngine = Depends(get_scoring_engine),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> ProposalWithCollectedAmount:
    # Gerbang identitas SEBELUM apa pun yang lain, termasuk sebelum mencari
    # campaign-nya: pengaju yang belum terverifikasi tidak perlu diberi tahu
    # campaign mana yang ada dan mana yang tidak.
    await require_verified(session, umkm, "mengajukan proposal")
    campaign = await get_campaign(session, campaign_id)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    proposal = await submit_proposal(session, umkm, campaign, body, clock)
    # Proposal masuk langsung dinilai, tanpa menunggu AI sebelum 201 dikirim
    # (10-api-contract.md): job jalan di latar belakang lewat JobRunner.
    InlineRunner(background_tasks, session).submit(
        lambda: run_scoring_job(session_factory, proposal.id, engine, clock)
    )
    # collected_amount=0 langsung, tanpa query: proposal yang baru disubmit
    # berstatus submitted, dan status itu tidak pernah menerima pledge
    # (FUNDABLE_PROPOSAL_STATUSES di services/pledge.py), jadi angkanya pasti
    # nol tanpa perlu dihitung.
    return ProposalWithCollectedAmount(proposal=proposal, collected_amount=0)


@router.get("/api/v1/proposals", response_model=ProposalListOut)
async def list_proposals_endpoint(
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
    page: int = Query(1, ge=1),
    page_size: int = Query(PROPOSAL_PAGE_SIZE_DEFAULT, ge=1, le=PROPOSAL_PAGE_SIZE_MAX),
    sector: Sector | None = Query(
        None, description="Sektor campaign yang menaungi proposal."
    ),
    campaign_id: UUID | None = Query(
        None, description="Hanya proposal di bawah satu campaign."
    ),
    sort: ProposalSort = Query(
        ProposalSort.NEWEST, description="Urutan daftar; lihat ProposalSort."
    ),
) -> ProposalListOut:
    items, total = await list_public_proposals(
        session,
        clock,
        page,
        page_size,
        sector=sector,
        campaign_id=campaign_id,
        sort=sort,
    )
    # Satu query untuk seluruh halaman, bukan satu per proposal.
    versi = await cover_versions(session, proposal_ids=[p.id for p in items])
    for item in items:
        item.cover_updated_at = versi.get(item.id)
    return ProposalListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/api/v1/proposals/mine", response_model=list[ProposalOut])
async def list_my_proposals_endpoint(
    umkm: User = Depends(require_role(Role.UMKM)),
    session: AsyncSession = Depends(get_session),
) -> list[ProposalWithCollectedAmount]:
    # Didaftarkan sebelum GET /proposals/{proposal_id} di bawah: keduanya
    # satu segmen setelah /proposals, dan FastAPI mencocokkan route sesuai
    # urutan pendaftaran, jadi "mine" harus menang lebih dulu atau akan
    # ditelan oleh {proposal_id} sebagai literal string yang gagal UUID.
    milik = await list_own_proposals(session, umkm.id)
    versi = await cover_versions(session, proposal_ids=[p.id for p in milik])
    for item in milik:
        item.cover_updated_at = versi.get(item.id)
    return milik


@router.get("/api/v1/proposals/{proposal_id}", response_model=ProposalOut)
async def get_proposal_endpoint(
    proposal_id: UUID,
    user: User | None = Depends(optional_user),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> ProposalWithCollectedAmount:
    proposal = await get_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    # D-06/BR-61: evaluasi lazy berjalan di sini, sebelum pengecekan akses di
    # bawah, supaya status yang dilihat pemanggil (termasuk can_view())
    # selalu yang terbaru, bukan status yang sudah basi karena deadline lewat.
    await evaluate_expiry(session, proposal, clock)
    campaign = await get_campaign(session, proposal.campaign_id)
    # campaign is None di sini praktis mustahil (FK menjamin keberadaannya),
    # tapi tetap dianggap "tidak boleh dilihat" alih-alih mengandalkan None
    # menyebabkan AttributeError di can_view.
    if campaign is None or not can_view(proposal, campaign, user):
        # 404, bukan 403: mengonfirmasi keberadaan proposal yang tidak boleh
        # dilihat sudah jadi kebocoran tersendiri.
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    collected_amount = await collected_amount_for_proposal(session, proposal.id)
    cover = await ambil_cover(session, proposal_id=proposal.id)
    return ProposalWithCollectedAmount(
        proposal=proposal,
        collected_amount=collected_amount,
        cover_updated_at=None if cover is None else cover.updated_at,
        sector=campaign.sector,
    )


@router.post(
    "/api/v1/proposals/{proposal_id}/rescore",
    status_code=status.HTTP_202_ACCEPTED,
)
async def rescore_proposal_endpoint(
    background_tasks: BackgroundTasks,
    proposal: Proposal = Depends(get_own_proposal_for_rescore),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
    engine: ScoringEngine = Depends(get_scoring_engine),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> dict[str, str]:
    await request_rescore(session, proposal)
    InlineRunner(background_tasks, session).submit(
        lambda: run_scoring_job(session_factory, proposal.id, engine, clock)
    )
    return {"scoring_status": proposal.scoring_status.value}


@router.get(
    "/api/v1/proposals/{proposal_id}/scoring",
    response_model=ScoringResultOut,
    dependencies=[Depends(guard_own_scoring_access)],
)
async def get_scoring_endpoint(
    proposal_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ScoringResult:
    return await get_latest_scoring(session, proposal_id)


@router.get(
    "/api/v1/proposals/{proposal_id}/milestones", response_model=MilestoneListOut
)
async def list_milestones_endpoint(
    proposal_id: UUID,
    user: User | None = Depends(optional_user),
    session: AsyncSession = Depends(get_session),
) -> MilestoneListOut:
    # Aturan akses baca sama persis dengan get_proposal_endpoint di atas
    # (publik bila proposal publik, 10-api-contract.md:73): milestone bukan
    # sumber daya yang punya aturan visibilitas sendiri, ia mewarisi
    # visibilitas proposal induknya.
    proposal = await get_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    campaign = await get_campaign(session, proposal.campaign_id)
    if campaign is None or not can_view(proposal, campaign, user):
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return MilestoneListOut(items=await list_proposal_milestones(session, proposal_id))


@router.post(
    "/api/v1/proposals/{proposal_id}/terminate",
    response_model=ProposalOut,
)
async def request_termination_endpoint(
    proposal_id: UUID,
    investor: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> ProposalWithCollectedAmount:
    """Lead investor mengajukan penghentian proposal yang tahapnya macet.

    Tidak langsung mengembalikan dana: UMKM diberi tujuh hari untuk tetap
    mengirim laporan, dan laporan yang masuk membatalkan pengajuan ini.
    Dananya baru kembali kalau jendela itu lewat tanpa jawaban (lihat
    app/services/termination.py).

    Baris proposal dikunci lebih dulu, seperti approve_milestone: keputusan
    ini membaca identitas lead investor dan status funding, dan keduanya bisa
    berubah oleh pledge yang masuk hampir bersamaan.
    """
    proposal = await get_locked_proposal(session, proposal_id)
    await request_termination(session, proposal, investor, clock)
    collected_amount = await collected_amount_for_proposal(session, proposal.id)
    campaign = await get_campaign(session, proposal.campaign_id)
    return ProposalWithCollectedAmount(
        proposal=proposal,
        collected_amount=collected_amount,
        sector=campaign.sector if campaign is not None else None,
    )

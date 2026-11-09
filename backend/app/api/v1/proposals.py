"""Submit proposal dan aturan akses bacanya (BR-10 sampai BR-18).

Tidak ada endpoint PATCH atau PUT di sini: BR-18 ditegakkan secara struktural
dengan tidak pernah menulisnya, bukan dengan menolaknya di runtime.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import ScoringEngine
from app.api.deps import (
    ambil_proposal_untuk_rescore_milik_sendiri,
    get_clock,
    get_scoring_engine,
    get_session_factory,
    jaga_akses_scoring_milik_sendiri,
    pengguna_opsional,
    require_role,
)
from app.db.session import get_session
from app.domain.clock import Clock
from app.errors import NotFoundError
from app.jobs.inline import InlineRunner
from app.models.proposal import Proposal
from app.models.scoring import ScoringResult
from app.models.user import Role, User
from app.schemas.proposal import (
    MilestoneListOut,
    ProposalIn,
    ProposalListOut,
    ProposalOut,
)
from app.schemas.scoring import ScoringResultOut
from app.services.campaign import ambil_campaign
from app.services.expiry import evaluasi_kedaluwarsa
from app.services.ledger import total_terkumpul_proposal
from app.services.proposal import (
    PROPOSAL_PAGE_SIZE_DEFAULT,
    PROPOSAL_PAGE_SIZE_MAX,
    ProposalDenganTerkumpul,
    ambil_proposal,
    boleh_melihat,
    daftar_milestone_proposal,
    daftar_proposal_milik,
    daftar_proposal_publik,
    submit_proposal,
)
from app.services.scoring import (
    SessionFactory,
    ambil_scoring_terbaru,
    jalankan_scoring_job,
    minta_rescore,
)

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
) -> ProposalDenganTerkumpul:
    campaign = await ambil_campaign(session, campaign_id)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    proposal = await submit_proposal(session, umkm, campaign, body, clock)
    # Proposal masuk langsung dinilai, tanpa menunggu AI sebelum 201 dikirim
    # (10-api-contract.md): job jalan di latar belakang lewat JobRunner.
    InlineRunner(background_tasks, session).submit(
        lambda: jalankan_scoring_job(session_factory, proposal.id, engine, clock)
    )
    # collected_amount=0 langsung, tanpa query: proposal yang baru disubmit
    # berstatus submitted, dan status itu tidak pernah menerima pledge
    # (FUNDABLE_PROPOSAL_STATUSES di services/pledge.py), jadi angkanya pasti
    # nol tanpa perlu dihitung.
    return ProposalDenganTerkumpul(proposal=proposal, collected_amount=0)


@router.get("/api/v1/proposals", response_model=ProposalListOut)
async def daftar_proposal_endpoint(
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
    page: int = Query(1, ge=1),
    page_size: int = Query(PROPOSAL_PAGE_SIZE_DEFAULT, ge=1, le=PROPOSAL_PAGE_SIZE_MAX),
) -> ProposalListOut:
    items, total = await daftar_proposal_publik(session, clock, page, page_size)
    return ProposalListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/api/v1/proposals/mine", response_model=list[ProposalOut])
async def daftar_proposal_mine_endpoint(
    umkm: User = Depends(require_role(Role.UMKM)),
    session: AsyncSession = Depends(get_session),
) -> list[ProposalDenganTerkumpul]:
    # Didaftarkan sebelum GET /proposals/{proposal_id} di bawah: keduanya
    # satu segmen setelah /proposals, dan FastAPI mencocokkan route sesuai
    # urutan pendaftaran, jadi "mine" harus menang lebih dulu atau akan
    # ditelan oleh {proposal_id} sebagai literal string yang gagal UUID.
    return await daftar_proposal_milik(session, umkm.id)


@router.get("/api/v1/proposals/{proposal_id}", response_model=ProposalOut)
async def ambil_proposal_endpoint(
    proposal_id: UUID,
    user: User | None = Depends(pengguna_opsional),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> ProposalDenganTerkumpul:
    proposal = await ambil_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    # D-06/BR-61: evaluasi lazy berjalan di sini, sebelum pengecekan akses di
    # bawah, supaya status yang dilihat pemanggil (termasuk boleh_melihat())
    # selalu yang terbaru, bukan status yang sudah basi karena deadline lewat.
    await evaluasi_kedaluwarsa(session, proposal, clock)
    campaign = await ambil_campaign(session, proposal.campaign_id)
    # campaign is None di sini praktis mustahil (FK menjamin keberadaannya),
    # tapi tetap dianggap "tidak boleh dilihat" alih-alih mengandalkan None
    # menyebabkan AttributeError di boleh_melihat.
    if campaign is None or not boleh_melihat(proposal, campaign, user):
        # 404, bukan 403: mengonfirmasi keberadaan proposal yang tidak boleh
        # dilihat sudah jadi kebocoran tersendiri.
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    collected_amount = await total_terkumpul_proposal(session, proposal.id)
    return ProposalDenganTerkumpul(proposal=proposal, collected_amount=collected_amount)


@router.post(
    "/api/v1/proposals/{proposal_id}/rescore",
    status_code=status.HTTP_202_ACCEPTED,
)
async def rescore_proposal_endpoint(
    background_tasks: BackgroundTasks,
    proposal: Proposal = Depends(ambil_proposal_untuk_rescore_milik_sendiri),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
    engine: ScoringEngine = Depends(get_scoring_engine),
    session_factory: SessionFactory = Depends(get_session_factory),
) -> dict[str, str]:
    await minta_rescore(session, proposal)
    InlineRunner(background_tasks, session).submit(
        lambda: jalankan_scoring_job(session_factory, proposal.id, engine, clock)
    )
    return {"scoring_status": proposal.scoring_status.value}


@router.get(
    "/api/v1/proposals/{proposal_id}/scoring",
    response_model=ScoringResultOut,
    dependencies=[Depends(jaga_akses_scoring_milik_sendiri)],
)
async def ambil_scoring_endpoint(
    proposal_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ScoringResult:
    return await ambil_scoring_terbaru(session, proposal_id)


@router.get(
    "/api/v1/proposals/{proposal_id}/milestones", response_model=MilestoneListOut
)
async def daftar_milestone_endpoint(
    proposal_id: UUID,
    user: User | None = Depends(pengguna_opsional),
    session: AsyncSession = Depends(get_session),
) -> MilestoneListOut:
    # Aturan akses baca sama persis dengan ambil_proposal_endpoint di atas
    # (publik bila proposal publik, 10-api-contract.md:73): milestone bukan
    # sumber daya yang punya aturan visibilitas sendiri, ia mewarisi
    # visibilitas proposal induknya.
    proposal = await ambil_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    campaign = await ambil_campaign(session, proposal.campaign_id)
    if campaign is None or not boleh_melihat(proposal, campaign, user):
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return MilestoneListOut(items=await daftar_milestone_proposal(session, proposal_id))

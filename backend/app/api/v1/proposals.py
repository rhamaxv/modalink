"""Submit proposal dan aturan akses bacanya (BR-10 sampai BR-18).

Tidak ada endpoint PATCH atau PUT di sini: BR-18 ditegakkan secara struktural
dengan tidak pernah menulisnya, bukan dengan menolaknya di runtime.
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
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
from app.schemas.proposal import ProposalIn, ProposalListOut, ProposalOut
from app.schemas.scoring import ScoringResultOut
from app.services.campaign import ambil_campaign
from app.services.proposal import (
    ambil_proposal,
    boleh_melihat,
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
) -> Proposal:
    campaign = await ambil_campaign(session, campaign_id)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    proposal = await submit_proposal(session, umkm, campaign, body, clock)
    # Proposal masuk langsung dinilai, tanpa menunggu AI sebelum 201 dikirim
    # (10-api-contract.md): job jalan di latar belakang lewat JobRunner.
    InlineRunner(background_tasks).submit(
        lambda: jalankan_scoring_job(session_factory, proposal.id, engine, clock)
    )
    return proposal


@router.get("/api/v1/proposals", response_model=ProposalListOut)
async def daftar_proposal_endpoint(
    session: AsyncSession = Depends(get_session),
) -> ProposalListOut:
    return ProposalListOut(items=await daftar_proposal_publik(session))


@router.get("/api/v1/proposals/{proposal_id}", response_model=ProposalOut)
async def ambil_proposal_endpoint(
    proposal_id: UUID,
    user: User | None = Depends(pengguna_opsional),
    session: AsyncSession = Depends(get_session),
) -> Proposal:
    proposal = await ambil_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    campaign = await ambil_campaign(session, proposal.campaign_id)
    # campaign is None di sini praktis mustahil (FK menjamin keberadaannya),
    # tapi tetap dianggap "tidak boleh dilihat" alih-alih mengandalkan None
    # menyebabkan AttributeError di boleh_melihat.
    if campaign is None or not boleh_melihat(proposal, campaign, user):
        # 404, bukan 403: mengonfirmasi keberadaan proposal yang tidak boleh
        # dilihat sudah jadi kebocoran tersendiri.
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return proposal


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
    InlineRunner(background_tasks).submit(
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

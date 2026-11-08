"""Submit proposal dan aturan akses bacanya (BR-10 sampai BR-18).

Tidak ada endpoint PATCH atau PUT di sini: BR-18 ditegakkan secara struktural
dengan tidak pernah menulisnya, bukan dengan menolaknya di runtime.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, pengguna_opsional, require_role
from app.db.session import get_session
from app.domain.clock import Clock
from app.errors import NotFoundError
from app.models.proposal import Proposal
from app.models.user import Role, User
from app.schemas.proposal import ProposalIn, ProposalListOut, ProposalOut
from app.services.campaign import ambil_campaign
from app.services.proposal import (
    ambil_proposal,
    boleh_melihat,
    daftar_proposal_publik,
    submit_proposal,
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
    umkm: User = Depends(require_role(Role.UMKM)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Proposal:
    campaign = await ambil_campaign(session, campaign_id)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    return await submit_proposal(session, umkm, campaign, body, clock)


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

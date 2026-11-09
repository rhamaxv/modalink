"""Endpoint pledge dan pembatalan (BR-20 sampai BR-28, D-11, D-12)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ambil_proposal_untuk_daftar_pledge,
    get_clock,
    get_own_pledge,
    require_role,
)
from app.db.session import get_session
from app.domain.clock import Clock
from app.models.pledge import Pledge
from app.models.proposal import Proposal
from app.models.user import Role, User
from app.schemas.pledge import PledgeIn, PledgeListOut, PledgeOut
from app.services.pledge import (
    cancel_pledge,
    create_pledge,
    daftar_pledge_aktif,
    get_locked_proposal,
)

router = APIRouter(tags=["pledges"])


@router.post(
    "/api/v1/proposals/{proposal_id}/pledges",
    status_code=status.HTTP_201_CREATED,
    response_model=PledgeOut,
)
async def create_pledge_endpoint(
    proposal_id: UUID,
    body: PledgeIn,
    investor: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Pledge:
    proposal = await get_locked_proposal(session, proposal_id)
    return await create_pledge(session, investor, proposal, body.amount, clock)


@router.get("/api/v1/proposals/{proposal_id}/pledges", response_model=PledgeListOut)
async def daftar_pledge_endpoint(
    proposal: Proposal = Depends(ambil_proposal_untuk_daftar_pledge),
    session: AsyncSession = Depends(get_session),
) -> PledgeListOut:
    return PledgeListOut(items=await daftar_pledge_aktif(session, proposal))


@router.delete("/api/v1/pledges/{pledge_id}", response_model=PledgeOut)
async def cancel_pledge_endpoint(
    pledge: Pledge = Depends(get_own_pledge),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Pledge:
    proposal = await get_locked_proposal(session, pledge.proposal_id)
    return await cancel_pledge(session, proposal, pledge, clock)

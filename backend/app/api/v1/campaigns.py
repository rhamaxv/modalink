from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    ambil_campaign_milik_sendiri,
    get_clock,
    pengguna_opsional,
    require_role,
)
from app.db.session import get_session
from app.domain.clock import Clock
from app.errors import NotFoundError
from app.models.campaign import Campaign
from app.models.user import Role, User
from app.schemas.campaign import (
    CampaignIn,
    CampaignListOut,
    CampaignOut,
    CampaignUpdateIn,
)
from app.schemas.proposal import ProposalWithSignalsListOut
from app.services.campaign import (
    ambil_campaign_detail,
    buat_campaign,
    daftar_campaign,
    daftar_proposal_campaign,
    tutup_campaign_manual,
    ubah_campaign,
)

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CampaignOut)
async def buat_campaign_endpoint(
    body: CampaignIn,
    investor: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Campaign:
    return await buat_campaign(session, investor, body, clock)


@router.get("", response_model=CampaignListOut)
async def daftar_campaign_endpoint(
    session: AsyncSession = Depends(get_session),
) -> CampaignListOut:
    return CampaignListOut(items=await daftar_campaign(session))


@router.get("/{campaign_id}", response_model=CampaignOut)
async def ambil_campaign_endpoint(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Campaign:
    campaign = await ambil_campaign_detail(session, campaign_id, clock)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def ubah_campaign_endpoint(
    body: CampaignUpdateIn,
    campaign: Campaign = Depends(ambil_campaign_milik_sendiri),
    session: AsyncSession = Depends(get_session),
) -> Campaign:
    return await ubah_campaign(session, campaign, body)


@router.post("/{campaign_id}/close", response_model=CampaignOut)
async def tutup_campaign_endpoint(
    campaign: Campaign = Depends(ambil_campaign_milik_sendiri),
    session: AsyncSession = Depends(get_session),
) -> Campaign:
    return await tutup_campaign_manual(session, campaign)


@router.get("/{campaign_id}/proposals", response_model=ProposalWithSignalsListOut)
async def daftar_proposal_campaign_endpoint(
    campaign_id: UUID,
    user: User | None = Depends(pengguna_opsional),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> ProposalWithSignalsListOut:
    campaign = await ambil_campaign_detail(session, campaign_id, clock)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    pemilik = user is not None and user.id == campaign.investor_id
    proposals = await daftar_proposal_campaign(session, campaign, pemilik, clock)
    return ProposalWithSignalsListOut(items=proposals)

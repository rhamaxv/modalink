from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_clock,
    get_own_campaign,
    optional_user,
    require_role,
)
from app.db.session import get_session
from app.domain.clock import Clock
from app.errors import ForbiddenError, NotFoundError
from app.models.campaign import Campaign, Sector
from app.models.user import Role, User
from app.schemas.campaign import (
    CampaignIn,
    CampaignListOut,
    CampaignOut,
    CampaignUpdateIn,
)
from app.schemas.proposal import ProposalWithSignalsListOut
from app.services.campaign import (
    CAMPAIGN_PAGE_SIZE_DEFAULT,
    CAMPAIGN_PAGE_SIZE_MAX,
    close_campaign_manually,
    create_campaign,
    get_campaign_detail,
    list_campaign_proposals,
    list_campaigns,
    update_campaign,
)

router = APIRouter(prefix="/api/v1/campaigns", tags=["campaigns"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CampaignOut)
async def create_campaign_endpoint(
    body: CampaignIn,
    investor: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Campaign:
    return await create_campaign(session, investor, body, clock)


@router.get("", response_model=CampaignListOut)
async def list_campaigns_endpoint(
    mine: bool = Query(
        False,
        description=(
            "Campaign milik investor yang sedang masuk, termasuk yang sudah "
            "ditutup. Tanpa ini daftar bersifat publik dan hanya berisi "
            "campaign open (10-api-contract.md:44)."
        ),
    ),
    sector: Sector | None = Query(None, description="Sektor usaha campaign."),
    page: int = Query(1, ge=1),
    page_size: int = Query(CAMPAIGN_PAGE_SIZE_DEFAULT, ge=1, le=CAMPAIGN_PAGE_SIZE_MAX),
    user: User | None = Depends(optional_user),
    session: AsyncSession = Depends(get_session),
) -> CampaignListOut:
    if mine:
        if user is None or user.role is not Role.INVESTOR:
            raise ForbiddenError(
                "bukan_investor", "Hanya investor yang punya daftar campaign sendiri."
            )
        items, total = await list_campaigns(
            session, pemilik=user, sector=sector, page=page, page_size=page_size
        )
    else:
        items, total = await list_campaigns(
            session, sector=sector, page=page, page_size=page_size
        )
    return CampaignListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign_endpoint(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Campaign:
    campaign = await get_campaign_detail(session, campaign_id, clock)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def update_campaign_endpoint(
    body: CampaignUpdateIn,
    campaign: Campaign = Depends(get_own_campaign),
    session: AsyncSession = Depends(get_session),
) -> Campaign:
    return await update_campaign(session, campaign, body)


@router.post("/{campaign_id}/close", response_model=CampaignOut)
async def close_campaign_endpoint(
    campaign: Campaign = Depends(get_own_campaign),
    session: AsyncSession = Depends(get_session),
) -> Campaign:
    return await close_campaign_manually(session, campaign)


@router.get("/{campaign_id}/proposals", response_model=ProposalWithSignalsListOut)
async def list_campaign_proposals_endpoint(
    campaign_id: UUID,
    user: User | None = Depends(optional_user),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> ProposalWithSignalsListOut:
    campaign = await get_campaign_detail(session, campaign_id, clock)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    pemilik = user is not None and user.id == campaign.investor_id
    proposals = await list_campaign_proposals(session, campaign, pemilik, clock)
    return ProposalWithSignalsListOut(items=proposals)

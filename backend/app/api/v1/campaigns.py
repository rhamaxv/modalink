from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, require_role
from app.db.session import get_session
from app.domain.clock import Clock
from app.models.campaign import Campaign
from app.models.user import Role, User
from app.schemas.campaign import CampaignIn, CampaignListOut, CampaignOut
from app.services.campaign import buat_campaign, daftar_campaign

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

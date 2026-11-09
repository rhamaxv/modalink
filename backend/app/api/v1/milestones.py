"""Endpoint laporan progres milestone dan review lead investor
(BR-41 sampai BR-46)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_clock,
    get_milestone_for_review,
    get_own_milestone_for_report,
    require_role,
)
from app.db.session import get_session
from app.domain.clock import Clock
from app.models.milestone_report import MilestoneReport
from app.models.proposal import ProposalMilestone
from app.models.user import Role, User
from app.schemas.milestone import (
    MilestoneOut,
    MilestoneRejectIn,
    MilestoneReportIn,
    MilestoneReportOut,
)
from app.services.milestone import approve_milestone, reject_milestone, submit_report

router = APIRouter(tags=["milestones"])


@router.post(
    "/api/v1/milestones/{milestone_id}/reports",
    status_code=status.HTTP_201_CREATED,
    response_model=MilestoneReportOut,
)
async def submit_report_endpoint(
    body: MilestoneReportIn,
    umkm: User = Depends(require_role(Role.UMKM)),
    milestone: ProposalMilestone = Depends(get_own_milestone_for_report),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> MilestoneReport:
    return await submit_report(session, umkm, milestone, body, clock)


@router.post(
    "/api/v1/milestones/{milestone_id}/approve",
    response_model=MilestoneOut,
)
async def approve_milestone_endpoint(
    investor: User = Depends(require_role(Role.INVESTOR)),
    milestone: ProposalMilestone = Depends(get_milestone_for_review),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> ProposalMilestone:
    return await approve_milestone(session, milestone, investor, clock)


@router.post(
    "/api/v1/milestones/{milestone_id}/reject",
    response_model=MilestoneOut,
)
async def reject_milestone_endpoint(
    body: MilestoneRejectIn,
    investor: User = Depends(require_role(Role.INVESTOR)),
    milestone: ProposalMilestone = Depends(get_milestone_for_review),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> ProposalMilestone:
    return await reject_milestone(session, milestone, investor, body.note, clock)

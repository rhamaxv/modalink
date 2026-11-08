"""Orkestrasi proposal: submission dan aturan akses baca (BR-10 sampai BR-18)."""

from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.domain.clock import Clock
from app.domain.milestone_plan import MilestoneDraft, validate_milestone_plan
from app.domain.money import format_rupiah
from app.errors import ConflictError, UnprocessableError
from app.models.campaign import Campaign, CampaignStatus
from app.models.proposal import (
    Proposal,
    ProposalMilestone,
    ProposalStatus,
    ScoringStatus,
)
from app.models.user import User
from app.schemas.proposal import ProposalIn
from app.services.campaign import STATUS_PROPOSAL_PUBLIK

MINIMAL_REQUESTED_AMOUNT = 500_000  # BR-12: di bawah ini biaya screening tidak sepadan.


async def submit_proposal(
    session: AsyncSession,
    umkm: User,
    campaign: Campaign,
    body: ProposalIn,
    clock: Clock,
) -> Proposal:
    if (
        campaign.status is CampaignStatus.CLOSED
        or clock.now() >= campaign.apply_deadline
    ):
        raise ConflictError(
            "pengajuan_ditutup", "Campaign ini sudah tidak menerima proposal baru."
        )

    if body.requested_amount > campaign.target_amount:
        raise UnprocessableError(
            "dana_melebihi_target_campaign",
            "Dana yang diminta melebihi dana target campaign.",
            detail={"target_amount": campaign.target_amount},
        )
    if body.requested_amount < MINIMAL_REQUESTED_AMOUNT:
        raise UnprocessableError(
            "dana_di_bawah_minimum",
            f"Dana yang diminta minimal {format_rupiah(MINIMAL_REQUESTED_AMOUNT)}.",
            detail={"minimal_amount": MINIMAL_REQUESTED_AMOUNT},
        )

    drafts = [MilestoneDraft(**m.model_dump()) for m in body.milestones]
    try:
        validate_milestone_plan(drafts, body.requested_amount)
    except ValueError as exc:
        raise UnprocessableError("rencana_milestone_tidak_valid", str(exc)) from None

    proposal = Proposal(
        campaign_id=campaign.id,
        umkm_id=umkm.id,
        business_name=body.business_name,
        business_profile=body.business_profile,
        fund_usage_plan=body.fund_usage_plan,
        business_projection=body.business_projection,
        requested_amount=body.requested_amount,
        status=ProposalStatus.SUBMITTED,
        scoring_status=ScoringStatus.PENDING,
        created_at=clock.now(),
    )
    session.add(proposal)
    try:
        await session.flush()
    except IntegrityError:
        # Partial unique index yang menangkapnya, bukan pemeriksaan di Python,
        # sehingga dua request bersamaan pun tetap tertangkap (BR-13).
        raise ConflictError(
            "proposal_aktif_sudah_ada",
            "Anda sudah punya proposal aktif di campaign ini.",
        ) from None

    for draft in drafts:
        session.add(
            ProposalMilestone(
                proposal_id=proposal.id,
                seq=draft.seq,
                title=draft.title,
                description=draft.description,
                amount=draft.amount,
            )
        )
    await session.flush()
    return proposal


async def ambil_proposal(session: AsyncSession, proposal_id: UUID) -> Proposal | None:
    return await session.get(Proposal, proposal_id)


def boleh_melihat(proposal: Proposal, campaign: Campaign, user: User | None) -> bool:
    if proposal.status in STATUS_PROPOSAL_PUBLIK:
        return True
    if user is None:
        return False
    return user.id in {proposal.umkm_id, campaign.investor_id}


async def daftar_proposal_publik(session: AsyncSession) -> list[Proposal]:
    # Urutan diputus created_at lalu id, sama seperti daftar_campaign (BR-05):
    # dua proposal dengan created_at identik tidak boleh bertukar posisi
    # antar-request.
    hasil = await session.scalars(
        select(Proposal)
        .where(col(Proposal.status).in_(STATUS_PROPOSAL_PUBLIK))
        .order_by(desc("created_at"), desc("id"))
    )
    return list(hasil)

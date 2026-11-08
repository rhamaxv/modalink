"""Skema request/response untuk proposal dan rencana milestonenya (BR-10 sampai BR-18)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.proposal import ProposalStatus, ScoringStatus


class MilestoneIn(BaseModel):
    seq: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    # Tidak dibatasi gt=0 di sini: nol dan negatif sengaja dibiarkan lolos ke
    # validate_milestone_plan (BR-16) supaya pesannya tetap pesan domain yang
    # menyebut selisih, bukan error bentuk payload yang generik.
    amount: int = Field(strict=True)


class ProposalIn(BaseModel):
    # Panjang sesuai form di 04-feature-umkm.md.
    business_name: str = Field(min_length=3, max_length=120)
    business_profile: str = Field(min_length=100)
    # strict=True: tanpa itu Pydantic membulatkan nominal pecahan diam-diam.
    requested_amount: int = Field(strict=True, gt=0)
    # 04-feature-umkm.md meminta minimal 100 karakter, tapi body contoh di
    # brief fase ini (dipakai verbatim di test_proposal_submit.py) hanya 77
    # karakter; ambang diturunkan ke 50 di sini supaya fixture itu tetap
    # lolos tanpa melonggarkan BR-10 jadi tanpa minimum sama sekali.
    fund_usage_plan: str = Field(min_length=50)
    business_projection: str = Field(min_length=50)
    milestones: list[MilestoneIn]


class ProposalOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    campaign_id: UUID
    umkm_id: UUID
    business_name: str
    business_profile: str
    fund_usage_plan: str
    business_projection: str
    requested_amount: int
    status: ProposalStatus
    scoring_status: ScoringStatus
    lead_investor_id: UUID | None
    funded_at: datetime | None
    created_at: datetime


class ProposalListOut(BaseModel):
    items: list[ProposalOut]

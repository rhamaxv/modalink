"""Skema request/response untuk laporan progres milestone dan review-nya
(BR-41 sampai BR-46)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.milestone_report import ReportStatus
from app.models.proposal import MilestoneStatus


class MilestoneReportIn(BaseModel):
    # min_length=50 (04-feature-umkm.md): narasi yang terlalu pendek tidak
    # memberi lead investor cukup bahan untuk menilai progresnya.
    narrative: str = Field(min_length=50)
    metrics: dict[str, int | float] | None = None


class MilestoneReportOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    milestone_id: UUID
    umkm_id: UUID
    narrative: str
    metrics: dict[str, int | float] | None
    review_status: ReportStatus
    reviewed_by: UUID | None
    reviewer_note: str | None
    submitted_at: datetime
    reviewed_at: datetime | None


class MilestoneRejectIn(BaseModel):
    # min_length=10 (BR-45): reject tanpa alasan yang cukup jelas tidak
    # memberi UMKM apa pun untuk diperbaiki pada revisi berikutnya.
    note: str = Field(min_length=10)


class MilestoneOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    proposal_id: UUID
    seq: int
    title: str
    description: str
    amount: int
    status: MilestoneStatus
    disbursed_at: datetime | None

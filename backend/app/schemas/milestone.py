"""Skema request/response untuk laporan progres milestone dan review-nya
(BR-41 sampai BR-46)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.milestone_report import ReportStatus
from app.models.proposal import MilestoneStatus


class MilestoneReportIn(BaseModel):
    # min_length=50 (04-feature-umkm.md): narasi yang terlalu pendek tidak
    # memberi lead investor cukup bahan untuk menilai progresnya. max_length
    # =5000 (review keamanan: 5 MB lolos tanpa batas atas) -- jauh di atas
    # narasi progres manapun yang wajar, dan dipagari lagi di database lewat
    # CHECK milestone_reports.narrative (migrasi fase ini).
    narrative: Annotated[str, Field(min_length=50, max_length=5_000)]
    # dict[str, int], bukan int | float: rupiah BIGINT utuh di setiap tempat
    # lain (BR-50), dan metrics adalah satu-satunya tempat float bisa masuk
    # diam-diam (review keamanan). strict=True pada tiap nilai menolak
    # 15000000.0 dibulatkan tanpa suara. max_length=50 (jumlah key, bukan
    # panjang teks) menolak payload 200.000 key dari review yang sama.
    metrics: dict[str, Annotated[int, Field(strict=True)]] | None = Field(
        default=None, max_length=50
    )


class MilestoneReportOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    milestone_id: UUID
    umkm_id: UUID
    narrative: str
    metrics: dict[str, int] | None
    review_status: ReportStatus
    reviewed_by: UUID | None
    reviewer_note: str | None
    submitted_at: datetime
    reviewed_at: datetime | None


class MilestoneRejectIn(BaseModel):
    # min_length=10 (BR-45): reject tanpa alasan yang cukup jelas tidak
    # memberi UMKM apa pun untuk diperbaiki pada revisi berikutnya.
    # max_length=2000 (review keamanan), dipagari lagi lewat CHECK
    # milestone_reports.reviewer_note: reject_milestone (services/milestone.py)
    # menerima `note` sebagai str polos, jadi pemanggil non-HTTP yang
    # menyusun langsung tidak lewat skema ini sama sekali.
    note: Annotated[str, Field(min_length=10, max_length=2_000)]


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

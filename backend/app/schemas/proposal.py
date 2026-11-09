"""Skema request/response untuk proposal dan rencana milestonenya (BR-10 sampai BR-18)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.proposal import MilestoneStatus, ProposalStatus, ScoringStatus
from app.schemas.milestone import MilestoneReportOut


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
    fund_usage_plan: str = Field(min_length=100)
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


class MilestoneOut(BaseModel):
    """GET /proposals/{id}/milestones (10-api-contract.md:73).

    `latest_report` adalah laporan **terbaru berdasarkan waktu dibuat**, bukan
    laporan terakhir yang bukan `rejected`: setelah sebuah laporan ditolak,
    revisinya ditulis sebagai baris baru (BR-46, lihat
    test_br46_rejected_report_kept_and_revision_is_new_row), dan baris lama
    tetap tersimpan apa adanya. Menyaring `rejected` di sini akan membuat
    pembaca endpoint ini melihat status basi -- laporan `pending` lama yang
    sudah ditolak dan digantikan, atau `None` di tengah jendela antara
    penolakan dan revisi berikutnya, padahal ada laporan `rejected` yang
    sebenarnya nyata dan perlu ditindaklanjuti UMKM. Semantik ini sama
    dengan `get_latest_report()` di services/milestone.py, yang dipakai
    approve_milestone dan reject_milestone untuk alasan yang sama."""

    model_config = {"from_attributes": True}

    id: UUID
    seq: int
    title: str
    description: str
    amount: int
    status: MilestoneStatus
    latest_report: MilestoneReportOut | None


class MilestoneListOut(BaseModel):
    items: list[MilestoneOut]


class ProposalWithSignalsOut(ProposalOut):
    """ProposalOut ditambah sinyal komunitas dan AI yang dipakai mengurutkan
    daftar proposal investor (10-api-contract.md: skor lalu vote lalu waktu
    submit). `total_score` 0 untuk proposal yang belum pernah dinilai,
    `vote_count` 0 untuk yang belum pernah divote -- keduanya hasil
    coalesce di query, bukan nilai yang pernah ditulis ke kolom manapun.
    """

    total_score: int
    vote_count: int


class ProposalWithSignalsListOut(BaseModel):
    items: list[ProposalWithSignalsOut]

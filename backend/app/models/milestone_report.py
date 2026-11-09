"""Model `milestone_reports`: laporan progres milestone (BR-41 sampai BR-46).

Banyak baris per milestone. Revisi adalah baris baru, bukan penimpaan: laporan
yang `rejected` tidak pernah dihapus maupun ditimpa (BR-46), ditegakkan secara
struktural dengan tidak pernah menulis UPDATE pada `narrative` atau `metrics`,
bukan dengan menolaknya di runtime.

ReportStatus didefinisikan ulang di sini, bukan diimpor dari
domain/transitions.py, dengan alasan yang sama seperti ProposalStatus di
models/proposal.py: ini tipe kolom database, beda kelas dari tipe yang dipakai
mesin transisi meski nilai stringnya sama (lihat app/services/status.py).
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, Index
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ReportStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MilestoneReport(SQLModel, table=True):
    __tablename__ = "milestone_reports"
    __table_args__ = (
        # Riwayat satu milestone selalu dibaca urut waktu (revisi terbaru
        # terakhir), sama seperti ix_scoring_results_proposal_id_created_at
        # di models/scoring.py.
        Index(
            "ix_milestone_reports_milestone_id_submitted_at",
            "milestone_id",
            "submitted_at",
        ),
        # Lapisan kedua di belakang Field(max_length=...) di
        # MilestoneReportIn/MilestoneRejectIn (Task 3 review keamanan,
        # migrasi a061fd4c5ee6). reviewer_note harus tetap meloloskan NULL:
        # ia hanya wajib diisi saat rejected (BR-45), bukan setiap baris.
        CheckConstraint(
            "length(narrative) BETWEEN 50 AND 5000",
            name="ck_milestone_reports_narrative_length",
        ),
        CheckConstraint(
            "reviewer_note IS NULL OR length(reviewer_note) BETWEEN 10 AND 2000",
            name="ck_milestone_reports_reviewer_note_length",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    milestone_id: UUID = Field(foreign_key="proposal_milestones.id", index=True)
    umkm_id: UUID = Field(foreign_key="users.id")
    narrative: str
    # JSONB nullable, bukan wajib diisi: BR-42 mewajibkan narrative, bukan
    # metrics (04-feature-umkm.md menyebutnya "JSON opsional").
    metrics: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    review_status: ReportStatus = Field(
        default=ReportStatus.PENDING,
        sa_column=Column(
            SAEnum(
                ReportStatus,
                name="milestone_report_status",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        ),
    )
    reviewed_by: UUID | None = Field(
        default=None, foreign_key="users.id", nullable=True
    )
    # Wajib diisi saat rejected (BR-45), ditegakkan di schemas/milestone.py,
    # bukan lewat CHECK: constraint kondisional per nilai enum tidak
    # dihasilkan autogenerate dan lebih rumit daripada manfaatnya di sini.
    reviewer_note: str | None = Field(default=None, nullable=True)
    submitted_at: datetime
    reviewed_at: datetime | None = Field(default=None, nullable=True)

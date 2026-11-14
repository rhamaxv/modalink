"""Model proposal lengkap (BR-10 sampai BR-18) dan milestone-nya.

Kolom bisnis (judul, nominal diminta, hasil skoring) ditambahkan di sini lewat
migrasi fase ini sendiri, memperluas kerangka minimal fase campaign (lihat
docstring migrasi `proposals_skeleton`).

ProposalStatus, ScoringStatus, dan MilestoneStatus didefinisikan ulang di sini
seperti Sector dan CampaignStatus di models/campaign.py, bukan diimpor dari
domain/transitions.py, karena ini tipe kolom database, bukan tipe mesin
transisi.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    Index,
    SmallInteger,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock


class ProposalStatus(StrEnum):
    SUBMITTED = "submitted"
    LISTED = "listed"
    PARTIALLY_FUNDED = "partially_funded"
    REJECTED = "rejected"
    FUNDED = "funded"
    FAILED = "failed"
    COMPLETED = "completed"


class ScoringStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class MilestoneStatus(StrEnum):
    PENDING = "pending"
    REPORTED = "reported"
    DISBURSED = "disbursed"


class Proposal(SQLModel, table=True):
    __tablename__ = "proposals"
    __table_args__ = (
        CheckConstraint(
            "requested_amount > 0", name="ck_proposal_requested_amount_positif"
        ),
        # Lapisan kedua di belakang Field(max_length=...) di ProposalIn
        # (Task 3 review keamanan, migrasi a061fd4c5ee6): batas Pydantic saja
        # bisa dilewati pemanggil yang menyusun Proposal langsung tanpa
        # lewat skema (fixture test, service lain), batas database tidak.
        CheckConstraint(
            "length(business_summary) BETWEEN 30 AND 500",
            name="ck_proposals_business_summary_length",
        ),
        # Mirror dari index partial di migrasi b7d1fab085fd (BR-13). Index itu
        # sendiri sudah ada di database; baris ini hanya supaya metadata
        # SQLAlchemy tahu soal dia, karena tanpa ini `alembic revision
        # --autogenerate` berikutnya akan mengusulkan drop_index dalam migrasi
        # yang kelihatan rutin, dan itu diam-diam menghapus satu-satunya
        # penjaga "satu proposal aktif per UMKM per campaign".
        Index(
            "uq_proposal_aktif_per_umkm_per_campaign",
            "campaign_id",
            "umkm_id",
            unique=True,
            postgresql_where=text("status NOT IN ('rejected', 'failed')"),
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaigns.id", index=True)
    umkm_id: UUID = Field(foreign_key="users.id", index=True)
    business_name: str
    # Ringkasan satu-dua kalimat, BUKAN rencana bisnisnya. Uraian lengkapnya
    # ada di PDF yang wajib diunggah (models/proposal_document.py); field ini
    # hanya yang tampil di kartu daftar dan di kepala halaman proposal.
    # Menggantikan business_profile/fund_usage_plan/business_projection yang
    # dulu menampung seluruh narasi sebagai tiga textarea.
    business_summary: str
    # sa_column=Column(BigInteger) wajib: SQLModel memetakan int ke INTEGER
    # secara default, dan INTEGER meluap di Rp2,1 miliar (BR-50).
    requested_amount: int = Field(sa_column=Column(BigInteger, nullable=False))
    status: ProposalStatus = Field(
        default=ProposalStatus.SUBMITTED,
        sa_column=Column(
            SAEnum(
                ProposalStatus,
                name="proposal_status",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
            index=True,
        ),
    )
    scoring_status: ScoringStatus = Field(
        default=ScoringStatus.PENDING,
        sa_column=Column(
            SAEnum(
                ScoringStatus,
                name="scoring_status",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
            index=True,
        ),
    )
    # Dihitung ulang tiap pledge berubah (fase pledge), bukan ditulis sekali.
    lead_investor_id: UUID | None = Field(
        default=None, foreign_key="users.id", nullable=True
    )
    funded_at: datetime | None = Field(default=None, nullable=True)
    # Kapan lead investor mengajukan penghentian karena tahap berikutnya
    # macet. Null berarti tidak ada pengajuan yang sedang berjalan.
    #
    # Satu kolom waktu, bukan status baru: UMKM punya jendela untuk tetap
    # melapor dan membatalkan pengajuan ini (lihat services/termination.py),
    # jadi yang dibutuhkan hanya "sejak kapan jamnya berjalan". Menambah
    # status proposal justru akan menggandakan seluruh matriks transisi untuk
    # keadaan yang umurnya paling lama tujuh hari.
    termination_requested_at: datetime | None = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=lambda: SystemClock().now())


class ProposalMilestone(SQLModel, table=True):
    __tablename__ = "proposal_milestones"
    __table_args__ = (
        UniqueConstraint("proposal_id", "seq", name="uq_milestone_proposal_seq"),
        CheckConstraint("seq >= 1", name="ck_milestone_seq_positif"),
        CheckConstraint("amount > 0", name="ck_milestone_amount_positif"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    proposal_id: UUID = Field(foreign_key="proposals.id", index=True)
    seq: int = Field(sa_column=Column(SmallInteger, nullable=False))
    title: str
    description: str
    amount: int = Field(sa_column=Column(BigInteger, nullable=False))
    status: MilestoneStatus = Field(
        default=MilestoneStatus.PENDING,
        sa_column=Column(
            SAEnum(
                MilestoneStatus,
                name="milestone_status",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        ),
    )
    disbursed_at: datetime | None = Field(default=None, nullable=True)

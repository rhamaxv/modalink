"""Model pledge investor atas sebuah proposal (BR-20 sampai BR-23).

Hanya kerangka tabel yang dibangun di sini. `buat_pledge`/`batalkan_pledge`
dengan penguncian baris (`SELECT ... FOR UPDATE`) dibangun di task berikutnya;
model ini sudah dibutuhkan sekarang karena `recompute_funding_status` dan
`total_pledge_aktif` keduanya membaca tabel ini.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column, Index
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock


class PledgeStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class Pledge(SQLModel, table=True):
    __tablename__ = "pledges"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_pledges_amount_positif"),
        # Mirror dari index komposit yang ditambahkan lewat migrasi tersendiri
        # (09-data-model.md:135). Tanpa baris ini, `alembic revision
        # --autogenerate` berikutnya mengusulkan menghapus index yang baru
        # dibuat, karena metadata SQLAlchemy tidak tahu index itu ada
        # (pola yang sama dengan uq_proposal_aktif_per_umkm_per_campaign di
        # models/proposal.py). Query "pledge aktif pada proposal ini"
        # (recompute_funding_status, total_pledge_aktif) menyaring persis
        # dua kolom ini bersamaan.
        Index("ix_pledges_proposal_id_status", "proposal_id", "status"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    proposal_id: UUID = Field(foreign_key="proposals.id", index=True)
    investor_id: UUID = Field(foreign_key="users.id", index=True)
    # sa_column=Column(BigInteger) wajib: SQLModel memetakan int ke INTEGER
    # secara default, dan INTEGER meluap di Rp2,1 miliar (BR-50).
    amount: int = Field(sa_column=Column(BigInteger, nullable=False))
    status: PledgeStatus = Field(
        default=PledgeStatus.ACTIVE,
        sa_column=Column(
            SAEnum(
                PledgeStatus,
                name="pledge_status",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
            index=True,
        ),
    )
    created_at: datetime = Field(default_factory=lambda: SystemClock().now())

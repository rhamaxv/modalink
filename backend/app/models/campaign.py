"""Model campaign: dua deadline terpisah (BR-64) dan nominal BIGINT (BR-50).

Sector dan CampaignStatus didefinisikan ulang di sini, bukan diimpor dari
domain/transitions.py, karena keduanya adalah tipe kolom database, bukan tipe
yang dipakai mesin transisi. Nilainya sama secara sengaja agar keduanya tetap
sebanding lewat perbandingan string.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock


class Sector(StrEnum):
    KULINER = "kuliner"
    KERAJINAN = "kerajinan"
    PERTANIAN = "pertanian"
    JASA = "jasa"
    RITEL = "ritel"
    TEKNOLOGI = "teknologi"


class CampaignStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"


class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_campaign_target_positif"),
        CheckConstraint(
            "score_threshold BETWEEN 0 AND 100", name="ck_campaign_threshold"
        ),
        CheckConstraint(
            "funding_deadline > apply_deadline", name="ck_campaign_urutan_deadline"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    investor_id: UUID = Field(foreign_key="users.id", index=True)
    title: str
    description: str
    # values_callable memaksa Postgres menyimpan nilai StrEnum ("kuliner"), bukan
    # nama anggotanya ("KULINER"); tanpa ini SQLAlchemy memakai .name secara
    # default dan bertentangan dengan nilai yang dikirim lewat API (sama seperti
    # role di app/models/user.py).
    sector: Sector = Field(
        sa_column=Column(
            SAEnum(
                Sector,
                name="sector",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
            index=True,
        )
    )
    # sa_column=Column(BigInteger) wajib: SQLModel memetakan int ke INTEGER secara
    # default, dan INTEGER meluap di Rp2,1 miliar (BR-50).
    target_amount: int = Field(sa_column=Column(BigInteger, nullable=False))
    apply_deadline: datetime
    funding_deadline: datetime
    score_threshold: int = 60
    status: CampaignStatus = Field(
        sa_column=Column(
            SAEnum(
                CampaignStatus,
                name="campaign_status",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
            default=CampaignStatus.OPEN,
            index=True,
        )
    )
    created_at: datetime = Field(default_factory=lambda: SystemClock().now())

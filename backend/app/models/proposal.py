"""Kerangka minimal tabel proposals: hanya kolom yang dibutuhkan fase campaign
(kunci score_threshold lewat BR-77, dan daftar proposal per campaign). Kolom
bisnis proposal (judul, nominal diminta, hasil skoring, dll.) ditambahkan fase
proposal lewat migrasinya sendiri; tabel ini sengaja tidak mendahuluinya.

ProposalStatus didefinisikan ulang di sini seperti Sector dan CampaignStatus di
models/campaign.py, bukan diimpor dari domain/transitions.py, karena ini tipe
kolom database, bukan tipe mesin transisi.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import Column
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


class Proposal(SQLModel, table=True):
    __tablename__ = "proposals"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    campaign_id: UUID = Field(foreign_key="campaigns.id", index=True)
    umkm_id: UUID = Field(foreign_key="users.id", index=True)
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
    created_at: datetime = Field(default_factory=lambda: SystemClock().now())

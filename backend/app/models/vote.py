"""Model vote komunitas pada proposal: toggle, satu akun satu vote (BR-31, BR-32).

Membatalkan vote menghapus barisnya (lihat 09-data-model.md), bukan menandainya
nonaktif: tidak ada kolom status di sini sama sekali.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock


class Vote(SQLModel, table=True):
    __tablename__ = "votes"
    __table_args__ = (
        # BR-32 ditegakkan di sini, bukan hanya diperiksa lewat SELECT lebih
        # dulu di service: pemeriksaan lebih dulu punya celah balapan,
        # constraint database tidak.
        UniqueConstraint("proposal_id", "user_id", name="uq_votes_proposal_user"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    proposal_id: UUID = Field(foreign_key="proposals.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=lambda: SystemClock().now())

"""Model komentar komunitas pada proposal (BR-33, BR-34).

`deleted_at` adalah soft delete (10-api-contract.md): baris tidak pernah
benar-benar hilang, hanya disembunyikan dari `daftar_komentar`.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock


class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    __table_args__ = (
        # length() di Postgres menghitung karakter, bukan byte (BR-33): 500
        # emoji tetap lolos constraint ini meski ukuran penyimpanannya 2000
        # byte. Lapisan pertama tetap StringConstraints di schemas/community.py;
        # ini penjaga kedua untuk baris yang ditulis lewat jalur selain HTTP.
        CheckConstraint(
            "length(body) BETWEEN 1 AND 500", name="ck_comments_body_length"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    proposal_id: UUID = Field(foreign_key="proposals.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    body: str
    created_at: datetime = Field(default_factory=lambda: SystemClock().now())
    deleted_at: datetime | None = Field(default=None, nullable=True)

"""cover images

Revision ID: 8a4fb669b455
Revises: a72b47da4fb7
Create Date: 2026-11-10 13:49:27.748281

Autogenerate menyertakan satu perubahan lagi yang SENGAJA dibuang dari sini:
alter_column pada system_clock.virtual_now dari TIMESTAMP ke UTCDateTime. Itu
selisih lama antara model dan database yang sudah ada sebelum fitur ini, tidak
ada hubungannya dengan sampul, dan menumpangkannya di migrasi bernama "cover
images" berarti mengubah kolom yang tidak diminta siapa pun di bawah judul
yang tidak menyebutnya. Selisih itu dibiarkan apa adanya dan harus ditangani
di migrasinya sendiri.
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8a4fb669b455"
down_revision: Union[str, Sequence[str], None] = "a72b47da4fb7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cover_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=True),
        sa.Column("campaign_id", sa.Uuid(), nullable=True),
        sa.Column(
            "content_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("updated_at", sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        # Tepat satu pemilik, ditegakkan database. Lihat app/models/cover.py.
        sa.CheckConstraint(
            "(proposal_id IS NOT NULL) <> (campaign_id IS NOT NULL)",
            name="ck_cover_images_exactly_one_owner",
        ),
        # 1.572.864 bait = 1,5 MB. Batas yang sama dipakai services/cover.py
        # saat membaca unggahan; yang di sini menutup jalur yang tidak lewat
        # service sama sekali.
        sa.CheckConstraint(
            "byte_size > 0 AND byte_size <= 1572864",
            name="ck_cover_images_byte_size",
        ),
        # ondelete CASCADE: sampul tidak punya arti apa pun tanpa pemiliknya,
        # dan baris yatim di sini akan menahan penghapusan proposal lewat
        # pelanggaran foreign key yang membingungkan.
        sa.ForeignKeyConstraint(
            ["campaign_id"], ["campaigns.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["proposals.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", name="uq_cover_images_campaign"),
        sa.UniqueConstraint("proposal_id", name="uq_cover_images_proposal"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("cover_images")

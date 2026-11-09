"""system_clock

Satu baris jam virtual tersimpan (D-06, BR-60, BR-63): `CHECK id = 1`
memaksa tabel ini tetap satu baris, jadi "jam saat ini" selalu baca pasti,
tidak pernah ambigu baris mana yang berlaku.

Revision ID: 78b36c0cb4dc
Revises: eab9bed95b66
Create Date: 2026-11-09 16:14:41.017653

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78b36c0cb4dc'
down_revision: Union[str, Sequence[str], None] = '152f14ae708d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "system_clock",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("virtual_now", sa.DateTime(), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_system_clock_tunggal"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("system_clock")

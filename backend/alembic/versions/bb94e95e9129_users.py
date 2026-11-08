"""users

Revision ID: bb94e95e9129
Revises: 20cedbeaca98
Create Date: 2026-11-09 03:06:19.223965

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'bb94e95e9129'
down_revision: Union[str, Sequence[str], None] = '20cedbeaca98'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Didefinisikan terpisah dari kolomnya supaya downgrade bisa memanggil .drop()
# secara eksplisit: op.drop_table saja tidak membuang tipe ENUM Postgres, dan
# tipe yang tersisa membuat upgrade berikutnya gagal karena "role" sudah ada.
role_enum = sa.Enum('investor', 'umkm', 'community', name='role')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('password_hash', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('role', role_enum, nullable=False),
        sa.Column('created_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    role_enum.drop(op.get_bind(), checkfirst=True)

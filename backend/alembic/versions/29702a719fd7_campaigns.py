"""campaigns

Revision ID: 29702a719fd7
Revises: bb94e95e9129
Create Date: 2026-11-09 03:55:04.600930

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '29702a719fd7'
down_revision: Union[str, Sequence[str], None] = 'bb94e95e9129'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Didefinisikan terpisah dari kolomnya supaya downgrade bisa memanggil .drop()
# secara eksplisit: op.drop_table saja tidak membuang tipe ENUM Postgres, dan
# tipe yang tersisa membuat upgrade berikutnya gagal karena sudah ada.
sector_enum = sa.Enum(
    'kuliner', 'kerajinan', 'pertanian', 'jasa', 'ritel', 'teknologi', name='sector'
)
campaign_status_enum = sa.Enum('open', 'closed', name='campaign_status')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('investor_id', sa.Uuid(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('sector', sector_enum, nullable=False),
        sa.Column('target_amount', sa.BigInteger(), nullable=False),
        sa.Column('apply_deadline', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column('funding_deadline', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column('score_threshold', sa.Integer(), nullable=False),
        sa.Column('status', campaign_status_enum, nullable=False),
        sa.Column('created_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.CheckConstraint('funding_deadline > apply_deadline', name='ck_campaign_urutan_deadline'),
        sa.CheckConstraint('score_threshold BETWEEN 0 AND 100', name='ck_campaign_threshold'),
        sa.CheckConstraint('target_amount > 0', name='ck_campaign_target_positif'),
        sa.ForeignKeyConstraint(['investor_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_campaigns_investor_id'), 'campaigns', ['investor_id'], unique=False)
    op.create_index(op.f('ix_campaigns_sector'), 'campaigns', ['sector'], unique=False)
    op.create_index(op.f('ix_campaigns_status'), 'campaigns', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_campaigns_status'), table_name='campaigns')
    op.drop_index(op.f('ix_campaigns_sector'), table_name='campaigns')
    op.drop_index(op.f('ix_campaigns_investor_id'), table_name='campaigns')
    op.drop_table('campaigns')
    campaign_status_enum.drop(op.get_bind(), checkfirst=True)
    sector_enum.drop(op.get_bind(), checkfirst=True)

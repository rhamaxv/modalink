"""proposals_skeleton

Revision ID: 6b9fa987d330
Revises: 29702a719fd7
Create Date: 2026-11-09 04:02:21.055373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '6b9fa987d330'
down_revision: Union[str, Sequence[str], None] = '29702a719fd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Didefinisikan terpisah dari kolomnya supaya downgrade bisa memanggil .drop()
# secara eksplisit: op.drop_table saja tidak membuang tipe ENUM Postgres, dan
# tipe yang tersisa membuat upgrade berikutnya gagal karena sudah ada.
proposal_status_enum = sa.Enum(
    'submitted', 'listed', 'partially_funded', 'rejected', 'funded', 'failed',
    'completed', name='proposal_status',
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'proposals',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('campaign_id', sa.Uuid(), nullable=False),
        sa.Column('umkm_id', sa.Uuid(), nullable=False),
        sa.Column('status', proposal_status_enum, nullable=False),
        sa.Column('created_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.ForeignKeyConstraint(['umkm_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_proposals_campaign_id'), 'proposals', ['campaign_id'], unique=False)
    op.create_index(op.f('ix_proposals_status'), 'proposals', ['status'], unique=False)
    op.create_index(op.f('ix_proposals_umkm_id'), 'proposals', ['umkm_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_proposals_umkm_id'), table_name='proposals')
    op.drop_index(op.f('ix_proposals_status'), table_name='proposals')
    op.drop_index(op.f('ix_proposals_campaign_id'), table_name='proposals')
    op.drop_table('proposals')
    proposal_status_enum.drop(op.get_bind(), checkfirst=True)

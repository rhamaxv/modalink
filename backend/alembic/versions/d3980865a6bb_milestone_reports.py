"""milestone_reports

Tabel laporan progres milestone (BR-41 sampai BR-46). Banyak baris per
milestone: laporan `rejected` tidak pernah di-UPDATE atau dihapus, revisi
selalu baris baru, sama seperti scoring_results pada fase sebelumnya.

Seperti scoring_verdict dan ledger_entry_type, review_status_enum
didefinisikan terpisah dari kolomnya supaya downgrade bisa memanggil .drop()
secara eksplisit: CREATE TABLE di sini yang memicu CREATE TYPE, bukan ALTER
TABLE ADD COLUMN, jadi drop_table saja tidak ikut menghapus tipenya.

Revision ID: d3980865a6bb
Revises: eab9bed95b66
Create Date: 2026-11-09 15:44:31.447901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'd3980865a6bb'
down_revision: Union[str, Sequence[str], None] = 'eab9bed95b66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

review_status_enum = sa.Enum(
    'pending', 'approved', 'rejected', name='milestone_report_status',
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'milestone_reports',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('milestone_id', sa.Uuid(), nullable=False),
        sa.Column('umkm_id', sa.Uuid(), nullable=False),
        sa.Column('narrative', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('review_status', review_status_enum, nullable=False),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewer_note', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('submitted_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.Column('reviewed_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(['milestone_id'], ['proposal_milestones.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.ForeignKeyConstraint(['umkm_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_milestone_reports_milestone_id'), 'milestone_reports',
        ['milestone_id'], unique=False,
    )
    op.create_index(
        'ix_milestone_reports_milestone_id_submitted_at', 'milestone_reports',
        ['milestone_id', 'submitted_at'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_milestone_reports_milestone_id_submitted_at',
        table_name='milestone_reports',
    )
    op.drop_index(
        op.f('ix_milestone_reports_milestone_id'), table_name='milestone_reports',
    )
    op.drop_table('milestone_reports')
    review_status_enum.drop(op.get_bind(), checkfirst=True)

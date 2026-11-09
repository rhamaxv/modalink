"""scoring_results

Tabel append-only: satu baris per percobaan scoring (BR-76). Rescore selalu
menambah baris baru, baris lama tidak pernah ditimpa.

Revision ID: 20db329f14af
Revises: b7d1fab085fd
Create Date: 2026-11-09 12:30:52.387368

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '20db329f14af'
down_revision: Union[str, Sequence[str], None] = 'b7d1fab085fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Didefinisikan terpisah dari kolomnya, seperti scoring_status_enum di
# b7d1fab085fd, supaya downgrade bisa memanggil .drop() secara eksplisit.
# Berbeda dari migrasi itu, di sini CREATE TABLE sendiri yang memicu CREATE
# TYPE (bukan ALTER TABLE ADD COLUMN), jadi tidak perlu .create() manual.
scoring_verdict_enum = sa.Enum('listed', 'rejected', name='scoring_verdict')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'scoring_results',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('proposal_id', sa.Uuid(), nullable=False),
        sa.Column('engine_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('model_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('fit_score', sa.SmallInteger(), nullable=False),
        sa.Column('data_quality_score', sa.SmallInteger(), nullable=False),
        sa.Column('impact_score', sa.SmallInteger(), nullable=False),
        sa.Column('total_score', sa.SmallInteger(), nullable=False),
        sa.Column('red_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('brief', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('threshold_used', sa.SmallInteger(), nullable=False),
        sa.Column('verdict', scoring_verdict_enum, nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('created_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
        sa.CheckConstraint(
            'data_quality_score BETWEEN 0 AND 30',
            name='ck_scoring_results_data_quality_score',
        ),
        sa.CheckConstraint('fit_score BETWEEN 0 AND 40', name='ck_scoring_results_fit_score'),
        sa.CheckConstraint(
            'impact_score BETWEEN 0 AND 30', name='ck_scoring_results_impact_score'
        ),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposals.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_scoring_results_proposal_id'), 'scoring_results', ['proposal_id'],
        unique=False,
    )
    op.create_index(
        'ix_scoring_results_proposal_id_created_at', 'scoring_results',
        ['proposal_id', 'created_at'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_scoring_results_proposal_id_created_at', table_name='scoring_results')
    op.drop_index(op.f('ix_scoring_results_proposal_id'), table_name='scoring_results')
    op.drop_table('scoring_results')
    scoring_verdict_enum.drop(op.get_bind(), checkfirst=True)

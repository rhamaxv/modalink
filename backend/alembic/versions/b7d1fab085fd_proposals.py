"""proposals

Memperluas kerangka minimal `proposals` dari fase campaign dengan kolom
bisnis proposal dan tabel `proposal_milestones` (BR-10 sampai BR-18). Tabel
`proposals` diperluas lewat ALTER, bukan drop-dan-create-ulang: migrasi
`proposals_skeleton` tetap jadi satu-satunya tempat yang membuat tabelnya.

Partial unique index yang menegakkan BR-13 tidak dihasilkan autogenerate,
jadi ditulis tangan di sini, seperti check constraint pada kolom yang
ditambah lewat ALTER TABLE (autogenerate hanya menangkap constraint yang
melekat pada kolom baru lewat create_table, bukan add_column).

Revision ID: b7d1fab085fd
Revises: 6b9fa987d330
Create Date: 2026-11-09 04:23:53.445666

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b7d1fab085fd'
down_revision: Union[str, Sequence[str], None] = '6b9fa987d330'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Didefinisikan terpisah dari kolomnya supaya downgrade bisa memanggil .drop()
# secara eksplisit, seperti proposal_status_enum di proposals_skeleton.
scoring_status_enum = sa.Enum(
    'pending', 'processing', 'done', 'failed', name='scoring_status',
)
milestone_status_enum = sa.Enum(
    'pending', 'reported', 'disbursed', name='milestone_status',
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'proposal_milestones',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('proposal_id', sa.Uuid(), nullable=False),
        sa.Column('seq', sa.SmallInteger(), nullable=False),
        sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('status', milestone_status_enum, nullable=False),
        sa.Column('disbursed_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
        sa.CheckConstraint('amount > 0', name='ck_milestone_amount_positif'),
        sa.CheckConstraint('seq >= 1', name='ck_milestone_seq_positif'),
        sa.ForeignKeyConstraint(['proposal_id'], ['proposals.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('proposal_id', 'seq', name='uq_milestone_proposal_seq'),
    )
    op.create_index(
        op.f('ix_proposal_milestones_proposal_id'),
        'proposal_milestones', ['proposal_id'], unique=False,
    )

    op.add_column('proposals', sa.Column(
        'business_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False,
    ))
    op.add_column('proposals', sa.Column(
        'business_profile', sqlmodel.sql.sqltypes.AutoString(), nullable=False,
    ))
    op.add_column('proposals', sa.Column(
        'fund_usage_plan', sqlmodel.sql.sqltypes.AutoString(), nullable=False,
    ))
    op.add_column('proposals', sa.Column(
        'business_projection', sqlmodel.sql.sqltypes.AutoString(), nullable=False,
    ))
    op.add_column('proposals', sa.Column(
        'requested_amount', sa.BigInteger(), nullable=False,
    ))
    # ALTER TABLE ADD COLUMN, berbeda dari CREATE TABLE, tidak memicu
    # pembuatan tipe ENUM secara otomatis; tipenya harus dibuat dulu di sini.
    scoring_status_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('proposals', sa.Column(
        'scoring_status', scoring_status_enum, nullable=False,
    ))
    op.add_column('proposals', sa.Column('lead_investor_id', sa.Uuid(), nullable=True))
    op.add_column(
        'proposals',
        sa.Column('funded_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=True),
    )
    op.create_check_constraint(
        'ck_proposal_requested_amount_positif', 'proposals', 'requested_amount > 0',
    )
    op.create_index(
        op.f('ix_proposals_scoring_status'), 'proposals', ['scoring_status'],
        unique=False,
    )
    op.create_foreign_key(
        'fk_proposals_lead_investor_id_users', 'proposals', 'users',
        ['lead_investor_id'], ['id'],
    )

    # BR-13: satu UMKM hanya boleh punya satu proposal aktif per campaign.
    # "Aktif" berarti status selain rejected dan failed, sehingga UMKM yang
    # ditolak tetap bisa mencoba lagi. Ini tidak terungkap autogenerate.
    op.create_index(
        'uq_proposal_aktif_per_umkm_per_campaign',
        'proposals', ['campaign_id', 'umkm_id'],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('rejected', 'failed')"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_proposal_aktif_per_umkm_per_campaign', table_name='proposals')
    op.drop_constraint('fk_proposals_lead_investor_id_users', 'proposals', type_='foreignkey')
    op.drop_index(op.f('ix_proposals_scoring_status'), table_name='proposals')
    op.drop_constraint('ck_proposal_requested_amount_positif', 'proposals', type_='check')
    op.drop_column('proposals', 'funded_at')
    op.drop_column('proposals', 'lead_investor_id')
    op.drop_column('proposals', 'scoring_status')
    op.drop_column('proposals', 'requested_amount')
    op.drop_column('proposals', 'business_projection')
    op.drop_column('proposals', 'fund_usage_plan')
    op.drop_column('proposals', 'business_profile')
    op.drop_column('proposals', 'business_name')
    scoring_status_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_index(op.f('ix_proposal_milestones_proposal_id'), table_name='proposal_milestones')
    op.drop_table('proposal_milestones')
    milestone_status_enum.drop(op.get_bind(), checkfirst=True)

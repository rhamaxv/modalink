"""pledges_and_ledger

Dua tabel baru untuk fase co-funding (BR-20 sampai BR-23, BR-50 sampai BR-55):

`ledger_entries` adalah ledger uang append-only. Tidak ada endpoint, service,
atau migrasi yang boleh meng-UPDATE atau menghapus barisnya; koreksi selalu
berupa entri baru ke arah berlawanan. `amount > 0` adalah penjaga database,
bukan sekadar validasi Python: arah dana ada di `entry_type`, bukan di tanda
`amount`. `idempotency_key` unik supaya klik ganda menghasilkan satu entri.

`pledges` adalah kerangka tabel yang baru dipakai penuh (dengan penguncian
baris proposal) di task berikutnya; di sini hanya dibutuhkan agar
`recompute_funding_status` dan `total_pledge_aktif` punya sesuatu untuk
dibaca.

Seperti scoring_results, kedua enum (`ledger_entry_type`, `pledge_status`)
didefinisikan terpisah dari kolomnya supaya downgrade bisa memanggil .drop()
secara eksplisit: CREATE TABLE di sini yang memicu CREATE TYPE, bukan ALTER
TABLE ADD COLUMN, jadi drop_table saja tidak ikut menghapus tipenya.

Revision ID: b66ce302d696
Revises: d9ce00cd5000
Create Date: 2026-11-09 13:32:12.414590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b66ce302d696'
down_revision: Union[str, Sequence[str], None] = 'd9ce00cd5000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ledger_entry_type_enum = sa.Enum(
    'pledge_in', 'refund_out', 'disbursement_out', name='ledger_entry_type',
)
pledge_status_enum = sa.Enum('active', 'cancelled', name='pledge_status')


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('ledger_entries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('proposal_id', sa.Uuid(), nullable=False),
    sa.Column('entry_type', ledger_entry_type_enum, nullable=False),
    sa.Column('amount', sa.BigInteger(), nullable=False),
    sa.Column('ref_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('ref_id', sa.Uuid(), nullable=True),
    sa.Column('actor_id', sa.Uuid(), nullable=True),
    sa.Column('idempotency_key', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
    sa.CheckConstraint('amount > 0', name='ck_ledger_amount_positif'),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['proposal_id'], ['proposals.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ledger_entries_idempotency_key'), 'ledger_entries', ['idempotency_key'], unique=True)
    op.create_index(op.f('ix_ledger_entries_proposal_id'), 'ledger_entries', ['proposal_id'], unique=False)
    op.create_table('pledges',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('proposal_id', sa.Uuid(), nullable=False),
    sa.Column('investor_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.BigInteger(), nullable=False),
    sa.Column('status', pledge_status_enum, nullable=False),
    sa.Column('created_at', sqlmodel.sql.sqltypes.UTCDateTime(), nullable=False),
    sa.CheckConstraint('amount > 0', name='ck_pledges_amount_positif'),
    sa.ForeignKeyConstraint(['investor_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['proposal_id'], ['proposals.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pledges_investor_id'), 'pledges', ['investor_id'], unique=False)
    op.create_index(op.f('ix_pledges_proposal_id'), 'pledges', ['proposal_id'], unique=False)
    op.create_index(op.f('ix_pledges_status'), 'pledges', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_pledges_status'), table_name='pledges')
    op.drop_index(op.f('ix_pledges_proposal_id'), table_name='pledges')
    op.drop_index(op.f('ix_pledges_investor_id'), table_name='pledges')
    op.drop_table('pledges')
    pledge_status_enum.drop(op.get_bind(), checkfirst=True)
    op.drop_index(op.f('ix_ledger_entries_proposal_id'), table_name='ledger_entries')
    op.drop_index(op.f('ix_ledger_entries_idempotency_key'), table_name='ledger_entries')
    op.drop_table('ledger_entries')
    ledger_entry_type_enum.drop(op.get_bind(), checkfirst=True)

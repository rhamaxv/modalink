"""ledger_entries_append_only_enforcement

Review keamanan Finding 3: "uang tidak pernah di-update" (CLAUDE.md aturan 3,
.claude/skills/ledger-invariants/SKILL.md) selama ini hanya berlaku karena
tidak ada kode yang menulis UPDATE/DELETE pada `ledger_entries`, bukan karena
database menolaknya -- `has_table_privilege('logicodix', 'ledger_entries',
'UPDATE')` dan `...'DELETE')` keduanya true, dan tabel ini tidak punya satu
pun trigger. Tiga lapis kode (service pledge, service milestone, service
ledger) sama-sama memegang sesi database yang sama live, dan ketiganya sama-
sama HANYA dipercaya untuk tidak pernah menulis UPDATE/DELETE secara disiplin.

Trigger di sini menolak setiap UPDATE dan DELETE pada `ledger_entries` di
level database, bukan privilege REVOKE: privilege REVOKE butuh baris "siapa
yang masih boleh menulis" diurus di level role, sementara trigger menolak
siapa pun yang terhubung sebagai peran apa pun, termasuk superuser psql yang
dipakai menjalankan migrasi ini sendiri -- pagar yang sama persis untuk
operator manual dan untuk bug di kode aplikasi.

Satu jalan keluar eksplisit disediakan: GUC sesi `modalink.ledger_cleanup_override`.
Tiga test konkurensi (test_pledge_concurrency.py, test_two_milestone_race.py,
test_concurrent_approve.py) membersihkan baris ledger_entries milik proposal
uji lewat SessionLocal mentah di teardown-nya, karena test itu memakai commit
sungguhan (bukan fixture `db` yang di-rollback) dan harus membersihkan data
sendiri. Trigger yang menolak tanpa kecuali akan merusak ketiga teardown itu.
GUC ini harus di-SET LOCAL secara eksplisit sebelum DELETE semacam itu, dan
kode aplikasi tidak pernah melakukannya -- escape hatch ini hanya terlihat
dan dipakai di infrastruktur test, tidak pernah di app/.

Revision ID: a72b47da4fb7
Revises: 78b36c0cb4dc
Create Date: 2026-11-09 18:09:24.424443

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a72b47da4fb7'
down_revision: Union[str, Sequence[str], None] = '78b36c0cb4dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_FUNCTION_NAME = "ledger_entries_larang_update_delete"
_TRIGGER_UPDATE = "trg_ledger_entries_larang_update"
_TRIGGER_DELETE = "trg_ledger_entries_larang_delete"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        f"""
        CREATE FUNCTION {_FUNCTION_NAME}() RETURNS TRIGGER AS $$
        BEGIN
            IF current_setting('modalink.ledger_cleanup_override', true)
                IS DISTINCT FROM 'on' THEN
                RAISE EXCEPTION
                    'ledger_entries bersifat append-only (BR-51): % pada baris id=% ditolak.',
                    TG_OP, OLD.id;
            END IF;
            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {_TRIGGER_UPDATE}
            BEFORE UPDATE ON ledger_entries
            FOR EACH ROW EXECUTE FUNCTION {_FUNCTION_NAME}();
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {_TRIGGER_DELETE}
            BEFORE DELETE ON ledger_entries
            FOR EACH ROW EXECUTE FUNCTION {_FUNCTION_NAME}();
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER_DELETE} ON ledger_entries;")
    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER_UPDATE} ON ledger_entries;")
    op.execute(f"DROP FUNCTION IF EXISTS {_FUNCTION_NAME}();")

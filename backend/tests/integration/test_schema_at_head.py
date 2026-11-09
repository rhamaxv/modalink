# Database test harus berada di revisi Alembic terbaru sebelum suite dipercaya.
#
# Tanpa pagar ini, database yang tertinggal satu migrasi membuat test gagal
# dengan pesan yang tidak menyebut penyebabnya sama sekali: constraint yang
# belum ada menghasilkan "DID NOT RAISE IntegrityError", dan tabel yang belum
# ada menghasilkan "relation does not exist". Keduanya sudah pernah menghabiskan
# waktu beberapa agen di project ini, dan satu di antaranya menyimpulkan
# "kontaminasi agen lain" padahal databasenya hanya belum dimigrasi.
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text

AKAR = Path(__file__).resolve().parents[2]


def _head_dari_berkas() -> str:
    cfg = Config(str(AKAR / "alembic.ini"))
    cfg.set_main_option("script_location", str(AKAR / "alembic"))
    return ScriptDirectory.from_config(cfg).get_current_head() or ""


async def test_database_test_is_at_latest_revision(db):
    terpasang = (
        await db.execute(text("select version_num from alembic_version"))
    ).scalar()
    head = _head_dari_berkas()
    assert terpasang == head, (
        f"database test ada di revisi {terpasang} sementara berkas migrasi sudah "
        f"sampai {head}. Jalankan `alembic upgrade head` dengan DATABASE_URL yang "
        f"sama sebelum mempercayai kegagalan test lain di suite ini."
    )


def test_only_one_migration_head_exists():
    """Rantai migrasi bercabang pernah membuat database melaporkan dirinya
    terbaru sementara dua tabel tidak ada. Dua head berarti satu cabang tidak
    akan pernah dijalankan oleh `upgrade head`."""
    cfg = Config(str(AKAR / "alembic.ini"))
    cfg.set_main_option("script_location", str(AKAR / "alembic"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    assert len(heads) == 1, f"rantai migrasi bercabang, head: {heads}"

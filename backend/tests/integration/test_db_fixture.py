from sqlalchemy import select, text

from app.models.user import Role, User
from app.services.auth import hash_password

EMAIL_UJI_SAVEPOINT = "uji-savepoint-commit@contoh.id"


async def test_commit_inside_db_does_not_leak_through_outer_rollback(db):
    """join_transaction_mode="create_savepoint" (H-1): sejak get_session
    produksi sungguh memanggil session.commit(), sesi fixture `db` ini wajib
    menyerap commit() itu sebagai SAVEPOINT yang menumpang di atas transaksi
    luar, bukan benar-benar mengirim COMMIT ke Postgres. Baris yang
    di-commit() di sini diperiksa lenyap lagi oleh test berikutnya
    (lihat test_row_after_commit_not_visible_to_next_test di bawah),
    yang hanya bisa terbukti kalau trans.rollback() di fixture db masih
    benar-benar berlaku walau sesi di dalamnya pernah commit().
    """
    db.add(
        User(
            email=EMAIL_UJI_SAVEPOINT,
            password_hash=hash_password("rahasia123"),
            name="Uji Savepoint",
            role=Role.UMKM,
        )
    )
    await db.commit()
    baris = (
        await db.scalars(select(User).where(User.email == EMAIL_UJI_SAVEPOINT))
    ).one()
    assert baris.email == EMAIL_UJI_SAVEPOINT


async def test_row_after_commit_not_visible_to_next_test(db):
    """Berjalan setelah test di atas (urutan deklarasi, tidak diacak: tidak
    ada plugin randomisasi di pyproject.toml). Kalau baris itu masih ada,
    commit() di test sebelumnya lolos dari SAVEPOINT dan benar-benar
    menembus transaksi luar, persis kebocoran yang join_transaction_mode
    mestinya cegah."""
    baris = (
        await db.scalars(select(User).where(User.email == EMAIL_UJI_SAVEPOINT))
    ).first()
    assert baris is None


async def test_db_fixture_rolled_back_between_tests(db):
    await db.execute(text("CREATE TEMP TABLE jejak (n int)"))
    await db.execute(text("INSERT INTO jejak VALUES (1)"))
    rows = (await db.execute(text("SELECT count(*) FROM jejak"))).scalar()
    assert rows == 1


async def test_db_fixture_clean_in_next_test(db):
    exists = (
        await db.execute(text("SELECT to_regclass('pg_temp.jejak') IS NOT NULL"))
    ).scalar()
    assert exists is False

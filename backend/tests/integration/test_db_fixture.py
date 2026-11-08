from sqlalchemy import text


async def test_fixture_db_dirollback_antar_test(db):
    await db.execute(text("CREATE TEMP TABLE jejak (n int)"))
    await db.execute(text("INSERT INTO jejak VALUES (1)"))
    rows = (await db.execute(text("SELECT count(*) FROM jejak"))).scalar()
    assert rows == 1


async def test_fixture_db_bersih_di_test_berikutnya(db):
    exists = (await db.execute(
        text("SELECT to_regclass('pg_temp.jejak') IS NOT NULL")
    )).scalar()
    assert exists is False

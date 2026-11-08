"""BR-02: email unik lintas peran, disimpan lowercase."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.user import Role, User


async def test_br02_email_unik_lintas_peran(db):
    db.add(User(email="a@x.id", password_hash="h", name="A", role=Role.INVESTOR))
    await db.flush()
    db.add(User(email="a@x.id", password_hash="h", name="B", role=Role.UMKM))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_email_disimpan_lowercase(db):
    u = User(email="Budi@Contoh.ID", password_hash="h", name="Budi", role=Role.UMKM)
    db.add(u)
    await db.flush()
    assert u.email == "budi@contoh.id"

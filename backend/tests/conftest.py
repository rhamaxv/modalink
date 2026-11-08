from dataclasses import dataclass

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine, get_session
from app.main import create_app
from app.models.user import Role, User
from app.services.auth import hash_password, issue_token


@pytest.fixture
async def db():
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            # Flush yang gagal (misal IntegrityError dari constraint unik)
            # sudah membuat Postgres mengabort transaksinya sendiri, sehingga
            # transaksi ini sudah lepas dari koneksi sebelum baris ini
            # tercapai. Rollback kedua pada transaksi yang sudah lepas hanya
            # memicu SAWarning, bukan kebocoran data, jadi dilewati.
            if trans.is_active:
                await trans.rollback()


@pytest.fixture
async def app(db):
    application = create_app()
    application.dependency_overrides[get_session] = lambda: db
    return application


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@dataclass
class PenggunaTeruji:
    """Pengguna yang sudah ada di `db` beserta header Authorization-nya."""

    user: User
    headers: dict[str, str]


async def _pengguna_teruji(db: AsyncSession, role: Role, email: str) -> PenggunaTeruji:
    user = User(
        email=email, password_hash=hash_password("rahasia123"), name="Test", role=role
    )
    db.add(user)
    await db.flush()
    token = issue_token(user.id, user.role)
    return PenggunaTeruji(user=user, headers={"Authorization": f"Bearer {token}"})


@pytest.fixture
async def investor(db):
    return await _pengguna_teruji(db, Role.INVESTOR, "investor-teruji@contoh.id")


@pytest.fixture
async def umkm(db):
    return await _pengguna_teruji(db, Role.UMKM, "umkm-teruji@contoh.id")

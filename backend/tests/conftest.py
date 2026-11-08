from dataclasses import dataclass
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock
from app.db.session import engine, get_session
from app.domain.clock import FrozenClock, SystemClock
from app.main import create_app
from app.models.campaign import Campaign, CampaignStatus, Sector
from app.models.proposal import Proposal, ProposalStatus
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
class Akun:
    """Pengguna yang sudah ada di `db` beserta header Authorization-nya."""

    user: User
    headers: dict[str, str]


async def _buat_akun(db: AsyncSession, email: str, role: Role) -> Akun:
    user = User(
        email=email, password_hash=hash_password("rahasia123"), name="Test", role=role
    )
    db.add(user)
    await db.flush()
    return Akun(user, {"Authorization": f"Bearer {issue_token(user.id, role)}"})


@pytest.fixture
async def investor(db):
    return await _buat_akun(db, "investor-teruji@contoh.id", Role.INVESTOR)


@pytest.fixture
async def umkm(db):
    return await _buat_akun(db, "umkm-teruji@contoh.id", Role.UMKM)


@pytest.fixture
async def community(db):
    return await _buat_akun(db, "warga-teruji@contoh.id", Role.COMMUNITY)


@pytest.fixture
async def investor_lain(db):
    """Investor kedua: peran benar, tapi bukan pemilik campaign manapun di test."""
    return await _buat_akun(db, "investor-lain-teruji@contoh.id", Role.INVESTOR)


@pytest.fixture
async def akun(investor, umkm, community, investor_lain):
    """Peta peran ke akun teruji, dipakai RBAC_MATRIX untuk memilih header."""
    return {
        "investor": investor,
        "umkm": umkm,
        "community": community,
        "investor_lain": investor_lain,
    }


@pytest.fixture
async def campaign(db, investor):
    """Campaign milik `investor`, apply_deadline jatuh di hari ke-7."""
    mulai = SystemClock().now()
    c = Campaign(
        investor_id=investor.user.id,
        title="Modal warung kopi Jakarta Timur",
        description="Mendanai warung kopi skala rumahan." * 2,
        sector=Sector.KULINER,
        target_amount=50_000_000,
        apply_deadline=mulai + timedelta(days=7),
        funding_deadline=mulai + timedelta(days=21),
        score_threshold=60,
        status=CampaignStatus.OPEN,
        created_at=mulai,
    )
    db.add(c)
    await db.flush()
    return c


@pytest.fixture
async def listed_proposal(db, campaign, umkm):
    """Satu proposal lolos skoring untuk campaign fixture, demi BR-77."""
    p = Proposal(
        campaign_id=campaign.id, umkm_id=umkm.user.id, status=ProposalStatus.LISTED
    )
    db.add(p)
    await db.flush()
    return p


@pytest.fixture
def majukan(app):
    """Memajukan jam yang dilihat aplikasi, dipakai menguji auto-close deadline.

    FrozenClock dipasang lewat dependency_overrides, bukan VirtualClock: itu
    baru ada di fase 09.
    """

    async def _majukan(hari: int) -> None:
        app.dependency_overrides[get_clock] = lambda: FrozenClock(
            SystemClock().now() + timedelta(days=hari)
        )

    return _majukan

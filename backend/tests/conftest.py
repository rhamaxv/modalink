from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.ai.mock_engine import MockScoringEngine
from app.api.deps import get_clock, get_session_factory
from app.db.session import engine, get_session
from app.domain.clock import FrozenClock, SystemClock
from app.main import create_app
from app.models.campaign import Campaign, CampaignStatus, Sector
from app.models.pledge import Pledge
from app.models.proposal import (
    Proposal,
    ProposalMilestone,
    ProposalStatus,
    ScoringStatus,
)
from app.models.user import Role, User
from app.models.vote import Vote
from app.schemas.milestone import MilestoneReportIn
from app.services.auth import hash_password, issue_token
from app.services.milestone import approve_milestone, submit_report
from app.services.pledge import create_pledge
from app.services.scoring import jalankan_scoring


@pytest.fixture
async def db():
    async with engine.connect() as conn:
        trans = await conn.begin()
        # join_transaction_mode="create_savepoint": get_session produksi
        # sekarang memanggil session.commit() (H-1), dan tanpa mode ini
        # SQLAlchemy jatuh ke "conditional_savepoint" yang berlaku sebagai
        # "rollback_only" karena trans di atas bukan SAVEPOINT. Mode ini
        # membuat commit/rollback sesi memakai SAVEPOINT yang menumpang di
        # atas trans, jadi apa pun yang di-commit lewat sesi ini tetap ikut
        # hilang saat trans.rollback() di bawah, bukan benar-benar menembus
        # ke Postgres.
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
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

    # Job scoring latar belakang memakai session yang sama dengan request:
    # `db` dibungkus satu transaksi yang baru di-rollback di akhir test (lihat
    # fixture db di atas), bukan dikomit, jadi job yang membuka koneksi baru
    # lewat SessionLocal() sungguhan tidak akan melihat baris yang baru
    # di-flush. Produksi memakai _sesi_job_latar_belakang yang sesungguhnya
    # (app/api/deps.py), yang membuka dan mengomit session sendiri.
    @asynccontextmanager
    async def _sesi_job_uji() -> AsyncIterator[AsyncSession]:
        yield db

    application.dependency_overrides[get_session_factory] = lambda: _sesi_job_uji
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
async def umkm_lain(db):
    """UMKM kedua: bukan pemilik proposal manapun di test, dipakai BR-13 dan akses baca."""
    return await _buat_akun(db, "umkm-lain-teruji@contoh.id", Role.UMKM)


@pytest.fixture
async def community_lain(db):
    """Komunitas kedua: dipakai membuktikan BR-34 (bukan penulis komentar)
    dengan dua akun sungguhan, bukan satu akun yang menghapus komentarnya
    sendiri."""
    return await _buat_akun(db, "warga-lain-teruji@contoh.id", Role.COMMUNITY)


@pytest.fixture
async def umkm_ketiga(db):
    """UMKM ketiga: dipakai rejected_proposal supaya transisi sementaranya
    lewat submitted (sebelum jalankan_scoring menolaknya) tidak bertabrakan
    dengan submitted_proposal atau listed_proposal pada campaign yang sama,
    yang keduanya juga aktif menurut partial unique index (BR-13)."""
    return await _buat_akun(db, "umkm-ketiga-teruji@contoh.id", Role.UMKM)


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
async def campaign_kedaluwarsa(db, investor):
    """Campaign dengan apply_deadline yang sudah lewat, dipakai menguji BR-17."""
    mulai = SystemClock().now()
    c = Campaign(
        investor_id=investor.user.id,
        title="Modal warung yang sudah tutup pendaftaran",
        description="Mendanai warung kopi skala rumahan." * 2,
        sector=Sector.KULINER,
        target_amount=50_000_000,
        apply_deadline=mulai - timedelta(days=1),
        funding_deadline=mulai + timedelta(days=21),
        score_threshold=60,
        status=CampaignStatus.OPEN,
        created_at=mulai - timedelta(days=10),
    )
    db.add(c)
    await db.flush()
    return c


def _isi_proposal_minimal(campaign_id, umkm_id, status: ProposalStatus) -> Proposal:
    """Baris proposal lengkap secara kolom, dipakai fixture yang statusnya
    sudah final secara artifisial (BR-13, bukan lewat mesin skoring)."""
    return Proposal(
        campaign_id=campaign_id,
        umkm_id=umkm_id,
        business_name="Warung Kopi Mbak Sri",
        business_profile="x" * 50,
        fund_usage_plan="x" * 50,
        business_projection="x" * 50,
        requested_amount=10_000_000,
        status=status,
        scoring_status=ScoringStatus.PENDING,
    )


def _proposal_submitted(campaign_id, umkm_id, **ubah) -> Proposal:
    """Baris proposal berstatus submitted, scoring_status pending: titik awal
    sebelum mesin skoring sungguhan dijalankan di atasnya."""
    isi = {
        "campaign_id": campaign_id,
        "umkm_id": umkm_id,
        "business_name": "Warung Kopi Mbak Sri",
        "business_profile": "x" * 110,
        "fund_usage_plan": "x" * 110,
        "business_projection": "x" * 60,
        "requested_amount": 10_000_000,
        "status": ProposalStatus.SUBMITTED,
        "scoring_status": ScoringStatus.PENDING,
    }
    isi.update(ubah)
    return Proposal(**isi)


@pytest.fixture
def clock():
    return FrozenClock(SystemClock().now())


@pytest.fixture
def engine_mock():
    return MockScoringEngine()


class _EngineMeledak:
    """Engine yang selalu meledak, dipakai menguji D-09/BR-74 lewat jalur
    orkestrasi sungguhan, bukan status yang diset langsung."""

    name = "meledak"
    model = "meledak"

    async def score(self, proposal, campaign):
        raise RuntimeError("engine meledak")


@pytest.fixture
def engine_meledak():
    return _EngineMeledak()


@pytest.fixture
async def listed_proposal(db, campaign, umkm_lain, clock):
    """Satu proposal lolos skoring untuk campaign fixture, dicapai lewat
    MockScoringEngine dan orkestrasi sungguhan (BR-73), bukan status yang
    diset langsung sekarang mesin skoring sudah ada.

    Dimiliki umkm_lain, bukan umkm: submitted_proposal di bawah ini juga
    aktif menurut BR-13 pada campaign yang sama, dan partial unique index
    hanya mengizinkan satu proposal aktif per pasangan campaign-umkm. Test
    yang butuh keduanya sekaligus (daftar proposal per campaign) akan gagal
    dengan IntegrityError kalau kedua fixture berbagi umkm yang sama.
    """
    p = _proposal_submitted(
        campaign.id,
        umkm_lain.user.id,
        business_profile="x" * 110 + " [[SCORE:80]]",  # threshold campaign 60
    )
    db.add(p)
    await db.flush()
    await jalankan_scoring(db, p.id, MockScoringEngine(), clock)
    await db.refresh(p)
    # Dua milestone yang jumlahnya persis sama dengan requested_amount
    # (BR-14), dipakai fixture milestone (funded_proposal.milestones) di
    # tests/integration/test_milestone_lapor.py.
    for seq, judul in ((1, "Beli mesin"), (2, "Bahan baku")):
        db.add(
            ProposalMilestone(
                proposal_id=p.id,
                seq=seq,
                title=judul,
                description="x" * 20,
                amount=p.requested_amount // 2,
            )
        )
    await db.flush()
    return p


@dataclass
class ProposalWithPledge:
    """Proposal dibungkus pledge-nya, khusus untuk fixture test.

    SQLModel (lewat validasi Pydantic v2) menolak menitipkan atribut bebas
    seperti `.pledges` langsung ke instance Proposal -- Proposal sengaja
    tidak punya relationship() ke Pledge (lihat models/proposal.py), jadi
    pembungkus tipis ini yang menyediakan funded_proposal.pledges[0].id
    tanpa query tambahan maupun relationship ORM yang tidak dibutuhkan
    produksi.
    """

    proposal: Proposal
    pledges: list[Pledge]
    milestones: list[ProposalMilestone]

    def __getattr__(self, name: str):
        return getattr(self.proposal, name)


@pytest.fixture
async def funded_proposal(db, listed_proposal, investor, clock):
    """Proposal yang sudah funded lewat satu pledge penuh sungguhan (BR-25),
    bukan status yang diset langsung: dipakai menguji bahwa pledge yang
    sudah terkunci (proposal funded) tidak bisa dibatalkan lagi.

    Pledge-nya dibuat oleh `investor`, bukan `investor_lain`, karena test
    yang memakai fixture ini membatalkan lewat akun `investor` -- kalau
    pledge-nya milik akun lain, test itu akan berhenti di pemeriksaan
    kepemilikan (403) sebelum sempat membuktikan BR-25 (409).

    `.milestones` adalah dua baris dari `listed_proposal`, terurut `seq`:
    dipakai tests/integration/test_milestone_lapor.py lewat
    `funded_proposal.milestones[0]` / `[1]`, bukan lewat relationship ORM
    (Proposal sengaja tidak punya itu, lihat docstring ProposalWithPledge).
    """
    pledge = await create_pledge(
        db, investor.user, listed_proposal, listed_proposal.requested_amount, clock
    )
    await db.refresh(listed_proposal)
    milestones = (
        await db.scalars(
            select(ProposalMilestone)
            .where(ProposalMilestone.proposal_id == listed_proposal.id)
            .order_by(ProposalMilestone.seq)
        )
    ).all()
    return ProposalWithPledge(
        proposal=listed_proposal, pledges=[pledge], milestones=list(milestones)
    )


@pytest.fixture
async def submitted_proposal(db, campaign, umkm):
    """Proposal yang belum dinilai, dimiliki `umkm` karena test kepemilikan
    (test_proposal_submitted_terlihat_oleh_pemiliknya) memverifikasi lewat akun ini."""
    p = _proposal_submitted(campaign.id, umkm.user.id)
    db.add(p)
    await db.flush()
    return p


@pytest.fixture
async def rejected_proposal(db, campaign, umkm_ketiga, clock):
    """Proposal yang ditolak scoring sungguhan lewat red flag kritis (BR-72),
    dicapai lewat orkestrasi, bukan status yang diset langsung. Statusnya
    melewati submitted dulu (aktif menurut BR-13) sebelum jalankan_scoring
    menolaknya, jadi pemiliknya harus berbeda dari submitted_proposal dan
    listed_proposal yang berbagi campaign yang sama dan tetap aktif di sana
    (lihat umkm_ketiga)."""
    p = _proposal_submitted(
        campaign.id,
        umkm_ketiga.user.id,
        business_projection="x" * 60 + " [[RED_FLAG:critical]]",
    )
    db.add(p)
    await db.flush()
    await jalankan_scoring(db, p.id, MockScoringEngine(), clock)
    await db.refresh(p)
    return p


@pytest.fixture
async def proposal_scoring_gagal(db, campaign, umkm, clock, engine_meledak):
    """Proposal yang penilaiannya gagal secara teknis: status tetap submitted,
    scoring_status failed, dicapai lewat orkestrasi sungguhan dengan engine
    yang meledak (D-09), supaya fixture ini menguji jalur yang sama dengan
    produksi, bukan status yang diset langsung."""
    p = _proposal_submitted(
        campaign.id, umkm.user.id, business_name="Warung Gagal Nilai"
    )
    db.add(p)
    await db.flush()
    await jalankan_scoring(db, p.id, engine_meledak, clock)
    await db.refresh(p)
    return p


@dataclass
class ProposalWithSkorTerbaru:
    """Proposal dibungkus skor sungguhan yang seharusnya dipakai UI, khusus
    fixture test. Atribut bebas seperti ini ditolak langsung di instance
    Proposal (lihat docstring ProposalWithPledge di atas), jadi pembungkus
    tipis yang sama dipakai lagi di sini."""

    proposal: Proposal
    skor_terbaru: int

    def __getattr__(self, name: str):
        return getattr(self.proposal, name)


@pytest.fixture
def proposal_dengan(db, campaign, clock):
    """Factory proposal dengan skor dan jumlah vote yang dikontrol, dipakai
    menguji urutan daftar proposal investor (10-api-contract.md: "terurut
    skor lalu vote lalu waktu submit"). Skor dicapai lewat scoring
    sungguhan via MockScoringEngine dan penanda [[SCORE:n]] (BR-73), bukan
    ditulis langsung ke scoring_results, supaya test di atasnya memverifikasi
    jalur baca produksi yang sesungguhnya, termasuk kasus skor di bawah
    threshold campaign yang membuat proposal berstatus rejected -- pemilik
    campaign tetap melihatnya di endpoint ini.

    Setiap panggilan memakai UMKM baru supaya partial unique index BR-13
    (satu proposal aktif per UMKM per campaign) tidak pernah jadi penghalang,
    dan pool akun komunitas dipakai ulang antar panggilan untuk vote supaya
    jumlah akun yang dibuat tidak meledak di test dengan banyak proposal.
    """
    counter = {"n": 0}
    pool: list[Akun] = []

    async def _akun_komunitas(indeks: int) -> Akun:
        while indeks >= len(pool):
            pool.append(
                await _buat_akun(
                    db, f"vote-pool-{len(pool)}-teruji@contoh.id", Role.COMMUNITY
                )
            )
        return pool[indeks]

    async def _buat(skor: int, vote: int) -> Proposal:
        counter["n"] += 1
        n = counter["n"]
        umkm_akun = await _buat_akun(db, f"umkm-urutan-{n}-teruji@contoh.id", Role.UMKM)
        p = _proposal_submitted(
            campaign.id,
            umkm_akun.user.id,
            business_name=f"Warung Urutan {n}",
            business_profile="x" * 110 + f" [[SCORE:{skor}]]",
        )
        db.add(p)
        await db.flush()
        await jalankan_scoring(db, p.id, MockScoringEngine(), clock)
        for i in range(vote):
            akun = await _akun_komunitas(i)
            db.add(Vote(proposal_id=p.id, user_id=akun.user.id))
        await db.flush()
        await db.refresh(p)
        return p

    return _buat


@pytest.fixture
async def banyak_proposal(proposal_dengan):
    """Beberapa proposal dengan skor dan vote yang sama, dipakai membuktikan
    urutan stabil antar-request murni dari tie-break created_at lalu id,
    bukan dari nilai skor/vote yang berbeda-beda."""
    return [await proposal_dengan(skor=60, vote=1) for _ in range(5)]


@pytest.fixture
async def proposal_discore_ulang(db, campaign, clock):
    """Proposal yang dinilai dua kali (BR-76, append-only): baris pertama
    tidak boleh terpilih lagi sebagai skor yang dipakai UI setelah baris
    kedua ditulis. Mengulang pola test_br76_dua_percobaan_scoring_sungguhan_
    meninggalkan_dua_baris di test_scoring_flow.py, bukan menulis dua baris
    ScoringResult langsung: query produksi harus benar-benar diuji lewat
    jalur yang sama dengan yang menulis datanya."""
    umkm_akun = await _buat_akun(db, "umkm-discore-ulang-teruji@contoh.id", Role.UMKM)
    p = _proposal_submitted(
        campaign.id, umkm_akun.user.id, business_profile="x" * 110 + " [[SCORE:50]]"
    )
    db.add(p)
    await db.flush()
    await jalankan_scoring(db, p.id, MockScoringEngine(), clock)

    await db.refresh(p)
    p.scoring_status = ScoringStatus.PENDING
    p.status = ProposalStatus.SUBMITTED
    # Ganti, bukan ditambah: MockScoringEngine mengambil penanda [[SCORE:n]]
    # PERTAMA yang ditemukan di teks gabungan (lihat mock_engine.py), jadi
    # menambahkan [[SCORE:95]] di belakang [[SCORE:50]] yang lama akan tetap
    # menghasilkan 50 lagi, bukan membuktikan apa pun soal baris terbaru.
    p.business_profile = "x" * 110 + " [[SCORE:95]]"
    await db.flush()
    await jalankan_scoring(db, p.id, MockScoringEngine(), clock)
    await db.refresh(p)
    return ProposalWithSkorTerbaru(proposal=p, skor_terbaru=95)


@pytest.fixture
def buat_proposal(db, campaign, umkm):
    """Pembuat proposal lepas status, dipakai menguji partial unique index (BR-13)."""

    async def _buat(status: ProposalStatus) -> Proposal:
        p = _isi_proposal_minimal(campaign.id, umkm.user.id, status)
        db.add(p)
        await db.flush()
        return p

    return _buat


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


@pytest.fixture
def body_proposal():
    """Payload submit proposal yang valid, sumber tunggal untuk test submit dan
    akses (C-23). Sebelumnya didefinisikan ulang verbatim di dua berkas test,
    dan dua salinan itu bisa diam-diam melenceng satu sama lain.
    """

    def _body(**ubah):
        isi = {
            "business_name": "Warung Kopi Mbak Sri",
            "business_profile": "Warung kopi rumahan di Jakarta Timur, berjalan 3 tahun, "
            "2 pekerja, omzet rata-rata Rp12 juta per bulan.",
            "requested_amount": 10_000_000,
            # 162 karakter, di atas minimum 100 BR-10. Rubrik skoring AI
            # menilai kelengkapan isian di field ini, jadi versi ringkas
            # sebelumnya (77 karakter) tidak boleh jadi fixture tetap.
            "fund_usage_plan": "Rp6 juta untuk mesin kopi semi-otomatis, Rp3 juta untuk "
            "bahan baku biji dan susu selama tiga bulan, dan Rp1 juta "
            "untuk memperbaiki etalase depan yang sudah lapuk.",
            "business_projection": "Omzet diperkirakan naik ke Rp18 juta per bulan "
            "dalam 6 bulan setelah mesin baru dipakai.",
            "milestones": [
                {
                    "seq": 1,
                    "title": "Beli mesin",
                    "description": "x" * 20,
                    "amount": 5_000_000,
                },
                {
                    "seq": 2,
                    "title": "Bahan baku",
                    "description": "x" * 20,
                    "amount": 5_000_000,
                },
            ],
        }
        return isi | ubah

    return _body


@pytest.fixture
async def milestone_reported(db, funded_proposal, umkm_lain, investor, clock):
    """Milestone kedua `funded_proposal`, sudah dilaporkan (`reported`),
    dipakai menguji approve/reject laporan (T-30, T-31). Dicapai lewat
    orkestrasi sungguhan -- approve_milestone untuk mencairkan milestone
    pertama tanpa laporan (D-13), lalu submit_report untuk yang kedua --
    bukan status yang diset langsung.

    `umkm_lain`, bukan `umkm`: `funded_proposal` (lewat `listed_proposal`)
    dimiliki `umkm_lain`, lihat docstring fixture itu soal BR-13.
    """
    m1, m2 = funded_proposal.milestones
    await approve_milestone(db, m1, investor.user, clock)
    await submit_report(
        db,
        umkm_lain.user,
        m2,
        MilestoneReportIn(narrative="x" * 60, metrics=None),
        clock,
    )
    await db.refresh(m2)
    return m2

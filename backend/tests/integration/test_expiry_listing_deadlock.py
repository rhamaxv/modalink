"""Review keamanan Finding 1: GET anonim yang mengunci baris proposal dalam
urutan berlawanan.

`daftar_proposal_publik` mengurutkan tampilannya created_at DESC, id DESC;
`daftar_proposal_campaign` mengurutkan total_score DESC, vote_count DESC,
created_at, id. Keduanya memanggil `evaluasi_kedaluwarsa` per baris dalam
urutan TAMPIL itu, dan fungsi itu mengambil `SELECT ... FOR UPDATE` atas
proposal yang kedaluwarsa. Dua proposal kedaluwarsa pada campaign yang sama
bisa muncul dalam urutan tampil yang berlawanan di dua endpoint ini, dan dua
request anonim yang bersamaan lalu saling mengunci baris secara berlawanan
arah -- Postgres mendeteksi siklus tunggu itu sebagai `40P01 deadlock
detected` dan mengabort salah satu transaksi, yang muncul ke pemanggil
sebagai HTTP 500 tak tertangani (tidak ada apa pun di app/errors.py yang
menangkap DBAPIError).

Test ini memakai dua sesi/koneksi database sungguhan lewat `create_app()`
tanpa override `get_session`, bukan fixture `db` yang dibungkus satu
transaksi: yang diuji adalah perilaku locking ANTAR transaksi, dan fixture
`db` membuatnya mustahil berebut lock dengan siapa pun (pola yang sama
dengan tests/integration/test_pledge_concurrency.py).
"""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import app.services.expiry as expiry_module
from app.ai.mock_engine import MockScoringEngine
from app.db.session import SessionLocal
from app.domain.clock import FrozenClock, SystemClock
from app.main import create_app
from app.models.campaign import Campaign, CampaignStatus, Sector
from app.models.proposal import Proposal, ProposalStatus, ScoringStatus
from app.models.user import Role, User
from app.services.auth import hash_password
from app.services.pledge import create_pledge, get_locked_proposal
from app.services.scoring import jalankan_scoring

# Jeda kecil setelah lock pertama diambil, sama alasannya dengan
# _RF1_READ_DELAY_S di test_pledge_concurrency.py: tanpanya, Postgres lokal
# yang cepat sering menyelesaikan seluruh loop evaluasi_kedaluwarsa satu
# request sebelum request kedua benar-benar mendapat giliran event loop,
# sehingga jendela balapan yang sebenarnya diuji di sini tidak pernah
# benar-benar tumpang tindih. Ini bukan sleep waktu bisnis (dikendalikan
# Clock); ini jeda penjadwalan yang memaksa interleaving nyata antar dua
# transaksi Postgres yang sungguhan.
_LOCK_DELAY_S = 0.05


@pytest.fixture
def paksa_interleaving_lock(monkeypatch):
    asli = expiry_module.get_locked_proposal

    async def _dengan_delay(session, proposal_id):
        hasil = await asli(session, proposal_id)
        await asyncio.sleep(_LOCK_DELAY_S)
        return hasil

    monkeypatch.setattr(expiry_module, "get_locked_proposal", _dengan_delay)


async def _buat_user_committed(role: Role, label: str) -> User:
    async with SessionLocal() as session:
        user = User(
            email=f"deadlock-{label}-{uuid4().hex}@contoh.id",
            password_hash=hash_password("rahasia123"),
            name=f"Deadlock Test {label}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _hapus_user_committed(user_id) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text("DELETE FROM users WHERE id = :uid"), {"uid": str(user_id)}
        )
        await session.commit()


@pytest.fixture
async def investor():
    user = await _buat_user_committed(Role.INVESTOR, "investor")
    yield user
    await _hapus_user_committed(user.id)


@pytest.fixture
async def investor_pledge():
    user = await _buat_user_committed(Role.INVESTOR, "pledger")
    yield user
    await _hapus_user_committed(user.id)


@pytest.fixture
async def umkm():
    user = await _buat_user_committed(Role.UMKM, "umkm")
    yield user
    await _hapus_user_committed(user.id)


@pytest.fixture
async def umkm_kedua():
    user = await _buat_user_committed(Role.UMKM, "umkm-kedua")
    yield user
    await _hapus_user_committed(user.id)


@pytest.fixture
async def dua_proposal_kedaluwarsa_overlap(investor, investor_pledge, umkm, umkm_kedua):
    """Dua proposal `listed`/`partially_funded` pada campaign yang sama,
    masing-masing dengan satu pledge aktif, yang `total_score`-nya dibalik
    relatif terhadap `created_at`-nya (lihat docstring modul): urutan tampil
    daftar_proposal_publik dan daftar_proposal_campaign jadi berlawanan untuk
    pasangan ini secara spesifik.

    `funding_deadline` campaign dibuat di masa depan dulu supaya create_pledge
    (yang menolak pledge baru setelah deadline lewat) berhasil, baru
    dimundurkan ke masa lalu lewat UPDATE langsung setelah kedua pledge
    tercatat -- bukan assignment proposal.status, jadi tidak kena pagar AST
    yang menolak `proposal.status = ...` di luar domain/transitions.py.
    """
    clock = FrozenClock(SystemClock().now())
    mulai = clock.now()

    async with SessionLocal() as session:
        campaign = Campaign(
            investor_id=investor.id,
            title="Campaign uji deadlock listing",
            description="Mendanai warung kopi skala rumahan." * 2,
            sector=Sector.KULINER,
            target_amount=50_000_000,
            apply_deadline=mulai - timedelta(minutes=10),
            funding_deadline=mulai + timedelta(minutes=10),
            score_threshold=5,
            status=CampaignStatus.OPEN,
            created_at=mulai,
        )
        session.add(campaign)
        await session.flush()

        # p1 dibuat lebih dulu dengan skor TINGGI, p2 belakangan dengan skor
        # RENDAH: daftar_proposal_publik (created_at DESC) menampilkan
        # [p2, p1], daftar_proposal_campaign (total_score DESC) menampilkan
        # [p1, p2] -- urutan lock yang persis berlawanan kalau diambil dalam
        # urutan tampil.
        p1 = Proposal(
            campaign_id=campaign.id,
            umkm_id=umkm.id,
            business_name="Warung Kopi Skor Tinggi",
            business_profile="x" * 110 + " [[SCORE:90]]",
            fund_usage_plan="x" * 110,
            business_projection="x" * 60,
            requested_amount=10_000_000,
            status=ProposalStatus.SUBMITTED,
            scoring_status=ScoringStatus.PENDING,
            created_at=mulai,
        )
        session.add(p1)
        await session.flush()

        p2 = Proposal(
            campaign_id=campaign.id,
            umkm_id=umkm_kedua.id,
            business_name="Warung Kopi Skor Rendah",
            business_profile="x" * 110 + " [[SCORE:10]]",
            fund_usage_plan="x" * 110,
            business_projection="x" * 60,
            requested_amount=10_000_000,
            status=ProposalStatus.SUBMITTED,
            scoring_status=ScoringStatus.PENDING,
            created_at=mulai + timedelta(seconds=1),
        )
        session.add(p2)
        await session.flush()

        await jalankan_scoring(session, p1.id, MockScoringEngine(), clock)
        await jalankan_scoring(session, p2.id, MockScoringEngine(), clock)
        await session.flush()

        proposal1 = await get_locked_proposal(session, p1.id)
        await create_pledge(session, investor_pledge, proposal1, 4_000_000, clock)
        proposal2 = await get_locked_proposal(session, p2.id)
        await create_pledge(session, investor_pledge, proposal2, 4_000_000, clock)
        await session.commit()

        # Memundurkan funding_deadline, bukan menulis status: kolom biasa di
        # luar keempat mesin status, pagar AST tidak menyentuhnya.
        await session.execute(
            text("UPDATE campaigns SET funding_deadline = :t WHERE id = :cid"),
            {"t": mulai - timedelta(minutes=1), "cid": str(campaign.id)},
        )
        await session.commit()

        p1_id, p2_id, campaign_id = p1.id, p2.id, campaign.id

    yield campaign_id, p1_id, p2_id

    async with SessionLocal() as session:
        for table in ("ledger_entries", "pledges", "scoring_results"):
            await session.execute(
                text(f"DELETE FROM {table} WHERE proposal_id IN (:a, :b)"),
                {"a": str(p1_id), "b": str(p2_id)},
            )
        await session.execute(
            text("DELETE FROM proposals WHERE id IN (:a, :b)"),
            {"a": str(p1_id), "b": str(p2_id)},
        )
        await session.execute(
            text("DELETE FROM campaigns WHERE id = :cid"), {"cid": str(campaign_id)}
        )
        await session.commit()


async def _tembak_concurrent(
    campaign_id, jumlah_publik: int, jumlah_campaign: int
) -> list[int]:
    app = create_app()
    # raise_app_exceptions=False: default httpx menangkap exception yang
    # tidak tertangkap handler FastAPI lalu melemparnya balik ke pemanggil
    # test, bukan mengembalikan response 500 apa adanya. Yang diuji di sini
    # justru respons 500 sungguhan yang akan diterima klien HTTP nyata.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        async def publik():
            r = await client.get("/api/v1/proposals")
            return r.status_code

        async def per_campaign():
            r = await client.get(f"/api/v1/campaigns/{campaign_id}/proposals")
            return r.status_code

        tugas = [publik() for _ in range(jumlah_publik)] + [
            per_campaign() for _ in range(jumlah_campaign)
        ]
        return await asyncio.gather(*tugas)


async def test_r61_concurrent_anonymous_listing_does_not_deadlock(
    dua_proposal_kedaluwarsa_overlap, paksa_interleaving_lock
):
    """Finding 1: 24 GET anonim bersamaan ke dua endpoint listing publik,
    menyentuh dua proposal kedaluwarsa yang overlap dan dilock berlawanan
    arah di urutan tampil masing-masing, tidak boleh pernah menghasilkan
    500 -- sebelum perbaikan ini pernah merah dengan 40P01 sungguhan
    (lihat laporan hardening untuk angka reproduksinya)."""
    campaign_id, p1_id, p2_id = dua_proposal_kedaluwarsa_overlap

    status_list = await _tembak_concurrent(campaign_id, jumlah_publik=12, jumlah_campaign=12)

    gagal = [s for s in status_list if s >= 500]
    assert gagal == [], f"{len(gagal)} dari {len(status_list)} request gagal 500: {gagal}"

    async with SessionLocal() as session:
        p1 = await session.get(Proposal, p1_id)
        p2 = await session.get(Proposal, p2_id)
        await session.refresh(p1)
        await session.refresh(p2)
        assert p1.status is ProposalStatus.FAILED
        assert p2.status is ProposalStatus.FAILED

        aktif = (
            await session.execute(
                text(
                    "SELECT count(*) FROM pledges WHERE proposal_id IN (:a, :b) "
                    "AND status = 'active'"
                ),
                {"a": str(p1_id), "b": str(p2_id)},
            )
        ).scalar()
        assert aktif == 0, "R4: proposal failed tidak boleh memegang pledge aktif"

        refund_rows = (
            await session.execute(
                text(
                    "SELECT count(*) FROM ledger_entries WHERE proposal_id IN (:a, :b) "
                    "AND entry_type = 'refund_out'"
                ),
                {"a": str(p1_id), "b": str(p2_id)},
            )
        ).scalar()
        assert refund_rows == 2, "BR-62: setiap pledge aktif harus mendapat refund_out"

"""RF-1: dua pledge bersamaan pada sisa yang sama.

Test ini memakai dua sesi database sungguhan, bukan fixture `db` yang
di-rollback, karena yang diuji adalah perilaku penguncian antar transaksi:
fixture `db` membungkus semuanya dalam satu transaksi, yang membuat
`with_for_update()` tidak pernah benar-benar berebut lock dengan siapa pun.
"""

import asyncio
import contextlib
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.ai.mock_engine import MockScoringEngine
from app.db.session import SessionLocal
from app.domain.clock import FrozenClock, SystemClock
from app.errors import ConflictError
from app.models.campaign import Campaign, CampaignStatus, Sector
from app.models.proposal import Proposal, ProposalStatus, ScoringStatus
from app.models.user import Role, User
from app.services import pledge as pledge_service
from app.services.auth import hash_password
from app.services.ledger import collected_amount_for_proposal
from app.services.pledge import create_pledge, get_locked_proposal
from app.services.scoring import run_scoring

# Review menemukan RF-1 lolos byte-identik setelah with_for_update() dihapus
# dari get_locked_proposal: asyncio.gather(attempt(a), attempt(b)) terlihat
# konkuren tapi di Postgres lokal yang cepat, coroutine pertama kerap
# menyelesaikan seluruh create_pledge (baca remaining, tulis pledge, commit)
# sebelum event loop pernah memberi giliran ke coroutine kedua -- jendela
# baca-remaining-lalu-tulis yang sebenarnya diuji RF-1 tidak pernah benar-
# benar tumpang tindih. _RF1_READ_DELAY_S memaksa jendela itu terbuka lebar
# di DUA sisi secara simetris (bukan memenangkan salah satu), lewat
# asyncio.sleep SETELAH baca remaining tapi SEBELUM keputusan tulis.
#
# Ini bukan sleep waktu bisnis yang dilarang skill testing-and-regression
# (itu dikendalikan FrozenClock) -- ini jeda penjadwalan event loop yang
# memaksa interleaving nyata, satu-satunya cara membuktikan sebuah lock
# baris database benar-benar bekerja tanpa thread/proses OS sungguhan.
# Kalau with_for_update() aktif, delay ini terjadi SAMBIL baris masih
# terkunci -- lawannya menunggu di level Postgres, bukan di barrier Python,
# jadi tidak ada risiko deadlock menunggu lawan yang belum pernah berjalan.
_RF1_READ_DELAY_S = 0.05


@pytest.fixture
def paksa_interleaving_baca_remaining(monkeypatch):
    """Lihat komentar modul di atas: menyisipkan jeda tepat setelah
    collected_amount_for_proposal (baca "sisa dana") dikembalikan ke create_pledge,
    sebelum create_pledge memutuskan menulis pledge atau menolak."""
    asli = pledge_service.collected_amount_for_proposal

    async def _dengan_delay(session, proposal_id):
        hasil = await asli(session, proposal_id)
        await asyncio.sleep(_RF1_READ_DELAY_S)
        return hasil

    monkeypatch.setattr(pledge_service, "collected_amount_for_proposal", _dengan_delay)


async def _create_committed_user(role: Role, label: str) -> User:
    async with SessionLocal() as session:
        user = User(
            email=f"concurrency-{label}-{uuid4().hex}@contoh.id",
            password_hash=hash_password("rahasia123"),
            name=f"Concurrency Test User {label}",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _delete_committed_user(user_id) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text("DELETE FROM users WHERE id = :uid"), {"uid": str(user_id)}
        )
        await session.commit()


@pytest.fixture
async def investor_a():
    user = await _create_committed_user(Role.INVESTOR, "a")
    yield user
    await _delete_committed_user(user.id)


@pytest.fixture
async def investor_b():
    user = await _create_committed_user(Role.INVESTOR, "b")
    yield user
    await _delete_committed_user(user.id)


@pytest.fixture
def clock():
    return FrozenClock(SystemClock().now())


@pytest.fixture
async def listed_proposal_committed(investor_a, investor_b, clock):
    """Proposal `listed` sungguhan, ter-commit ke Postgres lewat SessionLocal
    terpisah (bukan fixture `db`), sehingga terlihat dari dua sesi lain yang
    dibuka test ini secara konkuren.

    Menerima investor_b sebagai parameter meski campaign di bawah hanya
    dimiliki investor_a: salah satu dari mereka akan jadi lead_investor
    (BR-23) setelah race test berjalan, dan pytest membongkar fixture
    persis kebalik urutan setup-nya. Tanpa investor_b di sini, fixture itu
    dibongkar (dihapus dari tabel users) sebelum fixture ini sempat
    menghapus baris proposals yang masih merujuknya lewat lead_investor_id,
    dan DELETE itu gagal kena foreign key constraint.
    """
    umkm = await _create_committed_user(Role.UMKM, "applicant")
    started_at = clock.now()
    async with SessionLocal() as session:
        campaign = Campaign(
            investor_id=investor_a.id,
            title="Campaign uji konkurensi pledge",
            description="Mendanai warung kopi skala rumahan." * 2,
            sector=Sector.KULINER,
            target_amount=50_000_000,
            apply_deadline=started_at + timedelta(days=7),
            funding_deadline=started_at + timedelta(days=21),
            score_threshold=60,
            status=CampaignStatus.OPEN,
            created_at=started_at,
        )
        session.add(campaign)
        await session.flush()

        proposal = Proposal(
            campaign_id=campaign.id,
            umkm_id=umkm.id,
            business_name="Warung Kopi Uji Konkurensi",
            business_profile="x" * 110 + " [[SCORE:80]]",  # threshold campaign 60
            fund_usage_plan="x" * 110,
            business_projection="x" * 60,
            requested_amount=10_000_000,
            status=ProposalStatus.SUBMITTED,
            scoring_status=ScoringStatus.PENDING,
            created_at=started_at,
        )
        session.add(proposal)
        await session.flush()
        await run_scoring(session, proposal.id, MockScoringEngine(), clock)
        await session.commit()
        await session.refresh(proposal)

    yield proposal

    async with SessionLocal() as session:
        # ledger_entries sekarang punya trigger append-only (review keamanan
        # Finding 3): DELETE biasa ditolak database. SET LOCAL ini adalah
        # escape hatch yang hanya dipakai infrastruktur test, tidak pernah
        # oleh kode aplikasi, supaya teardown data uji tetap bisa membersihkan
        # baris yang dibuat test ini sendiri lewat commit sungguhan.
        await session.execute(text("SET LOCAL modalink.ledger_cleanup_override = 'on'"))
        for table in (
            "ledger_entries",
            "pledges",
            "scoring_results",
            "proposal_milestones",
        ):
            await session.execute(
                text(f"DELETE FROM {table} WHERE proposal_id = :pid"),
                {"pid": str(proposal.id)},
            )
        await session.execute(
            text("DELETE FROM proposals WHERE id = :pid"), {"pid": str(proposal.id)}
        )
        await session.execute(
            text("DELETE FROM campaigns WHERE investor_id = :iid"),
            {"iid": str(investor_a.id)},
        )
        await session.commit()
    await _delete_committed_user(umkm.id)


async def test_rf1_concurrent_pledges_do_not_exceed_target(
    listed_proposal_committed,
    investor_a,
    investor_b,
    clock,
    paksa_interleaving_baca_remaining,
):
    remaining = listed_proposal_committed.requested_amount  # belum ada pledge

    async def attempt(investor):
        async with SessionLocal() as session, session.begin():
            proposal = await get_locked_proposal(session, listed_proposal_committed.id)
            try:
                await create_pledge(session, investor, proposal, remaining, clock)
                return "succeeded"
            except ConflictError:
                return "rejected"

    outcomes = await asyncio.gather(attempt(investor_a), attempt(investor_b))
    assert sorted(outcomes) == ["rejected", "succeeded"]

    async with SessionLocal() as session:
        total = await collected_amount_for_proposal(
            session, listed_proposal_committed.id
        )
    assert total == remaining  # R2: dana terkumpul tidak pernah melebihi yang diminta


async def test_rf1_total_pledged_never_exceeds_requested_amount(
    listed_proposal_committed,
    investor_a,
    investor_b,
    clock,
    paksa_interleaving_baca_remaining,
):
    # Sengaja lebih dari separuh: dua pledge nilai ini sekaligus pasti melebihi target.
    half_plus = listed_proposal_committed.requested_amount // 2 + 1_000_000

    async def attempt(investor):
        async with SessionLocal() as session, session.begin():
            proposal = await get_locked_proposal(session, listed_proposal_committed.id)
            with contextlib.suppress(ConflictError):
                await create_pledge(session, investor, proposal, half_plus, clock)

    await asyncio.gather(attempt(investor_a), attempt(investor_b))

    async with SessionLocal() as session:
        total = await collected_amount_for_proposal(
            session, listed_proposal_committed.id
        )
    assert total <= listed_proposal_committed.requested_amount

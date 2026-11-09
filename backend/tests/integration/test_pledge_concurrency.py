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
from app.services.auth import hash_password
from app.services.ledger import total_terkumpul_proposal
from app.services.pledge import create_pledge, get_locked_proposal
from app.services.scoring import jalankan_scoring


async def _buat_user_committed(role: Role, label: str) -> User:
    async with SessionLocal() as sesi:
        user = User(
            email=f"concurrency-{label}-{uuid4().hex}@contoh.id",
            password_hash=hash_password("rahasia123"),
            name=f"Pengguna Uji Konkurensi {label}",
            role=role,
        )
        sesi.add(user)
        await sesi.commit()
        await sesi.refresh(user)
        return user


async def _hapus_user_committed(user_id) -> None:
    async with SessionLocal() as sesi:
        await sesi.execute(
            text("DELETE FROM users WHERE id = :uid"), {"uid": str(user_id)}
        )
        await sesi.commit()


@pytest.fixture
async def investor_a():
    user = await _buat_user_committed(Role.INVESTOR, "a")
    yield user
    await _hapus_user_committed(user.id)


@pytest.fixture
async def investor_b():
    user = await _buat_user_committed(Role.INVESTOR, "b")
    yield user
    await _hapus_user_committed(user.id)


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
    umkm = await _buat_user_committed(Role.UMKM, "pengaju")
    mulai = clock.now()
    async with SessionLocal() as sesi:
        campaign = Campaign(
            investor_id=investor_a.id,
            title="Campaign uji konkurensi pledge",
            description="Mendanai warung kopi skala rumahan." * 2,
            sector=Sector.KULINER,
            target_amount=50_000_000,
            apply_deadline=mulai + timedelta(days=7),
            funding_deadline=mulai + timedelta(days=21),
            score_threshold=60,
            status=CampaignStatus.OPEN,
            created_at=mulai,
        )
        sesi.add(campaign)
        await sesi.flush()

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
            created_at=mulai,
        )
        sesi.add(proposal)
        await sesi.flush()
        await jalankan_scoring(sesi, proposal.id, MockScoringEngine(), clock)
        await sesi.commit()
        await sesi.refresh(proposal)

    yield proposal

    async with SessionLocal() as sesi:
        for tabel in (
            "ledger_entries",
            "pledges",
            "scoring_results",
            "proposal_milestones",
        ):
            await sesi.execute(
                text(f"DELETE FROM {tabel} WHERE proposal_id = :pid"),
                {"pid": str(proposal.id)},
            )
        await sesi.execute(
            text("DELETE FROM proposals WHERE id = :pid"), {"pid": str(proposal.id)}
        )
        await sesi.execute(
            text("DELETE FROM campaigns WHERE investor_id = :iid"),
            {"iid": str(investor_a.id)},
        )
        await sesi.commit()
    await _hapus_user_committed(umkm.id)


async def test_rf1_concurrent_pledges_do_not_exceed_target(
    listed_proposal_committed, investor_a, investor_b, clock
):
    sisa = listed_proposal_committed.requested_amount  # belum ada pledge

    async def coba(investor):
        async with SessionLocal() as sesi, sesi.begin():
            proposal = await get_locked_proposal(sesi, listed_proposal_committed.id)
            try:
                await create_pledge(sesi, investor, proposal, sisa, clock)
                return "lolos"
            except ConflictError:
                return "ditolak"

    hasil = await asyncio.gather(coba(investor_a), coba(investor_b))
    assert sorted(hasil) == ["ditolak", "lolos"]


async def test_rf1_total_pledged_never_exceeds_requested_amount(
    listed_proposal_committed, investor_a, investor_b, clock
):
    separuh = (
        listed_proposal_committed.requested_amount // 2 + 1_000_000
    )  # sengaja > separuh

    async def coba(investor):
        async with SessionLocal() as sesi, sesi.begin():
            proposal = await get_locked_proposal(sesi, listed_proposal_committed.id)
            with contextlib.suppress(ConflictError):
                await create_pledge(sesi, investor, proposal, separuh, clock)

    await asyncio.gather(coba(investor_a), coba(investor_b))

    async with SessionLocal() as sesi:
        total = await total_terkumpul_proposal(sesi, listed_proposal_committed.id)
    assert total <= listed_proposal_committed.requested_amount

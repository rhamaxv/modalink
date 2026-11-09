"""RF-5: approve milestone dikirim dua kali nyaris bersamaan.

Sama seperti test_pledge_concurrency.py (RF-1): dua sesi database sungguhan,
bukan fixture `db` yang di-rollback, karena yang diuji adalah `with_for_update()`
benar-benar berebut lock antar transaksi konkuren. Fixture `db` membungkus
semuanya dalam satu transaksi, yang membuat dua pemanggil tidak pernah
benar-benar bersaing untuk baris proposal yang sama.
"""

import asyncio
import contextlib
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text

from app.ai.mock_engine import MockScoringEngine
from app.db.session import SessionLocal
from app.domain.clock import FrozenClock, SystemClock
from app.models.campaign import Campaign, CampaignStatus, Sector
from app.models.ledger import EntryType, LedgerEntry
from app.models.proposal import (
    Proposal,
    ProposalMilestone,
    ProposalStatus,
    ScoringStatus,
)
from app.models.user import Role, User
from app.schemas.milestone import MilestoneReportIn
from app.services.auth import hash_password
from app.services.milestone import approve_milestone, submit_report
from app.services.pledge import create_pledge, get_locked_proposal
from app.services.scoring import jalankan_scoring


async def _create_committed_user(role: Role, label: str) -> User:
    async with SessionLocal() as session:
        user = User(
            email=f"approve-race-{label}-{uuid4().hex}@contoh.id",
            password_hash=hash_password("rahasia123"),
            name=f"Approve Race Test User {label}",
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
async def lead():
    user = await _create_committed_user(Role.INVESTOR, "lead")
    yield user
    await _delete_committed_user(user.id)


@pytest.fixture
def clock():
    return FrozenClock(SystemClock().now())


@pytest.fixture
async def funded_proposal_tercommit(lead, clock):
    """Proposal `funded` sungguhan, ter-commit ke Postgres lewat SessionLocal
    terpisah, dengan dua milestone yang jumlahnya persis sama dengan
    requested_amount. `lead` sekaligus pemilik campaign dan satu-satunya
    pledger, sama seperti funded_proposal di tests/conftest.py, supaya ia
    otomatis jadi lead investor (BR-23) tanpa pledge kedua yang tidak perlu.
    """
    umkm = await _create_committed_user(Role.UMKM, "applicant")
    started_at = clock.now()
    async with SessionLocal() as session:
        campaign = Campaign(
            investor_id=lead.id,
            title="Campaign uji approve bersamaan",
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
            business_name="Warung Kopi Uji Approve Bersamaan",
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
        await jalankan_scoring(session, proposal.id, MockScoringEngine(), clock)

        for seq, judul in ((1, "Beli mesin"), (2, "Bahan baku")):
            session.add(
                ProposalMilestone(
                    proposal_id=proposal.id,
                    seq=seq,
                    title=judul,
                    description="x" * 20,
                    amount=proposal.requested_amount // 2,
                )
            )
        await session.flush()

        locked = await get_locked_proposal(session, proposal.id)
        await create_pledge(session, lead, locked, locked.requested_amount, clock)
        await session.commit()
        await session.refresh(proposal)

        milestones = (
            await session.scalars(
                select(ProposalMilestone)
                .where(ProposalMilestone.proposal_id == proposal.id)
                .order_by(ProposalMilestone.seq)
            )
        ).all()

    yield proposal, list(milestones)

    async with SessionLocal() as session:
        # ledger_entries sekarang punya trigger append-only (review keamanan
        # Finding 3): DELETE biasa ditolak database. SET LOCAL ini adalah
        # escape hatch yang hanya dipakai infrastruktur test, tidak pernah
        # oleh kode aplikasi, supaya teardown data uji tetap bisa membersihkan
        # baris yang dibuat test ini sendiri lewat commit sungguhan.
        await session.execute(
            text("SET LOCAL modalink.ledger_cleanup_override = 'on'")
        )
        # milestone_reports tidak punya kolom proposal_id (hanya milestone_id),
        # jadi dihapus lewat subquery, lebih dulu dari proposal_milestones yang
        # jadi induknya (FK milestone_reports.milestone_id).
        await session.execute(
            text(
                "DELETE FROM milestone_reports WHERE milestone_id IN "
                "(SELECT id FROM proposal_milestones WHERE proposal_id = :pid)"
            ),
            {"pid": str(proposal.id)},
        )
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
            {"iid": str(lead.id)},
        )
        await session.commit()
    await _delete_committed_user(umkm.id)


async def _total_disbursement(session, proposal_id) -> int:
    total = await session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.proposal_id == proposal_id,
            LedgerEntry.entry_type == EntryType.DISBURSEMENT_OUT,
        )
    )
    return int(total or 0)


async def test_rf5_double_concurrent_approve_produces_only_one_disbursement(
    funded_proposal_tercommit, lead, clock
):
    _proposal, milestones = funded_proposal_tercommit
    m1 = milestones[0]

    async def approve():
        async with SessionLocal() as sesi, sesi.begin():
            with contextlib.suppress(Exception):
                milestone = await sesi.get(ProposalMilestone, m1.id)
                await approve_milestone(sesi, milestone, lead, clock)

    await asyncio.gather(approve(), approve())

    async with SessionLocal() as sesi:
        entri = (
            await sesi.scalars(
                select(LedgerEntry).where(
                    LedgerEntry.ref_id == m1.id,
                    LedgerEntry.entry_type == EntryType.DISBURSEMENT_OUT,
                )
            )
        ).all()
    assert len(entri) == 1, "approve ganda menghasilkan dua pencairan"


async def test_rf5_double_concurrent_approve_on_last_milestone_completes_proposal_once(
    funded_proposal_tercommit, lead, clock
):
    proposal, milestones = funded_proposal_tercommit
    m1, m2 = milestones

    async with SessionLocal() as sesi, sesi.begin():
        milestone = await sesi.get(ProposalMilestone, m1.id)
        await approve_milestone(sesi, milestone, lead, clock)

    async with SessionLocal() as sesi, sesi.begin():
        milestone = await sesi.get(ProposalMilestone, m2.id)
        umkm = await sesi.get(User, proposal.umkm_id)
        await submit_report(
            sesi,
            umkm,
            milestone,
            MilestoneReportIn(narrative="x" * 60, metrics=None),
            clock,
        )

    async def approve():
        async with SessionLocal() as sesi, sesi.begin():
            with contextlib.suppress(Exception):
                milestone = await sesi.get(ProposalMilestone, m2.id)
                await approve_milestone(sesi, milestone, lead, clock)

    await asyncio.gather(approve(), approve())

    async with SessionLocal() as sesi:
        hasil = await sesi.get(Proposal, proposal.id)
        cair = await _total_disbursement(sesi, proposal.id)
    assert hasil is not None
    assert hasil.status is ProposalStatus.COMPLETED
    assert cair == proposal.requested_amount  # bukan dua kali lipat

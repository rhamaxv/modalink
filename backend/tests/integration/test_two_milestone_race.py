"""RF-6: dua milestone BERBEDA pada proposal yang sama, di-approve nyaris
bersamaan.

Beda dari RF-5 (test_concurrent_approve.py), yang membuktikan approve ganda
pada SATU milestone yang sama aman murni lewat `idempotency_key` unik
`disburse:{milestone_id}` -- aman apa pun nasib `with_for_update()` di
`get_locked_proposal`, karena constraint unik Postgres menjaganya terlepas
dari lock baris.

Dua milestone berbeda menulis dua `idempotency_key` berbeda, jadi constraint
unik itu tidak menyelamatkan apa pun di sini. Kalau *disbursement_precondition*
memutuskan "cukup dana" dari sesuatu yang dibaca lalu ditulis tanpa lock,
dua milestone bisa sama-sama lolos dan bersama-sama mencairkan lebih dari
yang pernah terkumpul -- uang keluar dari escrow dua kali lipat.

Fixture di bawah memaksa m2 ke status `reported` dengan laporan `pending`
lewat INSERT langsung (bukan lewat submit_report), SEBELUM m1 cair. Keadaan
ini tidak pernah tercapai lewat API sungguhan -- can_be_reported mewajibkan
m1 `disbursed` dulu (BR-43) -- dan itu sengaja: tujuannya mengisolasi pagar
*pencairan* (disbursement_precondition di approve_milestone) dari pagar
*pelaporan* (can_be_reported di submit_report), supaya race ini menguji
pagar pencairan sendirian, bukan tertahan lebih dulu oleh pagar pelaporan
yang sudah diuji terpisah (BR-43, test_milestone_lapor.py).
"""

import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from dokumen_uji import dokumen_untuk
from sqlalchemy import func, select, text

from app.ai.mock_engine import MockScoringEngine
from app.db.session import SessionLocal
from app.domain.clock import FrozenClock, SystemClock
from app.models.campaign import Campaign, CampaignStatus, Sector
from app.models.ledger import EntryType, LedgerEntry
from app.models.milestone_report import MilestoneReport, ReportStatus
from app.models.proposal import (
    MilestoneStatus,
    Proposal,
    ProposalMilestone,
    ProposalStatus,
    ScoringStatus,
)
from app.models.user import Role, User
from app.services.auth import hash_password
from app.services.milestone import approve_milestone
from app.services.pledge import create_pledge, get_locked_proposal
from app.services.scoring import run_scoring

AMOUNT_M1 = 5_000_000
AMOUNT_M2 = 5_000_000
REQUESTED_AMOUNT = AMOUNT_M1 + AMOUNT_M2


async def _create_committed_user(role: Role, label: str) -> User:
    async with SessionLocal() as session:
        user = User(
            email=f"two-milestone-race-{label}-{uuid4().hex}@contoh.id",
            password_hash=hash_password("rahasia123"),
            name=f"Two Milestone Race Test User {label}",
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


async def _buat_proposal_siap_race(
    lead: User, clock
) -> tuple[Proposal, list[ProposalMilestone]]:
    """Proposal `funded` sungguhan dengan m1 `pending` (belum cair) dan m2
    `reported` dengan laporan `pending` dipaksa ada lewat INSERT langsung
    (lihat docstring modul ini). Dipanggil berulang, satu proposal baru per
    percobaan: milestone jadi status terminal setelah satu kali approve,
    jadi tidak bisa dipakai ulang untuk mengukur banyak percobaan."""
    umkm = await _create_committed_user(Role.UMKM, "applicant")
    started_at = clock.now()
    async with SessionLocal() as session:
        campaign = Campaign(
            investor_id=lead.id,
            title="Campaign uji race dua milestone",
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
            business_name="Warung Kopi Uji Race Dua Milestone",
            business_summary="x" * 40,
            requested_amount=REQUESTED_AMOUNT,
            status=ProposalStatus.SUBMITTED,
            scoring_status=ScoringStatus.PENDING,
            created_at=started_at,
        )
        session.add(proposal)
        # Penanda skor tinggal di dokumen, bukan di kolom proposals: di
        # situlah mesin skoring membacanya sekarang.
        session.add(dokumen_untuk(proposal, "x" * 110 + " [[SCORE:80]]"))
        await session.flush()
        await run_scoring(session, proposal.id, MockScoringEngine(), clock)

        m1 = ProposalMilestone(
            proposal_id=proposal.id,
            seq=1,
            title="Beli mesin",
            description="x" * 20,
            amount=AMOUNT_M1,
            status=MilestoneStatus.PENDING,
        )
        m2 = ProposalMilestone(
            proposal_id=proposal.id,
            seq=2,
            title="Bahan baku",
            description="x" * 20,
            amount=AMOUNT_M2,
            # Dipaksa reported di sini, bukan lewat submit_report: lihat
            # docstring modul ini soal kenapa ini pelanggaran prasyarat yang
            # disengaja.
            status=MilestoneStatus.REPORTED,
        )
        session.add_all([m1, m2])
        await session.flush()

        session.add(
            MilestoneReport(
                milestone_id=m2.id,
                umkm_id=umkm.id,
                narrative="x" * 60,
                review_status=ReportStatus.PENDING,
                submitted_at=clock.now(),
            )
        )
        await session.flush()

        locked = await get_locked_proposal(session, proposal.id)
        await create_pledge(session, lead, locked, REQUESTED_AMOUNT, clock)
        await session.commit()
        await session.refresh(proposal)
        await session.refresh(m1)
        await session.refresh(m2)

    return proposal, [m1, m2]


async def _bersihkan_proposal(proposal_id, lead_id) -> None:
    async with SessionLocal() as session:
        # ledger_entries sekarang punya trigger append-only (review keamanan
        # Finding 3): DELETE biasa ditolak database. SET LOCAL ini adalah
        # escape hatch yang hanya dipakai infrastruktur test, tidak pernah
        # oleh kode aplikasi, supaya teardown data uji tetap bisa membersihkan
        # baris yang dibuat test ini sendiri lewat commit sungguhan.
        await session.execute(text("SET LOCAL modalink.ledger_cleanup_override = 'on'"))
        await session.execute(
            text(
                "DELETE FROM milestone_reports WHERE milestone_id IN "
                "(SELECT id FROM proposal_milestones WHERE proposal_id = :pid)"
            ),
            {"pid": str(proposal_id)},
        )
        for table in (
            "ledger_entries",
            "pledges",
            "scoring_results",
            "proposal_milestones",
        ):
            await session.execute(
                text(f"DELETE FROM {table} WHERE proposal_id = :pid"),
                {"pid": str(proposal_id)},
            )
        await session.execute(
            text("DELETE FROM proposals WHERE id = :pid"), {"pid": str(proposal_id)}
        )
        await session.execute(
            text("DELETE FROM campaigns WHERE investor_id = :iid"),
            {"iid": str(lead_id)},
        )
        await session.commit()


async def _total_disbursement(session, proposal_id) -> int:
    total = await session.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.proposal_id == proposal_id,
            LedgerEntry.entry_type == EntryType.DISBURSEMENT_OUT,
        )
    )
    return int(total or 0)


async def _race_satu_percobaan(lead: User, clock) -> dict:
    """Satu percobaan: proposal baru, lalu approve(m1) dan approve(m2)
    ditembakkan bersamaan lewat asyncio.gather pada dua sesi Postgres
    terpisah (bukan fixture `db` yang di-rollback -- lihat docstring
    test_pledge_concurrency.py untuk alasannya). Mengembalikan ringkasan
    hasil untuk ditabulasi pemanggil, bukan assert langsung di sini: satu
    percobaan tidak informatif sendirian, totalnya baru bermakna setelah
    N percobaan (lihat test_rf6 di bawah)."""
    proposal, (m1, m2) = await _buat_proposal_siap_race(lead, clock)

    async def approve(milestone: ProposalMilestone) -> str:
        async with SessionLocal() as sesi, sesi.begin():
            try:
                segar = await sesi.get(ProposalMilestone, milestone.id)
                await approve_milestone(sesi, segar, lead, clock)
                return "disbursed"
            except Exception:  # noqa: BLE001 -- apa pun penyebabnya dicatat, bukan ditelan
                return "rejected"

    hasil_m1, hasil_m2 = await asyncio.gather(approve(m1), approve(m2))

    async with SessionLocal() as sesi:
        total_cair = await _total_disbursement(sesi, proposal.id)

    await _bersihkan_proposal(proposal.id, lead.id)

    return {
        "m1": hasil_m1,
        "m2": hasil_m2,
        "total_cair": total_cair,
        "over_disbursement": total_cair > REQUESTED_AMOUNT,
    }


JUMLAH_PERCOBAAN = 30


async def test_rf6_two_different_milestones_approved_concurrently_never_overdisbursed(
    lead, clock
):
    """Menjalankan race N kali terhadap kode SEKARANG (dengan
    `with_for_update()` masih terpasang di get_locked_proposal) dan mencatat
    berapa kali total yang cair melebihi requested_amount.

    Tidak boleh pernah terjadi -- kalau pernah, itu bug nyata yang memang
    harus membuat test ini merah, bukan sesuatu yang di-suppress."""
    over_disbursement_count = 0
    ringkasan = []
    for _ in range(JUMLAH_PERCOBAAN):
        hasil = await _race_satu_percobaan(lead, clock)
        ringkasan.append(hasil)
        if hasil["over_disbursement"]:
            over_disbursement_count += 1

    assert over_disbursement_count == 0, (
        f"over-disbursement terjadi {over_disbursement_count}/{JUMLAH_PERCOBAAN} "
        f"kali dengan lock masih terpasang: {ringkasan}"
    )
    for hasil in ringkasan:
        assert hasil["total_cair"] <= REQUESTED_AMOUNT

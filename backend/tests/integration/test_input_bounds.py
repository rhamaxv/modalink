"""Lapisan database di belakang batas Pydantic (Task 3 review keamanan).

Setiap test di sini menyusun baris langsung lewat `db.add(...)`, melompati
skema HTTP sama sekali -- sama seperti
`test_br33_database_check_also_rejects_comment_over_500` di test_comment.py,
yang jadi pola acuannya. Tanpa CHECK constraint ini, pemanggil yang tidak
lewat ProposalIn/MilestoneReportIn/MilestoneRejectIn/RegisterIn (fixture
test lain, migrasi data, service yang lupa lewat skema) bisa menulis baris
yang melanggar batas yang sama tanpa satu pun error.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.clock import SystemClock
from app.models.milestone_report import MilestoneReport, ReportStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.user import Role, User


async def test_t3_database_check_rejects_business_profile_over_5000(
    db, campaign, umkm_lain
):
    db.add(
        Proposal(
            campaign_id=campaign.id,
            umkm_id=umkm_lain.user.id,
            business_name="Warung Uji CHECK",
            business_profile="x" * 5_001,
            fund_usage_plan="x" * 100,
            business_projection="x" * 50,
            requested_amount=10_000_000,
            status=ProposalStatus.SUBMITTED,
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_t3_database_check_rejects_fund_usage_plan_over_5000(
    db, campaign, umkm_lain
):
    db.add(
        Proposal(
            campaign_id=campaign.id,
            umkm_id=umkm_lain.user.id,
            business_name="Warung Uji CHECK",
            business_profile="x" * 100,
            fund_usage_plan="x" * 5_001,
            business_projection="x" * 50,
            requested_amount=10_000_000,
            status=ProposalStatus.SUBMITTED,
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_t3_database_check_rejects_business_projection_over_3000(
    db, campaign, umkm_lain
):
    db.add(
        Proposal(
            campaign_id=campaign.id,
            umkm_id=umkm_lain.user.id,
            business_name="Warung Uji CHECK",
            business_profile="x" * 100,
            fund_usage_plan="x" * 100,
            business_projection="x" * 3_001,
            requested_amount=10_000_000,
            status=ProposalStatus.SUBMITTED,
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_t3_database_check_rejects_milestone_report_narrative_over_5000(
    db, umkm_lain, funded_proposal
):
    m2 = funded_proposal.milestones[1]
    db.add(
        MilestoneReport(
            milestone_id=m2.id,
            umkm_id=umkm_lain.user.id,
            narrative="x" * 5_001,
            review_status=ReportStatus.PENDING,
            submitted_at=SystemClock().now(),
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_t3_database_check_allows_null_reviewer_note(
    db, umkm_lain, funded_proposal
):
    """CHECK reviewer_note harus tetap meloloskan NULL: field ini hanya
    wajib diisi saat laporan ditolak (BR-45), bukan setiap baris."""
    m2 = funded_proposal.milestones[1]
    db.add(
        MilestoneReport(
            milestone_id=m2.id,
            umkm_id=umkm_lain.user.id,
            narrative="x" * 60,
            review_status=ReportStatus.PENDING,
            reviewer_note=None,
            submitted_at=SystemClock().now(),
        )
    )
    await db.flush()  # tidak boleh melempar


async def test_t3_database_check_rejects_reviewer_note_over_2000(
    db, umkm_lain, funded_proposal
):
    m2 = funded_proposal.milestones[1]
    db.add(
        MilestoneReport(
            milestone_id=m2.id,
            umkm_id=umkm_lain.user.id,
            narrative="x" * 60,
            review_status=ReportStatus.REJECTED,
            reviewer_note="x" * 2_001,
            submitted_at=SystemClock().now(),
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_t3_database_check_rejects_user_name_over_120(db):
    db.add(
        User(
            email="nama-panjang-db@contoh.id",
            password_hash="hash-tidak-relevan-di-test-ini",
            name="x" * 121,
            role=Role.UMKM,
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()

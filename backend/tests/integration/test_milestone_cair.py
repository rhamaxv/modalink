"""Pencairan milestone sungguhan: entri ledger dan transisi proposal ke
`completed` saat milestone terakhir cair (BR-47, BR-48, T-09, T-21, D-13).
"""

from sqlalchemy import func
from sqlmodel import select

from app.models.ledger import EntryType, LedgerEntry

# Enum kolom database (app.models.proposal), bukan enum mesin transisi
# (app.domain.transitions): m1.status dan funded_proposal.proposal.status
# adalah nilai kolom sungguhan, dan membandingkannya dengan `is` terhadap
# kelas enum yang berbeda selalu False tanpa error (lihat docstring
# app/services/status.py; brief f07-b.md Task 3 justru salah mengimpor dari
# domain/transitions.py di sini, persis jebakan yang dicatat Task 0).
from app.models.proposal import MilestoneStatus as M
from app.models.proposal import ProposalStatus as S


async def test_d13_first_milestone_disburses_without_report_after_approve(
    client, db, investor, funded_proposal
):
    m1 = funded_proposal.milestones[0]
    res = await client.post(
        f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers
    )
    assert res.status_code == 200
    await db.refresh(m1)
    assert m1.status is M.DISBURSED


async def test_br47_approve_records_disbursement_of_milestone_amount(
    client, db, investor, funded_proposal
):
    m1 = funded_proposal.milestones[0]
    await client.post(f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers)
    entri = (
        await db.scalars(
            select(LedgerEntry).where(
                LedgerEntry.proposal_id == funded_proposal.id,
                LedgerEntry.entry_type == EntryType.DISBURSEMENT_OUT,
            )
        )
    ).all()
    assert len(entri) == 1
    assert entri[0].amount == m1.amount
    assert entri[0].idempotency_key == f"disburse:{m1.id}"


async def test_t09_last_milestone_disbursed_marks_proposal_completed(
    client, db, umkm_lain, investor, funded_proposal
):
    m1, m2 = funded_proposal.milestones
    await client.post(f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers)
    await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json={"narrative": "x" * 60, "metrics": None},
    )
    res = await client.post(
        f"/api/v1/milestones/{m2.id}/approve", headers=investor.headers
    )
    assert res.status_code == 200

    await db.refresh(funded_proposal.proposal)
    assert funded_proposal.proposal.status is S.COMPLETED


async def test_total_disbursed_equals_requested_amount_once_all_milestones_disburse(
    client, db, umkm_lain, investor, funded_proposal
):
    m1, m2 = funded_proposal.milestones
    await client.post(f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers)
    await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json={"narrative": "x" * 60, "metrics": None},
    )
    await client.post(f"/api/v1/milestones/{m2.id}/approve", headers=investor.headers)

    cair = await db.scalar(
        select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.proposal_id == funded_proposal.id,
            LedgerEntry.entry_type == EntryType.DISBURSEMENT_OUT,
        )
    )
    assert cair == funded_proposal.requested_amount


async def test_br48_duplicate_approve_request_does_not_double_disburse(
    client, db, investor, funded_proposal
):
    """Approve dikirim dua kali berurutan (bukan konkuren -- itu RF-5) untuk
    milestone yang sama: yang kedua ditolak 409 karena milestone sudah
    disbursed, dan tidak ada entri ledger kedua."""
    m1 = funded_proposal.milestones[0]
    pertama = await client.post(
        f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers
    )
    kedua = await client.post(
        f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers
    )
    assert pertama.status_code == 200
    assert kedua.status_code == 409

    entri = (
        await db.scalars(
            select(LedgerEntry).where(
                LedgerEntry.proposal_id == funded_proposal.id,
                LedgerEntry.entry_type == EntryType.DISBURSEMENT_OUT,
            )
        )
    ).all()
    assert len(entri) == 1

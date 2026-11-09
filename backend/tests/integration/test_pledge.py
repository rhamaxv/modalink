"""Endpoint pledge dan pembatalan (BR-20 sampai BR-28)."""

import pytest
from sqlalchemy import select

from app.errors import UnprocessableError
from app.models.ledger import EntryType, LedgerEntry
from app.models.pledge import Pledge, PledgeStatus
from app.models.proposal import ProposalStatus
from app.services.ledger import compute_balance
from app.services.pledge import create_pledge


async def test_br22_any_investor_may_fund(client, investor_lain, listed_proposal):
    """Bukan hanya pembuat campaign (D-12)."""
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor_lain.headers,
        json={"amount": 4_000_000},
    )
    assert res.status_code == 201


async def test_br21_pledge_exceeding_remainder_rejected_with_remainder_in_detail(
    client, investor, listed_proposal
):
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 7_000_000},
    )
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 5_000_000},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pledge_melebihi_sisa"
    assert res.json()["error"]["detail"]["remaining_amount"] == 3_000_000


async def test_br27_pledge_below_minimum_rejected(client, investor, listed_proposal):
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 50_000},
    )
    assert res.status_code == 422


async def test_br20_submitted_proposal_cannot_be_funded(
    client, investor, submitted_proposal
):
    res = await client.post(
        f"/api/v1/proposals/{submitted_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 1_000_000},
    )
    assert res.status_code in {404, 409}


async def test_br25_pledge_cannot_be_cancelled_after_funded(
    client, investor, funded_proposal
):
    pledge_id = funded_proposal.pledges[0].id
    res = await client.delete(f"/api/v1/pledges/{pledge_id}", headers=investor.headers)
    assert res.status_code == 409


async def test_br25_pledge_cannot_be_cancelled_after_completed(
    client, db, investor, umkm_lain, funded_proposal
):
    """Reproduksi double-spend (review Finding 1): BR-25 ditulis sebagai
    `proposal.status is FUNDED` saja, padahal `completed` ada SETELAH funded
    (T-09) dan tidak pernah tertutup. Begitu kedua milestone cair dan
    proposal `completed`, pledge yang mendanainya harus tetap terkunci --
    membatalkannya sekarang berarti merefund uang yang sudah keluar ke UMKM.
    """
    m1, m2 = funded_proposal.milestones
    pledge_id = funded_proposal.pledges[0].id

    await client.post(f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers)
    await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json={"narrative": "x" * 60, "metrics": None},
    )
    approve_m2 = await client.post(
        f"/api/v1/milestones/{m2.id}/approve", headers=investor.headers
    )
    assert approve_m2.status_code == 200
    await db.refresh(funded_proposal.proposal)
    assert funded_proposal.proposal.status is ProposalStatus.COMPLETED

    res = await client.delete(f"/api/v1/pledges/{pledge_id}", headers=investor.headers)
    assert res.status_code == 409

    await db.refresh(funded_proposal.proposal)
    assert funded_proposal.proposal.status is ProposalStatus.COMPLETED

    entries = (
        await db.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == funded_proposal.id)
        )
    ).all()
    assert EntryType.REFUND_OUT not in [e.entry_type for e in entries]
    assert compute_balance(entries) == 0


async def test_br26_cancellation_records_refund_not_delete(
    client, db, investor, listed_proposal
):
    create_response = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    await client.delete(
        f"/api/v1/pledges/{create_response.json()['id']}", headers=investor.headers
    )

    entries = (
        await db.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == listed_proposal.id)
        )
    ).all()
    entry_types = [e.entry_type for e in entries]
    assert EntryType.PLEDGE_IN in entry_types
    assert EntryType.REFUND_OUT in entry_types
    assert len(entries) == 2  # entri pledge_in tidak dihapus


async def test_t07_cancelling_last_pledge_returns_proposal_to_listed(
    client, db, investor, listed_proposal
):
    """R2b, lewat T-07 (partially_funded -> listed saat pledge kosong):
    pembatalan wajib memicu recompute_funding_status di transaksi yang sama,
    bukan hanya mencatat refund_out. Tanpa itu, proposal tetap kelihatan
    partially_funded padahal tidak ada satu pun pledge aktif lagi."""
    create_response = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    await db.refresh(listed_proposal)
    assert listed_proposal.status is ProposalStatus.PARTIALLY_FUNDED

    res = await client.delete(
        f"/api/v1/pledges/{create_response.json()['id']}", headers=investor.headers
    )
    assert res.status_code == 200
    await db.refresh(listed_proposal)
    assert listed_proposal.status is ProposalStatus.LISTED


async def test_br28_umkm_and_community_have_no_pledge_access(
    client, umkm, community, listed_proposal
):
    for account in (umkm, community):
        res = await client.post(
            f"/api/v1/proposals/{listed_proposal.id}/pledges",
            headers=account.headers,
            json={"amount": 1_000_000},
        )
        assert res.status_code == 403


async def test_br62_pledge_after_deadline_rejected_not_accepted_then_refunded(
    client, db, investor, listed_proposal, majukan
):
    """Review f06-b Finding 1: sebelum fix, pledge yang masuk setelah
    funding_deadline lewat tetap diterima (201 Created, baris pledge_in
    tercatat) dan baru dipaksa-refund balik oleh recompute_funding_status di
    akhir create_pledge. Investor sempat "berhasil" pledge pada proposal yang
    pada request yang sama juga ditulis `failed`. Sekarang pledge-nya
    ditolak sebelum satu baris pun ditulis.

    Status `failed` yang muncul di GET di bawah bukan akibat pledge yang
    ditolak -- ia berasal dari evaluate_expiry (BR-61, fase 09) yang
    berjalan di setiap pembacaan proposal begitu funding_deadline lewat,
    terlepas dari percobaan pledge apa pun. Yang dibuktikan di sini tetap
    sama seperti sebelum fase 09 ada: percobaan pledge yang ditolak itu
    sendiri tidak menulis satu baris pun.
    """
    await majukan(hari=30)  # funding_deadline campaign fixture jatuh di hari ke-21

    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pendanaan_sudah_ditutup"

    pledges = (
        await db.scalars(select(Pledge).where(Pledge.proposal_id == listed_proposal.id))
    ).all()
    assert pledges == [], "pledge yang ditolak tidak boleh menulis baris pledge apa pun"

    entries = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert entries["status"] == "failed", (
        "deadline sudah lewat tanpa pledge aktif; evaluasi lazy (BR-61) wajib "
        "menulis failed begitu proposal ini dibaca"
    )

    entries_rows = (
        await db.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == listed_proposal.id)
        )
    ).all()
    assert entries_rows == [], (
        "tidak ada pledge aktif yang perlu direfund; pledge yang ditolak tidak "
        "pernah tercatat untuk direfund balik"
    )


async def test_br62_cancelling_one_pledge_past_deadline_refunds_every_active_pledge(
    client, db, investor, investor_lain, listed_proposal, majukan
):
    """Review f06-b Finding 1: sebelum fix, membatalkan SATU pledge setelah
    funding_deadline lewat membuat recompute_funding_status menuliskan
    `failed`, sementara pledge investor lain yang tidak ikut dibatalkan tetap
    `active` selamanya tanpa entri `refund_out` pasangannya -- escrow-nya
    tersangkut permanen (BR-62). Sekarang pembatalan itu memicu refund untuk
    SELURUH pledge aktif yang tersisa, bukan hanya yang dibatalkan."""
    pledge_a = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    pledge_b = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor_lain.headers,
        json={"amount": 3_000_000},
    )
    await majukan(hari=30)

    res = await client.delete(
        f"/api/v1/pledges/{pledge_b.json()['id']}", headers=investor_lain.headers
    )
    assert res.status_code == 200

    await db.refresh(listed_proposal)
    assert listed_proposal.status is ProposalStatus.FAILED

    pledges = (
        await db.scalars(select(Pledge).where(Pledge.proposal_id == listed_proposal.id))
    ).all()
    assert {str(p.id) for p in pledges} == {
        pledge_a.json()["id"],
        pledge_b.json()["id"],
    }
    assert all(p.status is PledgeStatus.CANCELLED for p in pledges), (
        "proposal failed tidak boleh memegang satu pun pledge aktif"
    )

    entries_rows = (
        await db.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == listed_proposal.id)
        )
    ).all()
    refunded_pledge_ids = {
        e.ref_id for e in entries_rows if e.entry_type is EntryType.REFUND_OUT
    }
    assert refunded_pledge_ids == {p.id for p in pledges}, (
        "setiap pledge aktif pada proposal failed wajib punya refund_out pasangannya"
    )
    assert compute_balance(entries_rows) == 0


async def test_br27_service_layer_rejects_amount_below_minimum_without_http(
    db, investor, listed_proposal, clock
):
    """BR-27 sebelumnya hanya ditegakkan di PledgeIn (schemas/pledge.py), satu
    pintu HTTP saja. Pemanggil yang menyusun pledge lewat create_pledge()
    langsung -- test lain, job batch, service lain -- melewati pintu itu
    sama sekali dan bisa mencatat pledge Rp1 (CLAUDE.md aturan 1: aturan
    uang tidak boleh cuma benar di satu lapisan)."""
    with pytest.raises(UnprocessableError) as exc_info:
        await create_pledge(db, investor.user, listed_proposal, 1, clock)
    assert exc_info.value.code == "pledge_di_bawah_minimum"

"""Endpoint pledge dan pembatalan (BR-20 sampai BR-28)."""

from sqlalchemy import select

from app.models.ledger import EntryType, LedgerEntry
from app.models.proposal import ProposalStatus


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
    client, investor, listed_proposal, majukan
):
    """Review f06-b Finding 1: sebelum fix, pledge yang masuk setelah
    funding_deadline lewat tetap diterima (201 Created, baris pledge_in
    tercatat) dan baru dipaksa-refund balik oleh recompute_funding_status di
    akhir create_pledge. Investor sempat "berhasil" pledge pada proposal yang
    pada request yang sama juga ditulis `failed`. Sekarang pledge-nya
    ditolak sebelum satu baris pun ditulis."""
    await majukan(hari=30)  # funding_deadline campaign fixture jatuh di hari ke-21

    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pendanaan_sudah_ditutup"

    entries = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert entries["status"] == "listed", (
        "pledge yang ditolak tidak boleh ikut mengubah status proposal"
    )

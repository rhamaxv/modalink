"""Endpoint pledge dan pembatalan (BR-20 sampai BR-28)."""

from sqlalchemy import select

from app.models.ledger import EntryType, LedgerEntry


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
    buat = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    await client.delete(
        f"/api/v1/pledges/{buat.json()['id']}", headers=investor.headers
    )

    entri = (
        await db.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == listed_proposal.id)
        )
    ).all()
    tipe = [e.entry_type for e in entri]
    assert EntryType.PLEDGE_IN in tipe
    assert EntryType.REFUND_OUT in tipe
    assert len(entri) == 2  # entri pledge_in tidak dihapus


async def test_br28_umkm_and_community_have_no_pledge_access(
    client, umkm, community, listed_proposal
):
    for akun in (umkm, community):
        res = await client.post(
            f"/api/v1/proposals/{listed_proposal.id}/pledges",
            headers=akun.headers,
            json={"amount": 1_000_000},
        )
        assert res.status_code == 403

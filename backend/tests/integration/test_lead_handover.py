"""RF-4: lead investor berpindah saat pledge terbesar dibatalkan (BR-23, BR-25).

`recompute_funding_status` sudah memanggil `pick_lead_investor` dari jumlah
pledge aktif setiap kali dipanggil (services/pledge.py), jadi test di sini
menguji jalur HTTP pledge/cancel sungguhan, bukan menambah logika baru.
Test pertama menemukan bahwa BR-25 (pledge terkunci setelah `funded`) sudah
menutup sebagian besar RF-4; test kedua menguji jalur yang tersisa, sebelum
`funded`, dengan dua investor yang benar-benar berbeda supaya lead yang
berpindah bisa dibedakan dari lead yang kebetulan sama.
"""

from app.models.proposal import ProposalStatus as S
from app.services.ledger import total_terkumpul_proposal


async def test_rf4_cancelling_largest_pledge_after_funded_is_rejected(
    client, db, investor, investor_lain, listed_proposal
):
    besar = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 7_000_000},
    )
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor_lain.headers,
        json={"amount": 3_000_000},
    )

    await db.refresh(listed_proposal)
    assert listed_proposal.status is S.FUNDED
    assert listed_proposal.lead_investor_id == investor.user.id

    # Dibatalkan setelah funded harus ditolak (BR-25); ini yang melindungi RF-4
    # dari sisi "terlambat", lead investor tidak pernah berpindah lagi setelah
    # proposal funded karena pledge-nya sudah terkunci.
    res = await client.delete(
        f"/api/v1/pledges/{besar.json()['id']}", headers=investor.headers
    )
    assert res.status_code == 409


async def test_rf4_cancelling_largest_pledge_before_funded_moves_lead(
    client, db, investor, investor_lain, listed_proposal
):
    # 6 juta dan 3 juta: dua kandidat yang benar-benar beda jumlah dan beda
    # investor, supaya pergantian lead di bawah tidak bisa "kebetulan" sama
    # lead sebelum dan sesudah pembatalan.
    besar = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 6_000_000},
    )
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor_lain.headers,
        json={"amount": 3_000_000},
    )
    await db.refresh(listed_proposal)
    assert listed_proposal.lead_investor_id == investor.user.id

    res = await client.delete(
        f"/api/v1/pledges/{besar.json()['id']}", headers=investor.headers
    )
    assert res.status_code == 200

    await db.refresh(listed_proposal)
    assert listed_proposal.status is S.PARTIALLY_FUNDED
    assert listed_proposal.lead_investor_id == investor_lain.user.id


async def test_rf4_funded_never_occurs_with_total_below_requested(
    client, db, investor, investor_lain, listed_proposal
):
    """Invarian RF-4: status funded berarti total == requested_amount, tanpa
    kecuali. Beda dari draf brief: di sini proposal benar-benar dipledge
    sebagian (7 dari 10 juta) supaya cabang "belum funded" di bawah betul-betul
    tereksekusi, bukan lolos kosong karena fixture-nya memang belum dipledge
    sama sekali."""
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor_lain.headers,
        json={"amount": 3_000_000},
    )
    await db.refresh(listed_proposal)

    total = await total_terkumpul_proposal(db, listed_proposal.id)
    if listed_proposal.status is S.FUNDED:
        assert total == listed_proposal.requested_amount
    else:
        assert total < listed_proposal.requested_amount

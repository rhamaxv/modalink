"""Vote komunitas: toggle, satu akun satu vote, tidak pernah mengubah status
proposal (BR-30 sampai BR-32)."""

import pytest
from sqlalchemy import func, select

# Bukan app.domain.transitions.ProposalStatus: kelas itu beda identitas dari
# tipe kolom app.models.proposal.ProposalStatus meski nilai stringnya sama
# (lihat docstring models/proposal.py dan recompute_funding_status di
# services/pledge.py). Perbandingan `is` di bawah akan selalu False kalau
# memakai kelas domain, apa pun implementasinya -- brief f08-a salah di titik
# ini, bukan kodenya.
from app.models.proposal import ProposalStatus as S
from app.models.vote import Vote


async def test_community_can_vote(client, community, listed_proposal):
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/vote", headers=community.headers
    )
    assert res.status_code == 200
    assert res.json() == {"voted": True, "vote_count": 1}


async def test_br32_vote_is_toggle(client, db, community, listed_proposal):
    url = f"/api/v1/proposals/{listed_proposal.id}/vote"
    await client.post(url, headers=community.headers)
    kedua = await client.post(url, headers=community.headers)
    assert kedua.json() == {"voted": False, "vote_count": 0}

    # Test yang hanya memeriksa tally bisa lolos walau barisnya masih dua
    # (voted lalu dibatalkan tanpa benar-benar menghapus baris pertama).
    # Jumlah baris sungguhan di tabel adalah buktinya, bukan angka balasan.
    jumlah_baris = await db.scalar(
        select(func.count())
        .select_from(Vote)
        .where(Vote.proposal_id == listed_proposal.id)
    )
    assert jumlah_baris == 0


async def test_br32_one_account_one_vote_enforced_by_database(
    db, community, listed_proposal
):
    from sqlalchemy.exc import IntegrityError

    db.add(Vote(proposal_id=listed_proposal.id, user_id=community.user.id))
    await db.flush()
    db.add(Vote(proposal_id=listed_proposal.id, user_id=community.user.id))
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_br31_vote_does_not_change_proposal_status(
    db, client, community, listed_proposal
):
    sebelum = listed_proposal.status
    for _ in range(20):
        await client.post(
            f"/api/v1/proposals/{listed_proposal.id}/vote", headers=community.headers
        )
    await db.refresh(listed_proposal)
    assert listed_proposal.status is sebelum is S.LISTED


async def test_br30_submitted_proposal_cannot_be_voted(
    client, community, submitted_proposal
):
    res = await client.post(
        f"/api/v1/proposals/{submitted_proposal.id}/vote", headers=community.headers
    )
    assert res.status_code in {404, 409}


async def test_investor_and_umkm_cannot_vote(client, investor, umkm, listed_proposal):
    for akun in (investor, umkm):
        res = await client.post(
            f"/api/v1/proposals/{listed_proposal.id}/vote", headers=akun.headers
        )
        assert res.status_code == 403

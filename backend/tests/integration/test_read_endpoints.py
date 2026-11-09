"""Empat endpoint baca yang dipakai frontend tapi tidak dimiliki task mana
pun (10-api-contract.md baris 57, 67, 73, 96). Lihat laporan Fase 07 Task 6
untuk penyimpangan dari baris 73 (tidak ada kolom laporan terakhir: belum
ada model milestone_reports di backend ini)."""

from uuid import uuid4

from app.models.proposal import (
    MilestoneStatus,
    Proposal,
    ProposalMilestone,
    ProposalStatus,
)
from app.services.pledge import cancel_pledge, create_pledge, get_locked_proposal


async def test_br_mine_returns_only_current_umkm_own_proposals(
    client, db, campaign, umkm, umkm_lain, buat_proposal
):
    """Dua UMKM berbeda, masing-masing punya proposal sendiri: satu UMKM
    tidak boleh melihat proposal milik UMKM lain lewat endpoint ini."""
    milik_umkm = await buat_proposal(ProposalStatus.LISTED)

    milik_umkm_lain = Proposal(
        campaign_id=campaign.id,
        umkm_id=umkm_lain.user.id,
        business_name="Warung Kopi Tetangga",
        business_profile="x" * 50,
        fund_usage_plan="x" * 50,
        business_projection="x" * 50,
        requested_amount=8_000_000,
        status=ProposalStatus.LISTED,
    )
    db.add(milik_umkm_lain)
    await db.flush()

    res = await client.get("/api/v1/proposals/mine", headers=umkm.headers)
    assert res.status_code == 200
    ids = {p["id"] for p in res.json()}
    assert str(milik_umkm.id) in ids
    assert str(milik_umkm_lain.id) not in ids


async def test_br_mine_rejected_for_investor_role(client, investor):
    res = await client.get("/api/v1/proposals/mine", headers=investor.headers)
    assert res.status_code == 403


async def test_br67_pledges_list_hides_cancelled_pledge(
    client, db, investor, investor_lain, listed_proposal, clock
):
    """Panjang daftar yang diperiksa, bukan hanya status pledge yang
    dibatalkan: daftar berisi SELURUH riwayat akan tetap punya status
    'cancelled' yang benar tapi panjangnya salah."""
    proposal = await get_locked_proposal(db, listed_proposal.id)
    aktif = await create_pledge(db, investor.user, proposal, 3_000_000, clock)
    proposal2 = await get_locked_proposal(db, listed_proposal.id)
    dibatalkan = await create_pledge(
        db, investor_lain.user, proposal2, 2_000_000, clock
    )
    proposal3 = await get_locked_proposal(db, listed_proposal.id)
    await cancel_pledge(db, proposal3, dibatalkan, clock)

    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/pledges", headers=investor.headers
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(aktif.id)


async def test_br67_lead_investor_marker_moves_after_largest_cancelled(
    client, db, investor, investor_lain, listed_proposal, clock
):
    proposal = await get_locked_proposal(db, listed_proposal.id)
    kecil = await create_pledge(db, investor_lain.user, proposal, 2_000_000, clock)
    proposal2 = await get_locked_proposal(db, listed_proposal.id)
    besar = await create_pledge(db, investor.user, proposal2, 5_000_000, clock)

    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/pledges", headers=investor.headers
    )
    oleh_id = {p["id"]: p for p in res.json()["items"]}
    assert oleh_id[str(besar.id)]["is_lead_investor"] is True
    assert oleh_id[str(kecil.id)]["is_lead_investor"] is False

    proposal3 = await get_locked_proposal(db, listed_proposal.id)
    await cancel_pledge(db, proposal3, besar, clock)

    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/pledges", headers=investor.headers
    )
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(kecil.id)
    assert items[0]["is_lead_investor"] is True


async def test_milestones_visible_for_public_proposal_and_404_for_private_non_owner(
    client, db, listed_proposal, submitted_proposal, umkm, umkm_lain
):
    """`listed_proposal` publik (boleh_melihat selalu True untuk status itu),
    `submitted_proposal` tidak publik dan dimiliki `umkm` (bukan `umkm_lain`):
    GET milestones mewarisi persis aturan akses GET /proposals/{id}."""
    # listed_proposal sudah membawa dua milestone dari fixture-nya (BR-14,
    # jumlahnya persis requested_amount), jadi menambah seq=1 di sini akan
    # menabrak uq_milestone_proposal_seq. submitted_proposal tidak punya
    # milestone sama sekali, jadi hanya ia yang perlu dibuatkan.
    db.add(
        ProposalMilestone(
            proposal_id=submitted_proposal.id,
            seq=1,
            title="Beli mesin",
            description="x" * 20,
            amount=submitted_proposal.requested_amount,
            status=MilestoneStatus.PENDING,
        )
    )
    await db.flush()

    res_publik = await client.get(f"/api/v1/proposals/{listed_proposal.id}/milestones")
    assert res_publik.status_code == 200
    assert len(res_publik.json()["items"]) == 2

    res_anon = await client.get(f"/api/v1/proposals/{submitted_proposal.id}/milestones")
    assert res_anon.status_code == 404

    res_bukan_pemilik = await client.get(
        f"/api/v1/proposals/{submitted_proposal.id}/milestones",
        headers=umkm_lain.headers,
    )
    assert res_bukan_pemilik.status_code == 404

    res_pemilik = await client.get(
        f"/api/v1/proposals/{submitted_proposal.id}/milestones", headers=umkm.headers
    )
    assert res_pemilik.status_code == 200
    assert res_pemilik.json()["items"][0]["status"] == "pending"


async def test_internal_ledger_balance_matches_manual_sum_of_returned_entries(
    client, db, investor, investor_lain, listed_proposal, clock
):
    """Dua angka dihitung dengan cara berbeda dibandingkan: `balance` dari
    respons endpoint lawan penjumlahan manual atas `entries` yang sama
    persis respons itu, bukan angka yang dihitung ulang dari fixture."""
    proposal = await get_locked_proposal(db, listed_proposal.id)
    await create_pledge(db, investor.user, proposal, 4_000_000, clock)
    proposal2 = await get_locked_proposal(db, listed_proposal.id)
    dibatalkan = await create_pledge(
        db, investor_lain.user, proposal2, 1_000_000, clock
    )
    proposal3 = await get_locked_proposal(db, listed_proposal.id)
    await cancel_pledge(db, proposal3, dibatalkan, clock)

    res = await client.get(f"/api/v1/internal/ledger/{listed_proposal.id}")
    assert res.status_code == 200
    body = res.json()
    manual = sum(
        e["amount"] if e["entry_type"] == "pledge_in" else -e["amount"]
        for e in body["entries"]
    )
    assert manual == body["balance"]
    # pledge_in 4_000_000 + pledge_in 1_000_000 + refund_out 1_000_000 = 4_000_000.
    # Dihitung di sini dari nominal yang dikirim, bukan dibaca balik dari
    # body["balance"] sendiri, supaya assert di atas tidak jadi satu-satunya
    # pemeriksaan (tautologi "x == x" kalau implementasi salah dengan cara
    # yang konsisten di kedua sisi).
    assert body["balance"] == 4_000_000


async def test_internal_ledger_unknown_proposal_returns_404(client):
    """code diperiksa, bukan hanya status: endpoint yang belum terdaftar
    sama sekali juga membalas 404, tapi lewat error handler routing generik
    (code 'kesalahan_permintaan'), bukan lewat NotFoundError domain ini."""
    hantu = uuid4()
    res = await client.get(f"/api/v1/internal/ledger/{hantu}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "proposal_tidak_ada"

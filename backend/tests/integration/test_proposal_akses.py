from uuid import uuid4


async def test_proposal_listed_visible_publicly(client, listed_proposal):
    assert (
        await client.get(f"/api/v1/proposals/{listed_proposal.id}")
    ).status_code == 200


async def test_proposal_submitted_not_visible_publicly(client, submitted_proposal):
    assert (
        await client.get(f"/api/v1/proposals/{submitted_proposal.id}")
    ).status_code == 404


async def test_proposal_that_truly_does_not_exist_returns_404(client):
    """Cabang `if proposal is None` belum pernah dieksekusi test lain (C-22):
    test di atas hanya menguji proposal yang ada tapi tersembunyi dari
    viewer, bukan id yang sama sekali tidak ada baris-nya."""
    hantu = uuid4()
    res = await client.get(f"/api/v1/proposals/{hantu}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "proposal_tidak_ada"


async def test_proposal_submitted_visible_to_its_owner(
    client, umkm, submitted_proposal
):
    res = await client.get(
        f"/api/v1/proposals/{submitted_proposal.id}", headers=umkm.headers
    )
    assert res.status_code == 200


async def test_proposal_rejected_visible_to_campaign_owner(
    client, investor, rejected_proposal
):
    res = await client.get(
        f"/api/v1/proposals/{rejected_proposal.id}", headers=investor.headers
    )
    assert res.status_code == 200


async def test_proposal_submitted_not_visible_to_other_umkm(
    client, umkm_lain, submitted_proposal
):
    res = await client.get(
        f"/api/v1/proposals/{submitted_proposal.id}", headers=umkm_lain.headers
    )
    assert res.status_code == 404


async def test_list_campaign_proposals_hides_not_yet_listed(
    client, investor, listed_proposal, submitted_proposal, rejected_proposal
):
    """Filter visibilitas di endpoint daftar proposal campaign lahir di fase 03
    tanpa satu pun test. Refactor yang menghapus klausa .where() akan lolos semua
    test lain, dan kebocorannya baru terlihat saat proposal yang ditolak sudah
    terbaca publik."""
    campaign_id = listed_proposal.campaign_id

    publik = await client.get(f"/api/v1/campaigns/{campaign_id}/proposals")
    terlihat = {p["id"] for p in publik.json()["items"]}
    assert str(listed_proposal.id) in terlihat
    assert str(submitted_proposal.id) not in terlihat
    assert str(rejected_proposal.id) not in terlihat

    pemilik = await client.get(
        f"/api/v1/campaigns/{campaign_id}/proposals", headers=investor.headers
    )
    semua = {p["id"] for p in pemilik.json()["items"]}
    assert {
        str(listed_proposal.id),
        str(submitted_proposal.id),
        str(rejected_proposal.id),
    } <= semua


async def test_already_closed_campaign_rejects_new_proposal(
    client, investor, campaign, umkm, kirim_proposal
):
    """Ditunda dari fase 03 karena endpoint POST proposal baru lahir di sini."""
    await client.post(
        f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers
    )
    res = await kirim_proposal(campaign.id, headers=umkm.headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pengajuan_ditutup"


async def test_patch_and_close_nonexistent_campaign_returns_404(client, investor):
    """Satu-satunya cabang di dependency kepemilikan yang belum pernah dieksekusi."""
    hantu = uuid4()
    assert (
        await client.patch(
            f"/api/v1/campaigns/{hantu}", headers=investor.headers, json={"title": "x"}
        )
    ).status_code == 404
    assert (
        await client.post(f"/api/v1/campaigns/{hantu}/close", headers=investor.headers)
    ).status_code == 404


async def test_public_listing_only_includes_listed_and_above(
    client, listed_proposal, submitted_proposal, rejected_proposal
):
    ids = {p["id"] for p in (await client.get("/api/v1/proposals")).json()["items"]}
    assert str(listed_proposal.id) in ids
    assert str(submitted_proposal.id) not in ids
    assert str(rejected_proposal.id) not in ids

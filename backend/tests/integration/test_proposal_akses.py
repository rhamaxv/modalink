from uuid import uuid4


async def test_proposal_listed_terlihat_publik(client, listed_proposal):
    assert (
        await client.get(f"/api/v1/proposals/{listed_proposal.id}")
    ).status_code == 200


async def test_proposal_submitted_tidak_terlihat_publik(client, submitted_proposal):
    assert (
        await client.get(f"/api/v1/proposals/{submitted_proposal.id}")
    ).status_code == 404


async def test_proposal_yang_sungguh_tidak_ada_dikembalikan_404(client):
    """Cabang `if proposal is None` belum pernah dieksekusi test lain (C-22):
    test di atas hanya menguji proposal yang ada tapi tersembunyi dari
    viewer, bukan id yang sama sekali tidak ada baris-nya."""
    hantu = uuid4()
    res = await client.get(f"/api/v1/proposals/{hantu}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "proposal_tidak_ada"


async def test_proposal_submitted_terlihat_oleh_pemiliknya(
    client, umkm, submitted_proposal
):
    res = await client.get(
        f"/api/v1/proposals/{submitted_proposal.id}", headers=umkm.headers
    )
    assert res.status_code == 200


async def test_proposal_rejected_terlihat_oleh_pemilik_campaign(
    client, investor, rejected_proposal
):
    res = await client.get(
        f"/api/v1/proposals/{rejected_proposal.id}", headers=investor.headers
    )
    assert res.status_code == 200


async def test_proposal_submitted_tidak_terlihat_umkm_lain(
    client, umkm_lain, submitted_proposal
):
    res = await client.get(
        f"/api/v1/proposals/{submitted_proposal.id}", headers=umkm_lain.headers
    )
    assert res.status_code == 404


async def test_daftar_proposal_campaign_menyembunyikan_yang_belum_listed(
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


async def test_campaign_yang_sudah_closed_menolak_proposal_baru(
    client, investor, campaign, umkm, body_proposal
):
    """Ditunda dari fase 03 karena endpoint POST proposal baru lahir di sini."""
    await client.post(
        f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers
    )
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pengajuan_ditutup"


async def test_patch_dan_close_campaign_yang_tidak_ada_mengembalikan_404(
    client, investor
):
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


async def test_daftar_publik_hanya_memuat_listed_ke_atas(
    client, listed_proposal, submitted_proposal, rejected_proposal
):
    ids = {p["id"] for p in (await client.get("/api/v1/proposals")).json()["items"]}
    assert str(listed_proposal.id) in ids
    assert str(submitted_proposal.id) not in ids
    assert str(rejected_proposal.id) not in ids

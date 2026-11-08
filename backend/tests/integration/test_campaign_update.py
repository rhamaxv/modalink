"""Ubah, tutup, dan kunci ambang skor campaign (BR-77, T-40, T-41).

test_campaign_closed_menolak_proposal_baru dari rencana fase ini sengaja tidak
ditulis di sini: endpoint pembuatan proposal (POST .../proposals) adalah
cakupan fase proposal, bukan fase campaign. Aturan "campaign tertutup menolak
proposal baru" akan diuji saat endpoint itu dibangun.
"""

from app.models.campaign import CampaignStatus


async def test_br77_threshold_bisa_diubah_selama_belum_ada_proposal(
    client, investor, campaign
):
    res = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        headers=investor.headers,
        json={"score_threshold": 75},
    )
    assert res.status_code == 200
    assert res.json()["score_threshold"] == 75


async def test_br77_threshold_terkunci_setelah_proposal_pertama(
    client, investor, campaign, listed_proposal
):
    res = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        headers=investor.headers,
        json={"score_threshold": 20},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "threshold_terkunci"


async def test_judul_tetap_bisa_diubah_setelah_ada_proposal(
    client, investor, campaign, listed_proposal
):
    res = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        headers=investor.headers,
        json={"title": "Judul baru"},
    )
    assert res.status_code == 200


async def test_t40_pemilik_bisa_menutup_campaign_manual(client, db, investor, campaign):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers
    )
    assert res.status_code == 200
    await db.refresh(campaign)
    assert campaign.status is CampaignStatus.CLOSED


async def test_t41_campaign_tertutup_sendiri_setelah_apply_deadline_lewat(
    client, db, campaign, majukan
):
    await majukan(hari=8)  # apply_deadline campaign fixture jatuh di hari ke-7
    detail = (await client.get(f"/api/v1/campaigns/{campaign.id}")).json()
    assert detail["status"] == "closed"


async def test_t40_campaign_yang_sudah_closed_menolak_penutupan_ulang(
    client, investor, campaign
):
    await client.post(
        f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers
    )
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers
    )
    assert res.status_code == 409


async def test_investor_lain_tidak_bisa_mengubah_campaign(
    client, campaign, investor_lain
):
    res = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        headers=investor_lain.headers,
        json={"title": "Dibajak"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "bukan_pemilik"

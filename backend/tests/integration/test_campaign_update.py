"""Ubah, tutup, dan kunci ambang skor campaign (BR-77, T-40, T-41).

test_campaign_closed_menolak_proposal_baru dari rencana fase ini sengaja tidak
ditulis di sini: endpoint pembuatan proposal (POST .../proposals) adalah
cakupan fase proposal, bukan fase campaign. Aturan "campaign tertutup menolak
proposal baru" akan diuji saat endpoint itu dibangun.
"""

from app.models.campaign import CampaignStatus


async def test_br77_threshold_can_change_while_no_proposal_exists(
    client, investor, campaign
):
    res = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        headers=investor.headers,
        json={"score_threshold": 75},
    )
    assert res.status_code == 200
    assert res.json()["score_threshold"] == 75


async def test_br77_threshold_locked_after_first_proposal(
    client, investor, campaign, listed_proposal
):
    res = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        headers=investor.headers,
        json={"score_threshold": 20},
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "threshold_terkunci"


async def test_title_can_still_change_after_proposal_exists(
    client, investor, campaign, listed_proposal
):
    res = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        headers=investor.headers,
        json={"title": "Judul baru"},
    )
    assert res.status_code == 200


async def test_t40_owner_can_close_campaign_manually(client, db, investor, campaign):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers
    )
    assert res.status_code == 200
    await db.refresh(campaign)
    assert campaign.status is CampaignStatus.CLOSED


async def test_t41_campaign_closes_itself_after_apply_deadline_passes(
    client, db, campaign, majukan
):
    await majukan(hari=8)  # apply_deadline campaign fixture jatuh di hari ke-7
    detail = (await client.get(f"/api/v1/campaigns/{campaign.id}")).json()
    assert detail["status"] == "closed"


async def test_t40_already_closed_campaign_rejects_reclosing(
    client, investor, campaign
):
    await client.post(
        f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers
    )
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers
    )
    assert res.status_code == 409


async def test_other_investor_cannot_update_campaign(client, campaign, investor_lain):
    res = await client.patch(
        f"/api/v1/campaigns/{campaign.id}",
        headers=investor_lain.headers,
        json={"title": "Dibajak"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "bukan_pemilik"

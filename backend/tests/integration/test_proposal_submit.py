async def test_umkm_can_submit_proposal(client, umkm, campaign, body_proposal):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "submitted"
    assert data["scoring_status"] in {"pending", "processing", "done"}


async def test_br10_fund_usage_plan_under_100_characters_rejected(
    client, umkm, campaign, body_proposal
):
    """04-feature-umkm.md menetapkan minimal 100 karakter (BR-10). Rubrik
    skoring AI menilai kelengkapan isian di field ini, jadi minimumnya
    tidak boleh diam-diam dilonggarkan demi fixture test."""
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(fund_usage_plan="x" * 99),
    )
    assert res.status_code == 422


async def test_c26_fund_usage_plan_exactly_100_characters_accepted(
    client, umkm, campaign, body_proposal
):
    """Batas tepat di 100 belum pernah diuji sebelumnya: 99 ditolak dan 162
    (fixture) diterima, tapi off-by-one di validator bisa lolos tanpa
    kasus batas ini."""
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(fund_usage_plan="x" * 100),
    )
    assert res.status_code == 201


async def test_br11_funds_exceeding_campaign_target_rejected(
    client, umkm, campaign, body_proposal
):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(
            requested_amount=campaign.target_amount + 1,
            milestones=[
                {
                    "seq": 1,
                    "title": "a",
                    "description": "x" * 20,
                    "amount": campaign.target_amount + 1,
                }
            ],
        ),
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "dana_melebihi_target_campaign"


async def test_br14_milestone_amount_mismatch_rejected_with_difference(
    client, umkm, campaign, body_proposal
):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(
            milestones=[
                {"seq": 1, "title": "a", "description": "x" * 20, "amount": 5_000_000},
                {"seq": 2, "title": "b", "description": "x" * 20, "amount": 4_000_000},
            ]
        ),
    )
    assert res.status_code == 422
    assert "Rp1.000.000" in res.json()["error"]["message"]


async def test_br12_funds_below_minimum_rejected(client, umkm, campaign, body_proposal):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(
            requested_amount=400_000,
            milestones=[
                {"seq": 1, "title": "a", "description": "x" * 20, "amount": 200_000},
                {"seq": 2, "title": "b", "description": "x" * 20, "amount": 200_000},
            ],
        ),
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "dana_di_bawah_minimum"


async def test_br13_second_proposal_to_same_campaign_rejected_409(
    client, umkm, campaign, body_proposal
):
    await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "proposal_aktif_sudah_ada"


async def test_br17_campaign_past_apply_deadline_rejects(
    client, umkm, campaign_kedaluwarsa, body_proposal
):
    res = await client.post(
        f"/api/v1/campaigns/{campaign_kedaluwarsa.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pengajuan_ditutup"


async def test_t3_business_profile_over_5000_characters_rejected(
    client, umkm, campaign, body_proposal
):
    """Review keamanan: business_profile lolos sampai 5 MB tanpa batas atas
    sebelum ini. 5.000 karakter dipilih longgar -- kira-kira satu-dua
    halaman, jauh di atas rencana bisnis UMKM mana pun yang wajar -- supaya
    batas ini menolak payload raksasa tanpa pernah menolak isian sungguhan."""
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(business_profile="x" * 5_001),
    )
    assert res.status_code == 422


async def test_t3_fund_usage_plan_over_5000_characters_rejected(
    client, umkm, campaign, body_proposal
):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(fund_usage_plan="x" * 5_001),
    )
    assert res.status_code == 422


async def test_t3_business_projection_over_3000_characters_rejected(
    client, umkm, campaign, body_proposal
):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(business_projection="x" * 3_001),
    )
    assert res.status_code == 422


async def test_t3_more_than_30_milestones_rejected(
    client, umkm, campaign, body_proposal
):
    """Review keamanan: 50.000 item milestone lolos tanpa batas atas sebelum
    ini. 30 tahap jauh di atas rencana pendanaan bertahap mana pun yang
    wajar (seed data terpanjang hanya dua tahap)."""
    banyak = [
        {"seq": i, "title": f"Tahap {i}", "description": "x" * 20, "amount": 100_000}
        for i in range(1, 32)
    ]
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(requested_amount=31 * 100_000, milestones=banyak),
    )
    assert res.status_code == 422


async def test_br18_no_endpoint_to_update_proposal(app):
    rute = {
        (m, r.path)
        for r in app.routes
        if getattr(r, "methods", None)
        for m in r.methods
    }
    assert ("PATCH", "/api/v1/proposals/{proposal_id}") not in rute
    assert ("PUT", "/api/v1/proposals/{proposal_id}") not in rute

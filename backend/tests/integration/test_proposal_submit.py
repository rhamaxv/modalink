async def test_umkm_bisa_submit_proposal(client, umkm, campaign, body_proposal):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "submitted"
    assert data["scoring_status"] in {"pending", "processing", "done"}


async def test_br10_fund_usage_plan_di_bawah_100_karakter_ditolak(
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


async def test_c26_fund_usage_plan_tepat_100_karakter_diterima(
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


async def test_br11_dana_melebihi_target_campaign_ditolak(
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


async def test_br14_jumlah_milestone_tidak_pas_ditolak_dengan_selisih(
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


async def test_br12_dana_di_bawah_minimum_ditolak(
    client, umkm, campaign, body_proposal
):
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


async def test_br13_proposal_kedua_ke_campaign_sama_ditolak_409(
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


async def test_br17_campaign_yang_apply_deadline_nya_lewat_menolak(
    client, umkm, campaign_kedaluwarsa, body_proposal
):
    res = await client.post(
        f"/api/v1/campaigns/{campaign_kedaluwarsa.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pengajuan_ditutup"


async def test_br18_tidak_ada_endpoint_ubah_proposal(app):
    rute = {
        (m, r.path)
        for r in app.routes
        if getattr(r, "methods", None)
        for m in r.methods
    }
    assert ("PATCH", "/api/v1/proposals/{proposal_id}") not in rute
    assert ("PUT", "/api/v1/proposals/{proposal_id}") not in rute

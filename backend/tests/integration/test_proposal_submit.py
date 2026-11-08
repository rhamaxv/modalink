def body_proposal(**ubah):
    isi = {
        "business_name": "Warung Kopi Mbak Sri",
        "business_profile": "Warung kopi rumahan di Jakarta Timur, berjalan 3 tahun, "
        "2 pekerja, omzet rata-rata Rp12 juta per bulan.",
        "requested_amount": 10_000_000,
        "fund_usage_plan": "Rp6 juta mesin kopi, Rp3 juta bahan baku 3 bulan, "
        "Rp1 juta perbaikan etalase.",
        "business_projection": "Omzet diperkirakan naik ke Rp18 juta per bulan "
        "dalam 6 bulan setelah mesin baru dipakai.",
        "milestones": [
            {
                "seq": 1,
                "title": "Beli mesin",
                "description": "x" * 20,
                "amount": 5_000_000,
            },
            {
                "seq": 2,
                "title": "Bahan baku",
                "description": "x" * 20,
                "amount": 5_000_000,
            },
        ],
    }
    return isi | ubah


async def test_umkm_bisa_submit_proposal(client, umkm, campaign):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "submitted"
    assert data["scoring_status"] in {"pending", "processing", "done"}


async def test_br11_dana_melebihi_target_campaign_ditolak(client, umkm, campaign):
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
    client, umkm, campaign
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


async def test_br12_dana_di_bawah_minimum_ditolak(client, umkm, campaign):
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


async def test_br13_proposal_kedua_ke_campaign_sama_ditolak_409(client, umkm, campaign):
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
    client, umkm, campaign_kedaluwarsa
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

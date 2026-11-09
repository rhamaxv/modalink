"""Buat dan daftar campaign (BR-64, BR-05)."""

from datetime import timedelta

from app.domain.clock import SystemClock

SEKARANG = SystemClock().now()


def body_campaign(**ubah):
    isi = {
        "title": "Modal warung kopi Jakarta Timur",
        "description": "Mendanai warung kopi skala rumahan di Jakarta Timur." * 2,
        "sector": "kuliner",
        "target_amount": 50_000_000,
        "apply_deadline": (SEKARANG + timedelta(days=7)).isoformat(),
        "funding_deadline": (SEKARANG + timedelta(days=21)).isoformat(),
        "score_threshold": 60,
    }
    return isi | ubah


async def test_investor_bisa_membuat_campaign(client, investor):
    res = await client.post(
        "/api/v1/campaigns", headers=investor.headers, json=body_campaign()
    )
    assert res.status_code == 201
    assert res.json()["status"] == "open"


async def test_br64_funding_deadline_lebih_awal_ditolak_422(client, investor):
    res = await client.post(
        "/api/v1/campaigns",
        headers=investor.headers,
        json=body_campaign(funding_deadline=(SEKARANG + timedelta(days=3)).isoformat()),
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "urutan_deadline_salah"


async def test_apply_deadline_di_masa_lalu_ditolak(client, investor):
    res = await client.post(
        "/api/v1/campaigns",
        headers=investor.headers,
        json=body_campaign(apply_deadline=(SEKARANG - timedelta(days=1)).isoformat()),
    )
    assert res.status_code == 422


async def test_br05_daftar_campaign_bisa_diakses_tanpa_token(client, investor):
    dibuat = await client.post(
        "/api/v1/campaigns", headers=investor.headers, json=body_campaign()
    )
    res = await client.get("/api/v1/campaigns")
    assert res.status_code == 200

    # Dicari berdasarkan id, bukan dihitung jumlah seluruh baris. Beberapa test
    # di suite ini sengaja commit baris sungguhan (test_pledge_concurrency,
    # test_concurrent_approve) dan `python -m app.seed` menulis ke database yang
    # sama, jadi hitungan global membuat test ini merah karena sebab yang tidak
    # ada hubungannya dengan BR-05. Yang dijamin BR-05 adalah campaign bisa
    # dibaca tanpa token, bukan bahwa ia satu-satunya di database.
    ids = {item["id"] for item in res.json()["items"]}
    assert dibuat.json()["id"] in ids


async def test_daftar_campaign_urutannya_deterministik(client, investor):
    for i in range(3):
        await client.post(
            "/api/v1/campaigns",
            headers=investor.headers,
            json=body_campaign(title=f"Campaign {i}"),
        )
    sekali = (await client.get("/api/v1/campaigns")).json()["items"]
    lagi = (await client.get("/api/v1/campaigns")).json()["items"]
    assert [c["id"] for c in sekali] == [c["id"] for c in lagi]

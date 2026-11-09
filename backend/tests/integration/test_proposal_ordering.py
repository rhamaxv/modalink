"""Urutan daftar proposal untuk investor: skor lalu vote lalu waktu submit
(10-api-contract.md baris GET /campaigns/{id}/proposals)."""


async def test_ordered_by_score_then_vote_then_time(
    client, investor, campaign, proposal_dengan
):
    rendah = await proposal_dengan(skor=55, vote=9)
    tinggi = await proposal_dengan(skor=80, vote=0)
    sedang_a = await proposal_dengan(skor=70, vote=1)
    sedang_b = await proposal_dengan(skor=70, vote=5)

    items = (
        await client.get(
            f"/api/v1/campaigns/{campaign.id}/proposals", headers=investor.headers
        )
    ).json()["items"]
    urutan = [p["id"] for p in items]
    assert urutan == [
        str(tinggi.id),
        str(sedang_b.id),
        str(sedang_a.id),
        str(rendah.id),
    ]


async def test_tied_score_and_vote_broken_by_submit_time(
    client, investor, campaign, proposal_dengan
):
    duluan = await proposal_dengan(skor=70, vote=2)
    belakangan = await proposal_dengan(skor=70, vote=2)
    items = (
        await client.get(
            f"/api/v1/campaigns/{campaign.id}/proposals", headers=investor.headers
        )
    ).json()["items"]
    assert [p["id"] for p in items] == [str(duluan.id), str(belakangan.id)]


async def test_order_stable_across_requests(
    client, investor, campaign, banyak_proposal
):
    url = f"/api/v1/campaigns/{campaign.id}/proposals"
    sekali = [
        p["id"]
        for p in (await client.get(url, headers=investor.headers)).json()["items"]
    ]
    lagi = [
        p["id"]
        for p in (await client.get(url, headers=investor.headers)).json()["items"]
    ]
    assert sekali == lagi


async def test_score_used_is_latest_scoring_result(
    client, investor, campaign, proposal_discore_ulang
):
    """Proposal yang pernah dinilai dua kali harus memakai skor terbaru,
    bukan yang pertama."""
    items = (
        await client.get(
            f"/api/v1/campaigns/{campaign.id}/proposals", headers=investor.headers
        )
    ).json()["items"]
    cocok = next(p for p in items if p["id"] == str(proposal_discore_ulang.id))
    assert cocok["total_score"] == proposal_discore_ulang.skor_terbaru

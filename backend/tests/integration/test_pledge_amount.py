"""RF-2: nominal pledge yang bukan integer rupiah sah ditolak di batas HTTP."""

import pytest


@pytest.mark.parametrize(
    "value",
    [
        "1e9",
        1_000_000.5,
        "5.000.000",
        -1,
        0,
        9_223_372_036_854_775_808,
        # Keduanya cuma ditolak gara-gara strict=True di PledgeIn.amount (lihat
        # komentar di app/schemas/pledge.py): tanpa strict, Pydantic v2 lolos
        # meluluskan desimal bulat dan string numerik ke kolom BIGINT (BR-50).
        2_000_000.0,
        "5000000",
    ],
)
async def test_rf2_invalid_amount_rejected_with_422(
    client, investor, listed_proposal, value
):
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": value},
    )
    assert res.status_code == 422, f"nilai {value!r} lolos padahal seharusnya ditolak"

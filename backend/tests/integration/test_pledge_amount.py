"""RF-2: nominal pledge yang bukan integer rupiah sah ditolak di batas HTTP."""

import pytest


@pytest.mark.parametrize(
    "nilai",
    ["1e9", 1_000_000.5, "5.000.000", -1, 0, 9_223_372_036_854_775_808],
)
async def test_rf2_invalid_amount_rejected_with_422(
    client, investor, listed_proposal, nilai
):
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": nilai},
    )
    assert res.status_code == 422, f"nilai {nilai!r} lolos padahal seharusnya ditolak"

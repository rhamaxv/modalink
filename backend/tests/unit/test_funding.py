from datetime import UTC, datetime, timedelta

import pytest

from app.domain.funding import compute_funding_status, remaining_amount
from app.domain.transitions import ProposalStatus as S

SEKARANG = datetime(2026, 11, 7, tzinfo=UTC)
BESOK = SEKARANG + timedelta(days=1)
KEMARIN = SEKARANG - timedelta(days=1)


@pytest.mark.parametrize(
    "terkumpul,diminta,deadline,harapan",
    [
        (0, 10_000_000, BESOK, S.LISTED),
        (4_000_000, 10_000_000, BESOK, S.PARTIALLY_FUNDED),
        (10_000_000, 10_000_000, BESOK, S.FUNDED),
        (
            10_000_000,
            10_000_000,
            KEMARIN,
            S.FUNDED,
        ),  # sudah penuh, deadline tak relevan
        (0, 10_000_000, KEMARIN, S.FAILED),
        (4_000_000, 10_000_000, KEMARIN, S.FAILED),
    ],
)
def test_compute_funding_status(terkumpul, diminta, deadline, harapan):
    assert compute_funding_status(terkumpul, diminta, SEKARANG, deadline) is harapan


def test_br21_remaining_funds_computed_exactly():
    assert remaining_amount(4_000_000, 10_000_000) == 6_000_000
    assert remaining_amount(10_000_000, 10_000_000) == 0


def test_total_exceeding_requested_never_considered_valid():
    with pytest.raises(ValueError, match="melebihi"):
        compute_funding_status(11_000_000, 10_000_000, SEKARANG, BESOK)

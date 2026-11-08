"""Penentuan status funding. Satu-satunya tempat status ini dihitung (D-05)."""
from datetime import datetime

from app.domain.money import Rupiah
from app.domain.transitions import ProposalStatus


def remaining_amount(total_pledged: Rupiah, requested: Rupiah) -> Rupiah:
    return max(requested - total_pledged, 0)

def compute_funding_status(
    total_pledged: Rupiah,
    requested: Rupiah,
    now: datetime,
    funding_deadline: datetime,
) -> ProposalStatus:
    if total_pledged > requested:
        raise ValueError(
            "Total pledge melebihi dana yang diminta. "
            "Ini seharusnya mustahil; penguncian baris proposal bocor."
        )
    if total_pledged == requested:
        return ProposalStatus.FUNDED
    if now >= funding_deadline:
        return ProposalStatus.FAILED
    if total_pledged == 0:
        return ProposalStatus.LISTED
    return ProposalStatus.PARTIALLY_FUNDED

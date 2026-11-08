"""Lead investor adalah pemilik total pledge aktif terbesar (BR-23)."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.money import Rupiah


@dataclass(frozen=True, slots=True)
class PledgeRingkas:
    investor_id: UUID
    amount: Rupiah
    created_at: datetime


def pick_lead_investor(pledges: Sequence[PledgeRingkas]) -> UUID | None:
    if not pledges:
        return None

    total: dict[UUID, Rupiah] = defaultdict(int)
    pertama: dict[UUID, datetime] = {}
    for p in pledges:
        total[p.investor_id] += p.amount
        if p.investor_id not in pertama or p.created_at < pertama[p.investor_id]:
            pertama[p.investor_id] = p.created_at

    # Terbesar menang; seri diputus oleh pledge paling awal, bukan oleh urutan dict.
    return max(total, key=lambda inv: (total[inv], -pertama[inv].timestamp()))

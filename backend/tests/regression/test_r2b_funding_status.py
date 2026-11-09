"""R2b: status funding proposal selalu cocok dengan jumlah pledge aktif (D-05).

Penutup risiko dari D-05 (`partially_funded` disimpan sebagai kolom, bukan
dihitung saat dibaca): kalau ada kode yang menulis `listed`/`partially_funded`/
`funded` di luar `recompute_funding_status()`, test ini yang menangkapnya.
"""

from collections import defaultdict
from datetime import datetime, timedelta

import pytest

from app.domain.clock import SystemClock
from app.domain.funding import compute_funding_status
from app.models.campaign import Campaign
from app.models.pledge import Pledge
from app.models.proposal import Proposal, ProposalStatus
from app.services.ledger import total_pledge_aktif
from app.services.pledge import cancel_pledge, create_pledge, recompute_funding_status


class _AdvanceableClock:
    """Clock uji yang bisa dimajukan manual, khusus menyimulasikan deadline
    pendanaan lewat di tengah skenario ("fails-mid-way" di bawah). FrozenClock
    produksi sengaja tidak punya method ini: ia harus tetap diam sepanjang
    satu test, hanya R2b yang butuh memajukannya pertengahan jalan."""

    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        return self._at

    def advance_to(self, at: datetime) -> None:
        self._at = at


@pytest.fixture
def clock():
    """Menimpa fixture `clock` dari conftest (FrozenClock biasa) khusus di
    modul ini, supaya `listed_proposal` dan `funded_proposal` yang keduanya
    bergantung pada fixture `clock` ikut memakai jam yang bisa dimajukan."""
    return _AdvanceableClock(SystemClock().now())


async def check_consistency(db, proposal: Proposal, clock) -> None:
    total = await total_pledge_aktif(db, proposal.id)
    campaign = await db.get(Campaign, proposal.campaign_id)
    expected_domain_status = compute_funding_status(
        total, proposal.requested_amount, clock.now(), campaign.funding_deadline
    )
    # ProposalStatus(...value), bukan perbandingan `is` lintas kelas:
    # compute_funding_status mengembalikan app.domain.transitions.ProposalStatus,
    # kelas enum berbeda dari tipe kolom app.models.proposal.ProposalStatus
    # meski nilai stringnya sama. `is` lintas kelas selalu False walau nilainya
    # identik -- draf awal task ini membandingkan lintas kelas seperti itu,
    # tepat pola "enum import yang membuat assert is selalu gagal" yang sudah
    # pernah lolos lewat review di project ini.
    expected = ProposalStatus(expected_domain_status.value)
    assert proposal.status is expected, (
        f"status {proposal.status} tidak cocok dengan total pledge {total}; "
        f"harusnya {expected}. Ada kode yang menulis status di luar "
        f"recompute_funding_status() (D-05)."
    )


OPERATION_SEQUENCES = [
    pytest.param(["pledge_30", "pledge_70"], id="rises-to-full"),
    pytest.param(["pledge_30", "cancel_30"], id="returns-to-empty"),
    pytest.param(["pledge_30", "pledge_30", "cancel_30"], id="drops-partially"),
    pytest.param(["pledge_100"], id="funded-immediately"),
    pytest.param(["pledge_30", "pass_deadline"], id="fails-mid-way"),
]


@pytest.fixture
def run_operation(db, investor, clock):
    """Satu langkah skenario R2b: `pledge_NN` membuat pledge NN% dari
    requested_amount, `cancel_NN` membatalkan pledge NN% yang paling baru
    dibuat, `pass_deadline` memajukan jam ke sesudah funding_deadline lalu
    memicu recompute_funding_status seperti yang nanti dilakukan endpoint
    tick (D-06), bukan menulis status langsung."""
    pledges_by_label: dict[str, list[Pledge]] = defaultdict(list)

    async def _run(step: str, proposal: Proposal) -> None:
        if step == "pass_deadline":
            campaign = await db.get(Campaign, proposal.campaign_id)
            clock.advance_to(campaign.funding_deadline + timedelta(seconds=1))
            await recompute_funding_status(db, proposal, clock)
            return

        action, label = step.split("_", 1)
        if action == "pledge":
            amount = proposal.requested_amount * int(label) // 100
            pledge = await create_pledge(db, investor.user, proposal, amount, clock)
            pledges_by_label[label].append(pledge)
        elif action == "cancel":
            pledge = pledges_by_label[label].pop()
            await cancel_pledge(db, proposal, pledge, clock)
        else:
            raise ValueError(f"operasi tidak dikenal: {step}")

    return _run


@pytest.mark.parametrize("operations", OPERATION_SEQUENCES)
async def test_r2b_status_matches_active_pledges_after_every_operation(
    db, listed_proposal, clock, run_operation, operations
):
    for step in operations:
        await run_operation(step, listed_proposal)
        await db.refresh(listed_proposal)
        await check_consistency(db, listed_proposal, clock)


async def test_r2b_funded_always_means_total_equals_requested(db, funded_proposal):
    total = await total_pledge_aktif(db, funded_proposal.id)
    assert funded_proposal.status is ProposalStatus.FUNDED
    assert total == funded_proposal.requested_amount

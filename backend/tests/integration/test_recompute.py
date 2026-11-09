"""recompute_funding_status: satu-satunya penulis listed/partially_funded/funded (D-05).

Fixture `pledge` dan `batalkan` di sini menulis Pledge dan entri ledger
secara langsung, bukan lewat `buat_pledge`/`batalkan_pledge` dengan
penguncian baris: keduanya milik task berikutnya. Test ini hanya menguji
recompute_funding_status, bukan jalur HTTP pledge sungguhan.
"""

import pytest

from app.models.ledger import EntryType
from app.models.pledge import Pledge, PledgeStatus

# ProposalStatus dari app.models.proposal, bukan dari app.domain.transitions
# seperti di brief: keduanya kelas enum terpisah dengan nilai string yang
# sama, dan recompute_funding_status menulis kolomnya lewat tipe model
# (lihat services/pledge.py). Perbandingan `is` di bawah akan selalu gagal
# kalau S diimpor dari domain, meski nilainya sama persis.
from app.models.proposal import ProposalStatus as S
from app.services.ledger import record_entry
from app.services.pledge import recompute_funding_status


@pytest.fixture
def pledge(db, clock):
    async def _pledge(proposal, investor_akun, amount: int) -> Pledge:
        p = Pledge(
            proposal_id=proposal.id,
            investor_id=investor_akun.user.id,
            amount=amount,
            status=PledgeStatus.ACTIVE,
            created_at=clock.now(),
        )
        db.add(p)
        await db.flush()
        await record_entry(
            db, proposal.id, EntryType.PLEDGE_IN, amount, f"pledge:{p.id}", clock=clock
        )
        return p

    return _pledge


@pytest.fixture
def batalkan(db, clock):
    async def _batalkan(p: Pledge) -> None:
        p.status = PledgeStatus.CANCELLED
        await record_entry(
            db,
            p.proposal_id,
            EntryType.REFUND_OUT,
            p.amount,
            f"refund:{p.id}",
            clock=clock,
        )
        await db.flush()

    return _batalkan


async def test_status_mengikuti_jumlah_pledge(
    db, listed_proposal, investor, clock, pledge
):
    await pledge(listed_proposal, investor, 4_000_000)  # diminta 10 juta
    await recompute_funding_status(db, listed_proposal, clock)
    assert listed_proposal.status is S.PARTIALLY_FUNDED

    await pledge(listed_proposal, investor, 6_000_000)
    await recompute_funding_status(db, listed_proposal, clock)
    assert listed_proposal.status is S.FUNDED


async def test_t07_semua_pledge_dibatalkan_mengembalikan_ke_listed(
    db, listed_proposal, investor, clock, pledge, batalkan
):
    p = await pledge(listed_proposal, investor, 4_000_000)
    await recompute_funding_status(db, listed_proposal, clock)
    await batalkan(p)
    await recompute_funding_status(db, listed_proposal, clock)
    assert listed_proposal.status is S.LISTED


async def test_recompute_juga_memperbarui_lead_investor(
    db, listed_proposal, investor, investor_lain, clock, pledge
):
    await pledge(listed_proposal, investor, 3_000_000)
    await pledge(listed_proposal, investor_lain, 7_000_000)
    await recompute_funding_status(db, listed_proposal, clock)
    assert listed_proposal.lead_investor_id == investor_lain.user.id

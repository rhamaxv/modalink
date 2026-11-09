"""Penulis tunggal status funding (D-05).

`buat_pledge` dan `batalkan_pledge` dengan penguncian baris proposal
(`SELECT ... FOR UPDATE`) dibangun di task berikutnya. Modul ini hanya berisi
`recompute_funding_status`, fondasi yang keduanya wajib panggil di transaksi
yang sama setelah mengubah pledge.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.clock import Clock
from app.domain.funding import compute_funding_status
from app.domain.lead_investor import PledgeRingkas, pick_lead_investor
from app.models.campaign import Campaign
from app.models.pledge import Pledge, PledgeStatus
from app.models.proposal import Proposal, ProposalStatus


async def recompute_funding_status(
    session: AsyncSession, proposal: Proposal, clock: Clock
) -> None:
    """Satu-satunya penulis status funding yang didorong pledge: `listed`,
    `partially_funded`, dan `funded` (D-05).

    Bukan satu-satunya penulis `proposal.status` secara keseluruhan: T-01
    (`submitted` -> `listed` saat scoring lolos, lihat
    `services/scoring.py:_majukan_proposal`) adalah pelistingan awal, bukan
    akibat pledge, dan sengaja tidak lewat sini. Service yang mengubah pledge
    wajib memanggil fungsi ini di transaksi yang sama. Regression test R2b
    yang menegakkannya.
    """
    aktif = (
        await session.scalars(
            select(Pledge).where(
                Pledge.proposal_id == proposal.id,
                Pledge.status == PledgeStatus.ACTIVE,
            )
        )
    ).all()

    campaign = await session.get(Campaign, proposal.campaign_id)
    if campaign is None:
        # Praktis mustahil: proposal.campaign_id adalah foreign key yang
        # menjamin keberadaannya. Dianggap sebagai pelanggaran invarian, bukan
        # kondisi yang perlu diterjemahkan jadi DomainError, karena tidak ada
        # pemanggil yang bisa memulihkan diri darinya.
        raise RuntimeError(
            f"Proposal {proposal.id} merujuk campaign yang tidak ada: "
            f"{proposal.campaign_id}."
        )

    total = sum(p.amount for p in aktif)

    # ProposalStatus(baru.value), bukan assignment langsung: compute_funding_status
    # mengembalikan tipe app.domain.transitions.ProposalStatus, kelas berbeda
    # dari tipe kolom app.models.proposal.ProposalStatus meski nilai stringnya
    # sama (lihat catatan _majukan_proposal di services/scoring.py).
    baru = compute_funding_status(
        total, proposal.requested_amount, clock.now(), campaign.funding_deadline
    )
    proposal.status = ProposalStatus(baru.value)
    proposal.lead_investor_id = pick_lead_investor(
        [PledgeRingkas(p.investor_id, p.amount, p.created_at) for p in aktif]
    )
    if proposal.status is ProposalStatus.FUNDED and proposal.funded_at is None:
        proposal.funded_at = clock.now()
    await session.flush()

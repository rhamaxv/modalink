"""Pledge, pembatalannya, dan penulis tunggal status funding (D-05).

`create_pledge` dan `cancel_pledge` selalu menerima proposal yang sudah
dikunci lewat `get_locked_proposal` (RF-1): tanpa itu dua pledge nyaris
bersamaan sama-sama membaca sisa dana yang sama dan sama-sama lolos.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.clock import Clock
from app.domain.funding import compute_funding_status, remaining_amount
from app.domain.lead_investor import PledgeRingkas, pick_lead_investor
from app.domain.money import format_rupiah
from app.errors import ConflictError, NotFoundError
from app.models.campaign import Campaign
from app.models.ledger import EntryType
from app.models.pledge import Pledge, PledgeStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.user import User
from app.services.ledger import catat_entri, total_terkumpul_proposal

# BR-20: hanya proposal pada status ini yang boleh menerima pledge baru.
PROPOSAL_STATUS_BISA_DIDANAI = {ProposalStatus.LISTED, ProposalStatus.PARTIALLY_FUNDED}


async def get_locked_proposal(session: AsyncSession, proposal_id: UUID) -> Proposal:
    """Mengunci baris proposal sampai transaksi selesai (RF-1, RF-4, RF-5).

    Setiap operasi yang membaca lalu menulis uang pada satu proposal wajib
    lewat sini, bukan `session.get(Proposal, ...)`. Tanpa `FOR UPDATE`, dua
    request bersamaan sama-sama membaca sisa yang sama lalu sama-sama lolos
    (lihat test_pagar_penguncian.py dan test_rf1_* di
    tests/integration/test_pledge_concurrency.py).
    """
    proposal = await session.scalar(
        select(Proposal).where(Proposal.id == proposal_id).with_for_update()
    )
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return proposal


async def get_pledge(session: AsyncSession, pledge_id: UUID) -> Pledge | None:
    """Pledge tunggal lewat PK, dipakai dependency kepemilikan di api/deps.py.

    Bukan Proposal, jadi tidak kena pagar test_pagar_penguncian.py: pledge
    tidak pernah dikunci sendiri, locking selalu lewat baris proposal
    induknya di get_locked_proposal.
    """
    return await session.get(Pledge, pledge_id)


async def create_pledge(
    session: AsyncSession,
    investor: User,
    proposal: Proposal,
    amount: int,
    clock: Clock,
) -> Pledge:
    """Mencatat pledge baru dan menghitung ulang status funding (BR-20 sampai
    BR-24, BR-27, D-11, D-12). `proposal` wajib hasil `get_locked_proposal`."""
    if proposal.status not in PROPOSAL_STATUS_BISA_DIDANAI:
        # Brief task ini hanya menyebut pemeriksaan sisa dana (D-11); tanpa
        # pagar ini, proposal submitted yang belum lolos scoring bisa
        # langsung melompat ke partially_funded lewat recompute_funding_status
        # di bawah, melanggar BR-20.
        raise ConflictError(
            "proposal_belum_bisa_didanai",
            "Proposal ini belum bisa menerima pledge.",
        )

    sisa = remaining_amount(
        await total_terkumpul_proposal(session, proposal.id), proposal.requested_amount
    )
    if amount > sisa:
        raise ConflictError(
            "pledge_melebihi_sisa",
            f"Pledge melebihi sisa dana yang dibutuhkan, sisa {format_rupiah(sisa)}.",
            detail={"remaining_amount": sisa},
        )

    pledge = Pledge(
        proposal_id=proposal.id,
        investor_id=investor.id,
        amount=amount,
        status=PledgeStatus.ACTIVE,
        created_at=clock.now(),
    )
    session.add(pledge)
    await session.flush()

    await catat_entri(
        session,
        proposal.id,
        EntryType.PLEDGE_IN,
        amount,
        idempotency_key=f"pledge:{pledge.id}",
        ref_type="pledge",
        ref_id=pledge.id,
        actor_id=investor.id,
    )
    await recompute_funding_status(session, proposal, clock)
    return pledge


async def cancel_pledge(
    session: AsyncSession, proposal: Proposal, pledge: Pledge, clock: Clock
) -> Pledge:
    """Membatalkan pledge: mencatat refund, bukan menghapus (BR-25, BR-26).
    `proposal` wajib hasil `get_locked_proposal` dan harus proposal pemilik
    `pledge` (pemanggil yang menjamin pasangan ini benar)."""
    if proposal.status is ProposalStatus.FUNDED:
        raise ConflictError(
            "proposal_sudah_funded",
            "Pledge tidak bisa dibatalkan karena proposal sudah funded.",
        )
    if pledge.status is not PledgeStatus.ACTIVE:
        raise ConflictError(
            "pledge_sudah_batal",
            "Pledge ini sudah dibatalkan sebelumnya.",
        )

    # Assignment langsung, bukan lewat domain/transitions.py: PledgeStatus
    # bukan satu dari empat mesin status terpusat (proposal, milestone,
    # laporan, campaign), hanya status dua nilai tanpa matriks transisi.
    pledge.status = PledgeStatus.CANCELLED
    session.add(pledge)
    await session.flush()

    await catat_entri(
        session,
        proposal.id,
        EntryType.REFUND_OUT,
        pledge.amount,
        idempotency_key=f"refund:{pledge.id}",
        ref_type="pledge",
        ref_id=pledge.id,
        actor_id=pledge.investor_id,
    )
    await recompute_funding_status(session, proposal, clock)
    return pledge


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

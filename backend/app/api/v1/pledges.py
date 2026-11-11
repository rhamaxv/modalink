"""Endpoint pledge dan pembatalan (BR-20 sampai BR-28, D-11, D-12)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    current_user,
    get_clock,
    get_own_pledge,
    get_proposal_for_pledge_listing,
    require_role,
)
from app.db.session import get_session
from app.domain.clock import Clock
from app.models.pledge import Pledge
from app.models.proposal import Proposal
from app.models.user import Role, User
from app.schemas.ledger import LedgerEntryPublicOut, LedgerPublicOut
from app.schemas.pledge import PledgeIn, PledgeListOut, PledgeOut
from app.services.kyc import require_verified
from app.services.ledger import (
    EntryType,
    LedgerEntrySummary,
    get_proposal_ledger,
    total_raised,
)
from app.services.pledge import (
    cancel_pledge,
    create_pledge,
    get_locked_proposal,
    list_active_pledges,
)

router = APIRouter(tags=["pledges"])


@router.post(
    "/api/v1/proposals/{proposal_id}/pledges",
    status_code=status.HTTP_201_CREATED,
    response_model=PledgeOut,
)
async def create_pledge_endpoint(
    proposal_id: UUID,
    body: PledgeIn,
    investor: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Pledge:
    # Gerbang identitas sebelum baris proposal dikunci: menguncinya lebih
    # dulu untuk permintaan yang pasti ditolak hanya menahan investor lain
    # yang sedang mendanai proposal yang sama.
    await require_verified(session, investor, "mendanai proposal")
    proposal = await get_locked_proposal(session, proposal_id)
    return await create_pledge(session, investor, proposal, body.amount, clock)


@router.get("/api/v1/proposals/{proposal_id}/pledges", response_model=PledgeListOut)
async def list_pledges_endpoint(
    proposal: Proposal = Depends(get_proposal_for_pledge_listing),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> PledgeListOut:
    # `user` dioper supaya pledge milik pemanggil sendiri tidak ikut
    # disamarkan darinya (lihat docstring list_active_pledges). Endpoint ini
    # memang sudah menuntut autentikasi lewat
    # get_proposal_for_pledge_listing, jadi tidak ada jalur anonim di sini.
    return PledgeListOut(
        items=await list_active_pledges(session, proposal, pemanggil=user)
    )


@router.delete("/api/v1/pledges/{pledge_id}", response_model=PledgeOut)
async def cancel_pledge_endpoint(
    pledge: Pledge = Depends(get_own_pledge),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Pledge:
    proposal = await get_locked_proposal(session, pledge.proposal_id)
    return await cancel_pledge(session, proposal, pledge, clock)


@router.get(
    "/api/v1/proposals/{proposal_id}/ledger",
    response_model=LedgerPublicOut,
)
async def get_proposal_ledger_endpoint(
    proposal: Proposal = Depends(get_proposal_for_pledge_listing),
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> LedgerPublicOut:
    """Riwayat pergerakan dana satu proposal, untuk pihak yang uangnya ada di
    dalamnya.

    Catatan ini sudah ada sejak awal dan sudah append-only, tapi satu-satunya
    jalan membacanya adalah `GET /internal/ledger/{id}` yang HANYA hidup saat
    ENV=dev (BR-63). Di produksi, investor yang menaruh uang dan UMKM yang
    menerimanya sama-sama tidak bisa melihat apa pun. Bukti yang tidak bisa
    dilihat pemiliknya belum benar-benar jadi bukti.

    Pagar aksesnya memakai dependency yang sama persis dengan daftar pledge
    (get_proposal_for_pledge_listing): investor mana pun boleh membaca, UMKM
    hanya proposalnya sendiri, dan UMKM lain dibalas 404 supaya keberadaan
    proposal tidak terbuka untuk mereka. Identitas pelaku tiap baris tidak
    ikut dikirim sama sekali kecuali baris itu milik pemanggil sendiri;
    lihat docstring LedgerEntryPublicOut.
    """
    entri, saldo = await get_proposal_ledger(session, proposal.id)
    ringkas = [
        LedgerEntrySummary(entry_type=e.entry_type, amount=e.amount) for e in entri
    ]
    return LedgerPublicOut(
        entries=[
            LedgerEntryPublicOut(
                id=e.id,
                entry_type=e.entry_type,
                amount=e.amount,
                ref_type=e.ref_type,
                created_at=e.created_at,
                milik_saya=e.actor_id == user.id,
            )
            for e in entri
        ],
        balance=saldo,
        total_masuk=total_raised(ringkas),
        total_cair=sum(
            e.amount for e in ringkas if e.entry_type is EntryType.DISBURSEMENT_OUT
        ),
    )

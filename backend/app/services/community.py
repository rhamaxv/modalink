"""Orkestrasi vote dan komentar komunitas (BR-30 sampai BR-34).

Fase ini sengaja kecil: batasan yang harus dijaga bukan ukuran fitur,
melainkan satu invarian (BR-31) -- vote tidak pernah mengubah status
proposal. Lihat toggle_vote di bawah.
"""

from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.domain.clock import Clock
from app.errors import ConflictError
from app.models.comment import Comment
from app.models.proposal import Proposal
from app.models.user import User
from app.models.vote import Vote
from app.services.campaign import STATUS_PROPOSAL_PUBLIK

# BR-30: "listed ke atas" adalah definisi yang sama dipakai untuk kelihatan
# publik (services/campaign.py) -- proposal yang belum listed memang belum
# pernah ditampilkan ke siapa pun selain pemiliknya, jadi tidak ada yang bisa
# ia vote atau komentari.
DAPAT_DIVOTE_DAN_DIKOMENTARI = STATUS_PROPOSAL_PUBLIK


async def hitung_vote(session: AsyncSession, proposal_id: UUID) -> int:
    jumlah = await session.scalar(
        select(func.count()).select_from(Vote).where(Vote.proposal_id == proposal_id)
    )
    return jumlah or 0


async def toggle_vote(
    session: AsyncSession, user: User, proposal: Proposal
) -> tuple[bool, int]:
    if proposal.status not in DAPAT_DIVOTE_DAN_DIKOMENTARI:
        raise ConflictError(
            "proposal_belum_terbuka",
            "Proposal ini belum terbuka untuk dukungan publik.",
        )

    ada = await session.scalar(
        select(Vote).where(Vote.proposal_id == proposal.id, Vote.user_id == user.id)
    )
    if ada:
        await session.delete(ada)
        voted = False
    else:
        session.add(Vote(proposal_id=proposal.id, user_id=user.id))
        voted = True
    await session.flush()

    # Status proposal sengaja TIDAK disentuh di sini (BR-31). Vote adalah
    # sinyal bagi investor, bukan mekanisme promosi: proposal yang viral
    # tidak boleh mengalahkan proposal yang lebih baik secara AI dan
    # pendanaan semata karena jejaring sosialnya lebih luas.
    jumlah = await hitung_vote(session, proposal.id)
    return voted, jumlah


async def buat_komentar(
    session: AsyncSession, user: User, proposal: Proposal, body: str, clock: Clock
) -> Comment:
    if proposal.status not in DAPAT_DIVOTE_DAN_DIKOMENTARI:
        raise ConflictError(
            "proposal_belum_terbuka",
            "Proposal ini belum terbuka untuk komentar publik.",
        )
    komentar = Comment(
        proposal_id=proposal.id, user_id=user.id, body=body, created_at=clock.now()
    )
    session.add(komentar)
    await session.flush()
    return komentar


async def daftar_komentar(session: AsyncSession, proposal_id: UUID) -> list[Comment]:
    hasil = await session.scalars(
        select(Comment)
        .where(Comment.proposal_id == proposal_id, col(Comment.deleted_at).is_(None))
        .order_by(desc("created_at"), desc("id"))
    )
    return list(hasil)


async def ambil_komentar_aktif(
    session: AsyncSession, comment_id: UUID
) -> Comment | None:
    """Komentar yang belum dihapus. Komentar yang sudah soft-deleted dianggap
    tidak ada lagi untuk pemeriksaan kepemilikan maupun penghapusan ulang."""
    komentar = await session.get(Comment, comment_id)
    if komentar is None or komentar.deleted_at is not None:
        return None
    return komentar


async def hapus_komentar(
    session: AsyncSession, komentar: Comment, clock: Clock
) -> None:
    """Soft delete (BR-34). `komentar` wajib hasil `get_own_comment`, yang
    sudah memastikan kepemilikan -- sama seperti cancel_pledge mempercayai
    `get_own_pledge`, pemeriksaan kepemilikan tidak diulang di sini."""
    komentar.deleted_at = clock.now()
    session.add(komentar)
    await session.flush()

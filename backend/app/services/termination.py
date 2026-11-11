"""Penghentian proposal yang sudah penuh tapi tahapnya macet.

Menutup satu-satunya jalan buntu yang tersisa di aliran dana produk ini:
proposal `funded` yang UMKM-nya berhenti melapor. Lihat
app/domain/termination.py untuk aturan waktunya dan alasan bentuknya.

Alurnya dua langkah, bukan satu, dan itu disengaja:

    tahap macet 30 hari
        -> lead investor MENGAJUKAN penghentian
            -> UMKM melapor dalam 7 hari  => pengajuan batal, lanjut normal
            -> UMKM diam 7 hari           => sisa dana kembali pro-rata,
                                             proposal jadi failed

Penghentian satu langkah akan memberi lead investor hak menarik dana kapan
saja setelah tahap lewat tenggat, termasuk ketika UMKM sebenarnya sedang
mengerjakannya. Jendela jawaban itulah yang membuat aturan ini berlaku untuk
kedua pihak, bukan hanya untuk yang memegang uang.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.domain.clock import Clock
from app.domain.refund_split import KontribusiPledge, bagi_sisa_pro_rata
from app.domain.termination import jendela_jawaban_habis, tahap_macet
from app.domain.transitions import ProposalEvent
from app.errors import ConflictError, NotFoundError
from app.models.ledger import EntryType
from app.models.pledge import Pledge, PledgeStatus
from app.models.proposal import MilestoneStatus, Proposal, ProposalMilestone
from app.models.user import User
from app.services.ledger import record_entry
from app.services.status import advance_proposal


async def _milestone_terurut(
    session: AsyncSession, proposal_id
) -> list[ProposalMilestone]:
    return list(
        await session.scalars(
            select(ProposalMilestone)
            .where(ProposalMilestone.proposal_id == proposal_id)
            .order_by(col(ProposalMilestone.seq))
        )
    )


async def tahap_berikutnya_macet(
    session: AsyncSession, proposal: Proposal, clock: Clock
) -> bool:
    """Apakah tahap berikutnya sudah lewat tenggat laporannya.

    Diukur dari kapan tahap SEBELUMNYA cair, bukan dari kolom tenggat
    tersendiri: jam sebuah tahap baru mulai berjalan ketika dananya benar-benar
    ada di tangan UMKM, dan menyimpan tenggat sendiri akan membuat dua sumber
    kebenaran yang bisa berbeda setelah sebuah tahap ditolak lalu dilaporkan
    ulang.
    """
    tahapan = await _milestone_terurut(session, proposal.id)
    sebelumnya = None
    for m in tahapan:
        if m.status is MilestoneStatus.DISBURSED:
            sebelumnya = m
            continue
        # Tahap pertama yang belum cair. Kalau ia sudah dilaporkan, bolanya
        # ada di lead investor, bukan di UMKM, jadi ia tidak bisa disebut
        # macet oleh pihak yang justru sedang ditunggu.
        if m.status is MilestoneStatus.REPORTED:
            return False
        return tahap_macet(
            sebelumnya.disbursed_at if sebelumnya is not None else None, clock.now()
        )
    return False  # seluruh tahap sudah cair


async def request_termination(
    session: AsyncSession, proposal: Proposal, aktor: User, clock: Clock
) -> Proposal:
    """Lead investor mengajukan penghentian. Belum mengembalikan dana apa pun."""
    # 404, bukan 403: investor yang bukan lead tidak boleh sekaligus
    # mengonfirmasi keberadaan proposal ini, pola yang sama dengan
    # approve_milestone.
    if proposal.lead_investor_id != aktor.id:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    if proposal.status.value != "funded":
        raise ConflictError(
            "proposal_tidak_bisa_dihentikan",
            "Penghentian hanya berlaku untuk proposal yang dananya sudah penuh.",
        )
    if proposal.termination_requested_at is not None:
        raise ConflictError(
            "penghentian_sudah_diajukan",
            "Penghentian untuk proposal ini sudah diajukan dan masih menunggu jawaban UMKM.",
        )
    if not await tahap_berikutnya_macet(session, proposal, clock):
        raise ConflictError(
            "tahap_belum_macet",
            "Tahap berikutnya belum melewati tenggat laporannya, "
            "jadi penghentian belum bisa diajukan.",
        )

    proposal.termination_requested_at = clock.now()
    session.add(proposal)
    await session.flush()
    return proposal


async def cancel_termination(session: AsyncSession, proposal: Proposal) -> None:
    """Membatalkan pengajuan penghentian karena UMKM akhirnya melapor.

    Dipanggil dari submit_report. Tidak memeriksa apakah jendelanya masih
    terbuka: pemeriksaan itu milik finalize_termination, dan laporan yang
    masuk setelah dana terlanjur kembali tidak akan pernah sampai ke sini
    karena proposalnya sudah failed.
    """
    if proposal.termination_requested_at is None:
        return
    proposal.termination_requested_at = None
    session.add(proposal)
    await session.flush()


async def finalize_termination(
    session: AsyncSession, proposal: Proposal, clock: Clock
) -> bool:
    """Menuntaskan penghentian yang jendela jawabannya sudah habis.

    Mengembalikan True kalau dana benar-benar dikembalikan. Idempoten:
    kunci idempotensi refund berasal dari pledge, jadi pembacaan berulang
    tidak pernah menghasilkan entri ganda (BR-55).
    """
    if proposal.status.value != "funded":
        return False
    if not jendela_jawaban_habis(proposal.termination_requested_at, clock.now()):
        return False

    aktif = list(
        await session.scalars(
            select(Pledge).where(
                Pledge.proposal_id == proposal.id,
                Pledge.status == PledgeStatus.ACTIVE,
            )
        )
    )
    # Sisa yang dikembalikan adalah saldo yang BELUM cair, bukan nominal
    # pledge utuh: sebagian sudah diterima UMKM lewat milestone yang
    # disetujui, dan uang itu tidak ditarik kembali oleh mekanisme ini.
    terkumpul = sum(p.amount for p in aktif)
    sudah_cair = sum(
        m.amount
        for m in await _milestone_terurut(session, proposal.id)
        if m.status is MilestoneStatus.DISBURSED
    )
    sisa = terkumpul - sudah_cair

    if sisa > 0 and aktif:
        bagian = bagi_sisa_pro_rata(
            [KontribusiPledge(p.id, p.investor_id, p.amount) for p in aktif], sisa
        )
        for p in aktif:
            nominal = bagian.get(p.id, 0)
            if nominal <= 0:
                continue
            await record_entry(
                session,
                proposal.id,
                EntryType.REFUND_OUT,
                nominal,
                idempotency_key=f"terminate-refund:{p.id}",
                clock=clock,
                ref_type="pledge",
                ref_id=p.id,
                actor_id=p.investor_id,
            )

    # Pledge ditandai cancelled SETELAH refundnya tercatat: urutan terbalik
    # akan membuat baris refund kehilangan daftar pledge aktif yang
    # dipakainya menghitung bagian.
    for p in aktif:
        p.status = PledgeStatus.CANCELLED

    advance_proposal(proposal, ProposalEvent.PENGHENTIAN_TUNTAS)
    proposal.termination_requested_at = None
    session.add(proposal)
    await session.flush()
    return True

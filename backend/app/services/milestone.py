"""Orkestrasi laporan progres milestone dan review lead investor
(BR-41 sampai BR-46, T-20 sampai T-23, T-30, T-31).

approve_milestone dan reject_milestone menyentuh `Proposal` lewat
`get_locked_proposal` (dipinjam dari services/pledge.py, bukan diduplikasi:
docstringnya sendiri sudah menyebut RF-5 sebagai pemakai yang dituju) untuk
dua alasan sekaligus: BR-44 (hanya lead investor yang boleh approve/reject,
dan identitasnya dibaca dari kolom `lead_investor_id` milik baris proposal
itu) dan RF-5 (approve mencairkan uang, jadi baris proposal harus terkunci
sebelum pemeriksaan apa pun dibaca, bukan sesudahnya). Karena modul ini kini
menyentuh Proposal, tests/unit/test_proposal_lock_guard.py mewajibkan semua
aksesnya lewat baris yang terkunci -- menulis session.get(Proposal, ...)
atau select(Proposal) tanpa with_for_update() di sini akan membuatnya merah.
"""

from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.clock import Clock
from app.domain.milestone_rules import can_be_reported
from app.domain.transitions import IllegalTransition, MilestoneEvent, ReportEvent
from app.domain.transitions import MilestoneStatus as DomainMilestoneStatus
from app.errors import ConflictError, NotFoundError
from app.models.milestone_report import MilestoneReport, ReportStatus
from app.models.proposal import ProposalMilestone
from app.models.user import User
from app.schemas.milestone import MilestoneReportIn
from app.services.pledge import get_locked_proposal
from app.services.status import advance_milestone, advance_report


async def get_milestone(
    session: AsyncSession, milestone_id: UUID
) -> ProposalMilestone | None:
    return await session.get(ProposalMilestone, milestone_id)


async def get_previous_milestone(
    session: AsyncSession, milestone: ProposalMilestone
) -> ProposalMilestone | None:
    if milestone.seq <= 1:
        return None
    return await session.scalar(
        select(ProposalMilestone).where(
            ProposalMilestone.proposal_id == milestone.proposal_id,
            ProposalMilestone.seq == milestone.seq - 1,
        )
    )


async def get_latest_report(
    session: AsyncSession, milestone_id: UUID
) -> MilestoneReport | None:
    # Nama kolom sebagai string, bukan MilestoneReport.submitted_at.desc():
    # atribut kelas SQLModel diketik sebagai datetime biasa oleh mypy (tidak
    # ada plugin sqlmodel), sama seperti catatan di services/scoring.py.
    return await session.scalar(
        select(MilestoneReport)
        .where(MilestoneReport.milestone_id == milestone_id)
        .order_by(desc("submitted_at"))
        .limit(1)
    )


async def submit_report(
    session: AsyncSession,
    umkm: User,
    milestone: ProposalMilestone,
    body: MilestoneReportIn,
    clock: Clock,
) -> MilestoneReport:
    previous = await get_previous_milestone(session, milestone)
    # Jembatan nilai, bukan assignment langsung: MilestoneStatus di models/
    # berbeda kelas dari MilestoneStatus di domain/transitions.py (lihat
    # docstring app/services/status.py), tapi nilai stringnya sama sehingga
    # can_be_reported tetap bisa dipanggil. Bukan apply_*, jadi di luar
    # cakupan tests/unit/test_transition_guard.py: ini hanya membaca, bukan
    # menulis transisi status.
    previous_status = (
        DomainMilestoneStatus(previous.status.value) if previous is not None else None
    )
    if not can_be_reported(milestone.seq, previous_status):
        code = (
            "milestone_pertama_tanpa_laporan"
            if milestone.seq == 1
            else "milestone_sebelumnya_belum_cair"
        )
        raise ConflictError(code, "Milestone ini belum bisa dilaporkan.")

    try:
        advance_milestone(milestone, MilestoneEvent.LAPOR)  # T-20
    except IllegalTransition:
        # can_be_reported di atas hanya melihat milestone sebelumnya; ini
        # menangkap milestone ITU SENDIRI yang sudah punya laporan menunggu
        # review (reported) atau sudah cair (disbursed).
        raise ConflictError(
            "milestone_tidak_bisa_dilaporkan",
            "Milestone ini sudah punya laporan menunggu review, atau sudah cair.",
        ) from None

    report = MilestoneReport(
        milestone_id=milestone.id,
        umkm_id=umkm.id,
        narrative=body.narrative,
        metrics=body.metrics,
        review_status=ReportStatus.PENDING,
        submitted_at=clock.now(),
    )
    session.add(report)
    await session.flush()
    return report


async def approve_milestone(
    session: AsyncSession, milestone: ProposalMilestone, aktor: User, clock: Clock
) -> ProposalMilestone:
    # BR-44: kunci baris proposal dulu, baca identitas lead investor sesudahnya
    # (RF-5 -- approve mencairkan uang, jadi urutannya tidak boleh dibalik).
    # 404, bukan 403, sama seperti get_own_milestone_for_report di api/deps.py:
    # investor yang bukan lead tidak boleh sekaligus mengonfirmasi keberadaan
    # milestone ini.
    proposal = await get_locked_proposal(session, milestone.proposal_id)
    if proposal.lead_investor_id != aktor.id:
        raise NotFoundError("milestone_tidak_ada", "Milestone tidak ditemukan.")

    # D-13: seq=1 cair tanpa laporan (T-21); seq lainnya wajib lewat laporan
    # yang disetujui (T-22). MILESTONE_MAP sendiri tidak tahu soal seq, jadi
    # pemilihan event ini yang menegakkan pembatasan "hanya seq=1" dari D-13.
    event = (
        MilestoneEvent.APPROVE_TANPA_LAPORAN
        if milestone.seq == 1
        else MilestoneEvent.APPROVE
    )
    try:
        advance_milestone(milestone, event)
    except IllegalTransition:
        raise ConflictError(
            "milestone_tidak_bisa_disetujui",
            "Milestone ini tidak bisa disetujui pada status sekarang.",
        ) from None

    if event is MilestoneEvent.APPROVE:
        report = await get_latest_report(session, milestone.id)
        if report is None or report.review_status is not ReportStatus.PENDING:
            raise RuntimeError(
                f"Milestone {milestone.id} baru disetujui dari status reported "
                "tapi tidak punya laporan pending."
            )
        advance_report(report, ReportEvent.APPROVE)  # T-30
        report.reviewed_by = aktor.id
        report.reviewed_at = clock.now()

    await session.flush()
    return milestone


async def reject_milestone(
    session: AsyncSession,
    milestone: ProposalMilestone,
    aktor: User,
    note: str,
    clock: Clock,
) -> ProposalMilestone:
    # BR-44: sama seperti approve_milestone di atas -- identitas lead investor
    # dibaca lewat baris proposal yang terkunci, bukan session.get biasa.
    proposal = await get_locked_proposal(session, milestone.proposal_id)
    if proposal.lead_investor_id != aktor.id:
        raise NotFoundError("milestone_tidak_ada", "Milestone tidak ditemukan.")

    try:
        advance_milestone(milestone, MilestoneEvent.REJECT)  # T-23
    except IllegalTransition:
        raise ConflictError(
            "milestone_belum_dilaporkan",
            "Milestone ini belum punya laporan untuk ditolak.",
        ) from None

    report = await get_latest_report(session, milestone.id)
    if report is None or report.review_status is not ReportStatus.PENDING:
        raise RuntimeError(
            f"Milestone {milestone.id} baru ditolak dari status reported "
            "tapi tidak punya laporan pending."
        )
    advance_report(report, ReportEvent.REJECT)  # T-31
    report.reviewer_note = note
    report.reviewed_by = aktor.id
    report.reviewed_at = clock.now()

    await session.flush()
    return milestone

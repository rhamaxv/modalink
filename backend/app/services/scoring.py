"""Orkestrasi scoring: jalankan satu percobaan, dan picu ulang saat gagal
(BR-70 sampai BR-78, D-09).

Jembatan nilai antar-enum domain dan model (ProposalStatus/ScoringStatus di
app.models.proposal adalah tipe kolom database, beda kelas dari pasangannya
di app.domain.transitions yang dipakai mesin transisi, meski nilai stringnya
sama) tidak lagi ditulis di sini: dipusatkan di app/services/status.py
(advance_proposal, advance_scoring), lihat docstring modul itu.
"""

from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import cast
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.ai.engine import CampaignLike, ScoringEngine
from app.db.session import SessionLocal
from app.domain.clock import Clock
from app.domain.transitions import IllegalTransition, ProposalEvent, ScoringEvent
from app.domain.verdict import Verdict, decide_verdict, total_score
from app.errors import ConflictError, NotFoundError
from app.models.campaign import Campaign
from app.models.proposal import Proposal, ProposalStatus, ScoringStatus
from app.models.scoring import ScoringResult, ScoringVerdict
from app.services.status import advance_proposal, advance_scoring

SessionFactory = Callable[[], AbstractAsyncContextManager[AsyncSession]]


async def run_scoring(
    session: AsyncSession, proposal_id: UUID, engine: ScoringEngine, clock: Clock
) -> None:
    proposal = await session.get(Proposal, proposal_id)
    if proposal is None or proposal.status is not ProposalStatus.SUBMITTED:
        return  # compare-and-set: job kedua tidak melakukan apa-apa (BR-75)

    advance_scoring(proposal, ScoringEvent.AMBIL)  # T-50
    await session.flush()

    campaign = await session.get(Campaign, proposal.campaign_id)
    if campaign is None:
        # Praktis mustahil (FK menjamin keberadaannya), tapi mypy tidak tahu
        # itu; dianggap kegagalan teknis yang sama seperti exception di bawah,
        # bukan AttributeError yang bocor keluar jalur D-09.
        advance_scoring(proposal, ScoringEvent.GAGAL)  # T-52
        await session.flush()
        return
    mulai = clock.now()
    try:
        # cast, bukan perbaikan tipe: Campaign.sector bertipe Sector, subclass
        # str yang benar secara runtime, tapi mypy memeriksa atribut Protocol
        # secara invarian sehingga Sector tidak dianggap cocok dengan
        # CampaignLike.sector: str apa adanya.
        skor = await engine.score(proposal, cast(CampaignLike, campaign))
    except Exception:  # noqa: BLE001
        # Blind kecuali disengaja: timeout, error jaringan, ValueError validasi
        # schema, atau RuntimeError kunci API tidak ada semuanya harus jatuh
        # ke jalur yang sama (D-09, BR-74). proposal.status sengaja tidak
        # disentuh, hanya scoring_status.
        advance_scoring(proposal, ScoringEvent.GAGAL)  # T-52
        await session.flush()
        return

    verdict = decide_verdict(skor, campaign.score_threshold)
    session.add(
        ScoringResult(
            proposal_id=proposal.id,
            engine_name=engine.name,
            model_name=engine.model,
            fit_score=skor.fit_score,
            data_quality_score=skor.data_quality_score,
            impact_score=skor.impact_score,
            total_score=total_score(skor),
            red_flags=[f.model_dump() for f in skor.red_flags],
            brief=skor.brief.model_dump(),
            threshold_used=campaign.score_threshold,
            verdict=ScoringVerdict(verdict.value),
            latency_ms=int((clock.now() - mulai).total_seconds() * 1000),
        )
    )

    event = (
        ProposalEvent.SCORING_LULUS
        if verdict is Verdict.LISTED
        else ProposalEvent.SCORING_GAGAL
    )
    advance_proposal(proposal, event)
    advance_scoring(proposal, ScoringEvent.SELESAI)  # T-51
    await session.flush()


async def run_scoring_job(
    session_factory: SessionFactory,
    proposal_id: UUID,
    engine: ScoringEngine,
    clock: Clock,
) -> None:
    """Dipanggil JobRunner (app/jobs/inline.py): membuka session sendiri
    lewat session_factory, bukan session request yang sudah selesai saat
    BackgroundTasks benar-benar berjalan."""
    async with session_factory() as session:
        await run_scoring(session, proposal_id, engine, clock)


@asynccontextmanager
async def production_job_session() -> AsyncIterator[AsyncSession]:
    """Implementasi SessionFactory sungguhan untuk app/api/deps.py: session
    baru per job, dikomit kalau tidak ada exception. Diletakkan di sini,
    bukan di deps.py, karena pagar AST menolak router/deps menyentuh
    session.<metode> secara langsung (test_pagar_layering.py)."""
    async with SessionLocal() as session:
        yield session
        await session.commit()


async def get_proposal_for_rescore(
    session: AsyncSession, proposal_id: UUID
) -> Proposal:
    proposal = await session.get(Proposal, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return proposal


async def request_rescore(session: AsyncSession, proposal: Proposal) -> None:
    if proposal.scoring_status is not ScoringStatus.FAILED:
        raise ConflictError(
            "scoring_belum_gagal",
            "Rescore hanya bisa dilakukan saat penilaian sebelumnya gagal.",
        )
    try:
        advance_scoring(proposal, ScoringEvent.NILAI_ULANG)  # T-53
    except IllegalTransition:
        # Tidak seharusnya tercapai: proposal.scoring_status sudah dipastikan
        # FAILED di atas, dan FAILED->NILAI_ULANG selalu ada di SCORING_MAP.
        raise ConflictError(
            "scoring_belum_gagal",
            "Rescore hanya bisa dilakukan saat penilaian sebelumnya gagal.",
        ) from None
    await session.flush()


async def get_latest_scoring(session: AsyncSession, proposal_id: UUID) -> ScoringResult:
    proposal = await session.get(Proposal, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    # Nama kolom sebagai string, bukan ScoringResult.created_at.desc(): atribut
    # kelas SQLModel diketik sebagai datetime biasa oleh mypy (tidak ada
    # plugin sqlmodel), sehingga .desc() di atasnya dianggap tidak ada (sama
    # seperti catatan di services/campaign.py).
    hasil = (
        await session.scalars(
            select(ScoringResult)
            .where(ScoringResult.proposal_id == proposal_id)
            .order_by(desc("created_at"))
            .limit(1)
        )
    ).first()
    if hasil is None:
        raise NotFoundError("scoring_belum_ada", "Proposal ini belum pernah dinilai.")
    return hasil

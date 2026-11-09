"""Dependency FastAPI yang dipakai setiap router: siapa pengguna, dan apa perannya."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.engine import ScoringEngine, build_engine
from app.config import settings
from app.db.session import get_session
from app.domain.clock import Clock
from app.errors import DomainError, ForbiddenError, NotFoundError
from app.models.campaign import Campaign
from app.models.comment import Comment
from app.models.pledge import Pledge
from app.models.proposal import Proposal, ProposalMilestone
from app.models.user import Role, User
from app.services.auth import ambil_user, decode_token
from app.services.campaign import ambil_campaign
from app.services.clock_service import ambil_clock
from app.services.community import ambil_komentar_aktif
from app.services.milestone import get_milestone
from app.services.pledge import get_pledge
from app.services.proposal import ambil_proposal
from app.services.scoring import (
    SessionFactory,
    ambil_proposal_untuk_rescore,
    sesi_job_produksi,
)

# Instance tunggal dibangun sekali saat modul ini diimpor, bukan satu engine
# baru per request: GeminiEngine.from_settings membangun genai.Client sendiri,
# dan membangunnya ulang di setiap request membuang kerja tanpa manfaat.
# Efek sampingnya disengaja: SCORING_ENGINE=gemini tanpa GEMINI_API_KEY
# membuat proses gagal start, bukan gagal samar di request pertama.
_scoring_engine = build_engine(settings)


def get_scoring_engine() -> ScoringEngine:
    return _scoring_engine


def get_session_factory() -> SessionFactory:
    # Dependency, bukan import langsung: test fase ini mengganti ini lewat
    # dependency_overrides agar job latar belakang memakai session transaksi
    # yang sama dengan test, bukan koneksi baru yang tidak melihat baris yang
    # baru di-flush dan belum dikomit. Implementasinya sendiri ada di
    # services/scoring.py, bukan di sini: pagar AST menolak berkas di app/api
    # menyentuh session.<metode> secara langsung.
    return sesi_job_produksi


class TidakTerautentikasi(DomainError):
    status = 401


async def get_clock(session: AsyncSession = Depends(get_session)) -> Clock:
    # Dependency, bukan import langsung: test fase 09 mengganti ini lewat
    # dependency_overrides tanpa menyentuh satu pun pemanggilnya. Dibaca dari
    # jam virtual tersimpan (D-06) supaya endpoint tick sungguhan punya efek
    # nyata ke seluruh pembacaan lain, bukan sekadar menulis baris yang tidak
    # pernah dibaca balik.
    return await ambil_clock(session)


async def current_user(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise TidakTerautentikasi("tidak_terautentikasi", "Token tidak ada.")
    # Tidak ada penerjemahan di sini: decode_token sudah melempar TokenKedaluwarsa
    # atau TokenTidakSah, keduanya DomainError berstatus 401.
    claims = decode_token(authorization.removeprefix("Bearer "))

    user = await ambil_user(session, claims.sub)
    if user is None:
        raise TidakTerautentikasi("token_tidak_sah", "Akun tidak ditemukan.")
    return user


async def pengguna_opsional(
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> User | None:
    """Seperti current_user, tapi None untuk request tanpa token.

    Dipakai endpoint publik yang perlu tahu siapa pemanggilnya hanya untuk
    memperluas apa yang terlihat (pembuat campaign melihat proposal rejected),
    bukan untuk menolak request.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        claims = decode_token(authorization.removeprefix("Bearer "))
    except DomainError:
        return None
    return await ambil_user(session, claims.sub)


def require_role(*roles: Role) -> Callable[[User], User]:
    def guard(user: User = Depends(current_user)) -> User:
        # Peran dibaca dari baris database, bukan dari klaim token (BR-04).
        if user.role not in roles:
            raise ForbiddenError(
                "peran_tidak_berhak", "Peran Anda tidak berhak atas aksi ini."
            )
        return user

    return guard


async def ambil_campaign_milik_sendiri(
    campaign_id: UUID,
    user: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
) -> Campaign:
    # Peran dan kepemilikan adalah dua pemeriksaan berbeda: require_role di atas
    # hanya membuktikan jenis penggunanya, bukan bahwa campaign ini miliknya.
    campaign = await ambil_campaign(session, campaign_id)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    if campaign.investor_id != user.id:
        raise ForbiddenError("bukan_pemilik", "Campaign ini bukan milik Anda.")
    return campaign


async def get_own_pledge(
    pledge_id: UUID,
    user: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
) -> Pledge:
    """BR-28 (lewat require_role) dan kepemilikan pledge (BR-25/BR-26) adalah
    dua pemeriksaan berbeda, sama seperti ambil_campaign_milik_sendiri di atas.
    404 untuk pledge yang tidak ada, 403 untuk pledge yang ada tapi bukan
    milik investor ini: pledge investor lain tetap "diketahui ada" lewat
    GET /proposals/{id}/pledges yang terbuka untuk investor manapun, jadi
    403 di sini tidak menambah kebocoran baru.
    """
    pledge = await get_pledge(session, pledge_id)
    if pledge is None:
        raise NotFoundError("pledge_tidak_ada", "Pledge tidak ditemukan.")
    if pledge.investor_id != user.id:
        raise ForbiddenError("bukan_pemilik_pledge", "Pledge ini bukan milik Anda.")
    return pledge


async def ambil_proposal_untuk_rescore_milik_sendiri(
    proposal_id: UUID,
    user: User = Depends(require_role(Role.UMKM, Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
) -> Proposal:
    """H-2: 10-api-contract.md membatasi POST rescore ke pemilik proposal
    (UMKM) atau pemilik campaign (investor), bukan peran manapun. 404, bukan
    403: investor atau UMKM lain yang lolos require_role di atas tidak boleh
    sekalian mengonfirmasi bahwa proposal ini ada.
    """
    proposal = await ambil_proposal_untuk_rescore(session, proposal_id)
    campaign = await ambil_campaign(session, proposal.campaign_id)
    if campaign is None or user.id not in {proposal.umkm_id, campaign.investor_id}:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return proposal


async def ambil_proposal_untuk_daftar_pledge(
    proposal_id: UUID,
    user: User = Depends(require_role(Role.UMKM, Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
) -> Proposal:
    """GET /proposals/{id}/pledges (10-api-contract.md:67). Pola yang sama
    dengan jaga_akses_scoring_milik_sendiri di bawah: investor manapun boleh
    melihat (kontrak menyebut peran itu blanket, bukan hanya pemilik
    campaign), tapi UMKM hanya pemilik proposal ini sendiri. UMKM lain yang
    lolos require_role di atas tetap ditolak 404, bukan 403, supaya
    keberadaan proposal tidak terbuka untuk UMKM yang bukan pemiliknya.
    """
    proposal = await ambil_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    if user.role is Role.UMKM and proposal.umkm_id != user.id:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return proposal


async def get_own_comment(
    comment_id: UUID,
    user: User = Depends(require_role(Role.COMMUNITY)),
    session: AsyncSession = Depends(get_session),
) -> Comment:
    """Kepemilikan komentar (BR-34), terpisah dari peran benar di atas, sama
    seperti get_own_pledge. 404 untuk komentar yang tidak ada atau sudah
    terhapus, 403 untuk komentar yang ada tapi bukan milik pengguna ini --
    keberadaannya sudah publik lewat GET /proposals/{id}/comments, jadi 403
    di sini tidak menambah kebocoran baru.
    """
    komentar = await ambil_komentar_aktif(session, comment_id)
    if komentar is None:
        raise NotFoundError("komentar_tidak_ada", "Komentar tidak ditemukan.")
    if komentar.user_id != user.id:
        raise ForbiddenError("bukan_penulis", "Komentar ini bukan milik Anda.")
    return komentar


async def jaga_akses_scoring_milik_sendiri(
    proposal_id: UUID,
    user: User = Depends(require_role(Role.UMKM, Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """H-2: GET scoring mengizinkan investor manapun (10-api-contract.md
    menyebut "investor" secara blanket, beda dari rescore yang membatasi ke
    pemilik campaign), tapi UMKM hanya boleh melihat scoring proposal
    miliknya sendiri. UMKM lain yang lolos require_role di atas harus tetap
    ditolak 404 di sini.
    """
    if user.role is Role.UMKM:
        proposal = await ambil_proposal(session, proposal_id)
        if proposal is None or proposal.umkm_id != user.id:
            raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")


async def get_own_milestone_for_report(
    milestone_id: UUID,
    umkm: User = Depends(require_role(Role.UMKM)),
    session: AsyncSession = Depends(get_session),
) -> ProposalMilestone:
    """Kepemilikan laporan: hanya UMKM pemilik proposal induk milestone ini
    yang boleh melaporkan progresnya (04-feature-umkm.md). 404 untuk UMKM
    lain, bukan 403, supaya keberadaan milestone proposal orang lain tidak
    ikut terkonfirmasi, sama seperti ambil_proposal_untuk_rescore_milik_sendiri
    di atas.
    """
    milestone = await get_milestone(session, milestone_id)
    if milestone is None:
        raise NotFoundError("milestone_tidak_ada", "Milestone tidak ditemukan.")
    proposal = await ambil_proposal(session, milestone.proposal_id)
    if proposal is None or proposal.umkm_id != umkm.id:
        raise NotFoundError("milestone_tidak_ada", "Milestone tidak ditemukan.")
    return milestone


async def get_milestone_for_review(
    milestone_id: UUID,
    investor: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
) -> ProposalMilestone:
    """Dependency ini hanya menjaga perannya investor dan memastikan
    milestone-nya ada. BR-44 (hanya lead investor yang boleh approve/reject)
    sengaja tidak diperiksa di sini: pemeriksaan identitas lead investor
    butuh baris proposal yang terkunci (RF-5, approve mencairkan uang), dan
    dependency FastAPI bukan tempat yang tepat untuk mengunci baris sebelum
    router memutuskan apakah akan melakukan apa pun dengannya. Pemeriksaan
    itu hidup di approve_milestone dan reject_milestone (services/milestone.py),
    lewat get_locked_proposal yang sama dengan RF-1.
    """
    milestone = await get_milestone(session, milestone_id)
    if milestone is None:
        raise NotFoundError("milestone_tidak_ada", "Milestone tidak ditemukan.")
    return milestone

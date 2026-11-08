"""Dependency FastAPI yang dipakai setiap router: siapa pengguna, dan apa perannya."""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.domain.clock import Clock, SystemClock
from app.errors import DomainError, ForbiddenError, NotFoundError
from app.models.campaign import Campaign
from app.models.user import Role, User
from app.services.auth import ambil_user, decode_token
from app.services.campaign import ambil_campaign


class TidakTerautentikasi(DomainError):
    status = 401


def get_clock() -> Clock:
    # Dependency, bukan import langsung: test fase 09 mengganti ini lewat
    # dependency_overrides tanpa menyentuh satu pun pemanggilnya.
    return SystemClock()


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

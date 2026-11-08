"""Dependency FastAPI yang dipakai setiap router: siapa pengguna, dan apa perannya."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.domain.clock import Clock, SystemClock
from app.errors import DomainError, ForbiddenError
from app.models.user import Role, User
from app.services.auth import decode_token


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

    user = await session.get(User, claims.sub)
    if user is None:
        raise TidakTerautentikasi("token_tidak_sah", "Akun tidak ditemukan.")
    return user


def require_role(*roles: Role) -> Callable[[User], User]:
    def guard(user: User = Depends(current_user)) -> User:
        # Peran dibaca dari baris database, bukan dari klaim token (BR-04).
        if user.role not in roles:
            raise ForbiddenError(
                "peran_tidak_berhak", "Peran Anda tidak berhak atas aksi ini."
            )
        return user

    return guard

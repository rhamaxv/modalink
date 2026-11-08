"""Dependency FastAPI yang dipakai setiap router: siapa pengguna, dan apa perannya."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.errors import DomainError
from app.models.user import User
from app.services.auth import decode_token


class TidakTerautentikasi(DomainError):
    status = 401


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

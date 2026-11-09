"""Hash password, terbitkan/verifikasi JWT, dan orkestrasi register/login (BR-02..BR-04)."""

import secrets
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.domain.clock import SystemClock
from app.errors import DomainError
from app.models.user import User
from app.schemas.auth import LoginIn, RegisterIn

_hasher = PasswordHasher()
_clock = SystemClock()


class TokenExpired(DomainError):
    status = 401


class TokenInvalid(DomainError):
    status = 401


class InvalidCredentials(DomainError):
    status = 401


class EmailAlreadyUsed(DomainError):
    """Email sudah dipakai akun lain."""

    status = 400


@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub: UUID
    role: str


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


# Hash umpan: dihitung sekali saat modul diimpor dari string acak, bukan
# ditulis sebagai literal (itu akan jadi kredensial di berkas yang di-track).
# Dipakai di authenticate_user supaya argon2 tetap jalan untuk email yang
# tidak dikenal, menutup oracle waktu respons.
HASH_UMPAN = hash_password(secrets.token_hex(32))


def verify_password(raw: str, hashed: str) -> bool:
    # Hash korup atau dari algoritme lain melempar VerificationError atau
    # InvalidHashError, bukan VerifyMismatchError; keduanya berarti "tidak
    # cocok", bukan kegagalan server (500).
    try:
        return _hasher.verify(hashed, raw)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def issue_token(user_id: UUID, role: str, ttl_hours: int | None = None) -> str:
    ttl = settings.jwt_ttl_hours if ttl_hours is None else ttl_hours
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": _clock.now() + timedelta(hours=ttl),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> TokenClaims:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise TokenExpired("token_kedaluwarsa", "Token sudah kedaluwarsa.") from None
    except jwt.InvalidTokenError:
        raise TokenInvalid("token_tidak_sah", "Token tidak sah.") from None
    return TokenClaims(sub=UUID(payload["sub"]), role=payload["role"])


async def register_user(session: AsyncSession, body: RegisterIn) -> User:
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        role=body.role,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        # Constraint database yang menangkapnya, bukan pemeriksaan di Python:
        # pemeriksaan lebih dulu punya celah balapan, constraint tidak. Dicek
        # dulu constraint mana yang melanggar: email satu-satunya kolom unik
        # hari ini, tapi begitu users punya constraint kedua, pelanggaran yang
        # tidak berhubungan akan salah dilaporkan sebagai email terpakai.
        if (
            "users_email" not in str(exc.orig).lower()
            and "ix_users_email" not in str(exc.orig).lower()
        ):
            raise
        raise EmailAlreadyUsed("email_terpakai", "Email ini sudah terdaftar.") from None
    return user


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def authenticate_user(session: AsyncSession, body: LoginIn) -> User:
    user = await session.scalar(select(User).where(User.email == body.email.lower()))

    # Hash umpan dipakai saat email tidak dikenal supaya argon2 tetap berjalan dan
    # lama responsnya tidak membedakan "email tidak ada" dari "password salah".
    cocok = verify_password(body.password, user.password_hash if user else HASH_UMPAN)
    if user is None or not cocok:
        raise InvalidCredentials("kredensial_salah", "Email atau password salah.")
    return user

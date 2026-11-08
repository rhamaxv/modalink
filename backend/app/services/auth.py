"""Hash password dan terbitkan/verifikasi JWT (BR-03, BR-04)."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import settings
from app.domain.clock import SystemClock
from app.errors import DomainError

_hasher = PasswordHasher()
_clock = SystemClock()


class TokenKedaluwarsa(DomainError):
    status = 401


class TokenTidakSah(DomainError):
    status = 401


@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub: UUID
    role: str


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


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
        raise TokenKedaluwarsa(
            "token_kedaluwarsa", "Token sudah kedaluwarsa."
        ) from None
    except jwt.InvalidTokenError:
        raise TokenTidakSah("token_tidak_sah", "Token tidak sah.") from None
    return TokenClaims(sub=UUID(payload["sub"]), role=payload["role"])

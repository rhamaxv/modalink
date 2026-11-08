"""Hash password dan terbitkan/verifikasi JWT (BR-03, BR-04)."""
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import settings
from app.domain.clock import SystemClock

_hasher = PasswordHasher()
_clock = SystemClock()


@dataclass(frozen=True, slots=True)
class TokenClaims:
    sub: UUID
    role: str


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw)
    except VerifyMismatchError:
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
        raise ValueError("Token kedaluwarsa.") from None
    except jwt.InvalidTokenError:
        raise ValueError("Token tidak sah.") from None
    return TokenClaims(sub=UUID(payload["sub"]), role=payload["role"])

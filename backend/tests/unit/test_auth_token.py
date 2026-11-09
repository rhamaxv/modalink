"""BR-03: hash argon2, BR-04: JWT membawa role dan ditolak jika kedaluwarsa atau palsu."""

from uuid import uuid4

import pytest

from app.services.auth import (
    TokenExpired,
    TokenInvalid,
    decode_token,
    hash_password,
    issue_token,
    verify_password,
)


def test_br03_hash_never_equals_original_password():
    h = hash_password("rahasia123")
    assert h != "rahasia123"
    assert h.startswith("$argon2")


def test_verify_password_correct_and_incorrect():
    h = hash_password("rahasia123")
    assert verify_password("rahasia123", h) is True
    assert verify_password("rahasia124", h) is False


def test_verify_password_corrupted_hash_treated_as_mismatch():
    assert verify_password("rahasia123", "bukan-hash-argon2-yang-sah") is False


def test_token_carries_sub_and_role():
    uid = uuid4()
    claims = decode_token(issue_token(uid, "investor"))
    assert claims.sub == uid
    assert claims.role == "investor"


def test_expired_token_rejected():
    uid = uuid4()
    kedaluwarsa = issue_token(uid, "investor", ttl_hours=-1)
    with pytest.raises(TokenExpired):
        decode_token(kedaluwarsa)


def test_token_with_different_signature_rejected():
    import jwt

    palsu = jwt.encode(
        {"sub": str(uuid4()), "role": "investor"},
        "kunci-lain-yang-sama-sekali-berbeda-32-byte",
        algorithm="HS256",
    )
    with pytest.raises(TokenInvalid):
        decode_token(palsu)

"""BR-03: hash argon2, BR-04: JWT membawa role dan ditolak jika kedaluwarsa atau palsu."""

from uuid import uuid4

import pytest

from app.services.auth import decode_token, hash_password, issue_token, verify_password


def test_br03_hash_tidak_pernah_sama_dengan_password_asli():
    h = hash_password("rahasia123")
    assert h != "rahasia123"
    assert h.startswith("$argon2")


def test_verify_password_benar_dan_salah():
    h = hash_password("rahasia123")
    assert verify_password("rahasia123", h) is True
    assert verify_password("rahasia124", h) is False


def test_token_membawa_sub_dan_role():
    uid = uuid4()
    claims = decode_token(issue_token(uid, "investor"))
    assert claims.sub == uid
    assert claims.role == "investor"


def test_token_kedaluwarsa_ditolak():
    uid = uuid4()
    kedaluwarsa = issue_token(uid, "investor", ttl_hours=-1)
    with pytest.raises(ValueError, match="kedaluwarsa"):
        decode_token(kedaluwarsa)


def test_token_dengan_tanda_tangan_lain_ditolak():
    import jwt

    palsu = jwt.encode(
        {"sub": str(uuid4()), "role": "investor"},
        "kunci-lain-yang-sama-sekali-berbeda-32-byte",
        algorithm="HS256",
    )
    with pytest.raises(ValueError):
        decode_token(palsu)

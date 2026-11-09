"""Skema request/response untuk register, login, dan profil pengguna saat ini."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

import email_validator
from pydantic import AfterValidator, BaseModel, Field

from app.models.user import Role


def _validasi_email(value: str) -> str:
    """Pengganti `EmailStr` bawaan Pydantic, bukan dipakai langsung: EmailStr
    menolak domain reserved RFC 2606 (`.test`, `.example`, dst) tanpa opsi
    untuk melonggarkannya per-field, dan `app/seed/demo.py` sengaja memakai
    `demo.modalink.test` untuk akun demo juri (konvensi domain yang tidak
    pernah dikirim email sungguhan). `test_environment=True` membuka
    pengecualian itu secara eksplisit sambil tetap menolak "not-an-email"
    (review keamanan) -- bukan mematikan validasi, hanya mengakui bahwa TLD
    reserved itu valid secara sintaks untuk proyek yang tidak pernah benar-
    benar mengirim email. `check_deliverability=False` tetap seperti
    default EmailStr: tidak ada resolusi DNS saat request masuk.
    """
    try:
        hasil = email_validator.validate_email(
            value, check_deliverability=False, test_environment=True
        )
    except email_validator.EmailNotValidError as exc:
        raise ValueError(f"Alamat email tidak valid: {exc}") from exc
    return hasil.normalized


# max_length=254 (RFC 5321) diperiksa Field lebih dulu, sebelum
# AfterValidator: payload raksasa ditolak cepat lewat panjang, bukan lewat
# parsing email_validator yang harus memeriksa seluruhnya dulu.
Email = Annotated[str, Field(max_length=254), AfterValidator(_validasi_email)]


class RegisterIn(BaseModel):
    # Email kustom, bukan str polos: tanpa ini "not-an-email" lolos sebagai
    # email yang sah (review keamanan).
    email: Email
    # BR-03: minimal 8 karakter. max_length=128 menolak payload beberapa MB
    # (review keamanan: 5 MB lolos tanpa batas atas) sambil tetap jauh di
    # atas password manusia terpanjang yang wajar.
    password: Annotated[str, Field(min_length=8, max_length=128)]
    # max_length=120, sama dengan business_name di schemas/proposal.py: nama
    # orang tidak pernah butuh lebih dari itu, dan tanpa batas atas payload
    # beberapa MB lolos sebagai nama (review keamanan).
    name: Annotated[str, Field(min_length=1, max_length=120)]
    role: Role


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    # Tidak memuat password_hash: inilah yang membuat endpoint mana pun yang
    # memakai skema ini otomatis memenuhi BR-03.
    model_config = {"from_attributes": True}

    id: UUID
    email: str
    name: str
    role: Role
    created_at: datetime

"""Skema request/response untuk register, login, dan profil pengguna saat ini."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.user import Role


class RegisterIn(BaseModel):
    email: str
    # BR-03: minimal 8 karakter.
    password: str = Field(min_length=8)
    name: str
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

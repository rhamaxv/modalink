"""Model pengguna: satu tabel untuk seluruh peran (BR-02)."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock


class Role(StrEnum):
    INVESTOR = "investor"
    UMKM = "umkm"
    COMMUNITY = "community"


class User(SQLModel, table=True):
    __tablename__ = "users"
    __table_args__ = (
        # Lapisan kedua di belakang Field(max_length=120) di RegisterIn
        # (Task 3 review keamanan, migrasi a061fd4c5ee6). `password` sengaja
        # tidak punya pasangan CHECK: hanya hash-nya yang pernah tersimpan di
        # kolom apa pun, jadi panjang password mentah tidak pernah mencapai
        # baris database untuk dipagari lagi -- batas Pydantic di sana
        # satu-satunya pagar yang mungkin, bukan kelonggaran yang terlewat.
        CheckConstraint("length(name) BETWEEN 1 AND 120", name="ck_users_name_length"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    # values_callable memaksa Postgres menyimpan nilai StrEnum ("investor")
    # bukan nama anggotanya ("INVESTOR"); tanpa ini SQLAlchemy memakai .name
    # secara default dan bertentangan dengan 09-data-model.md serta role di JWT.
    role: Role = Field(
        sa_column=Column(
            SAEnum(
                Role,
                name="role",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        )
    )
    created_at: datetime = Field(default_factory=lambda: SystemClock().now())

    def model_post_init(self, context: object, /) -> None:
        # @field_validator tidak jalan di sini: untuk model table=True, SQLModel
        # membuat instance lewat __init__ gaya SQLAlchemy yang melewati jalur
        # validasi pydantic biasa. model_post_init tetap dipanggil, jadi
        # normalisasi email (BR-02) ditaruh di sini.
        self.email = self.email.strip().lower()

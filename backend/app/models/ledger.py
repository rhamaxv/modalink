"""Model `ledger_entries`: append-only, saldo tidak pernah disimpan (BR-50 sampai BR-55).

Tidak ada endpoint, service, atau migrasi yang boleh meng-UPDATE atau
menghapus baris di tabel ini. Koreksi berarti entri baru ke arah berlawanan,
tidak pernah mengubah entri yang sudah ada.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, CheckConstraint, Column, Index
from sqlalchemy import Enum as SAEnum
from sqlmodel import Field, SQLModel


class EntryType(StrEnum):
    PLEDGE_IN = "pledge_in"
    REFUND_OUT = "refund_out"
    DISBURSEMENT_OUT = "disbursement_out"


class LedgerEntry(SQLModel, table=True):
    """Append-only. Tidak ada endpoint, service, atau migrasi yang boleh
    meng-UPDATE atau menghapus baris di tabel ini (BR-51)."""

    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ledger_amount_positif"),
        # Mirror dari index komposit yang ditambahkan lewat migrasi tersendiri
        # (09-data-model.md:156); lihat komentar yang sama di models/pledge.py
        # soal kenapa __table_args__ ini bukan formalitas. total_terkumpul_proposal
        # dan R2 selalu menyaring proposal_id lalu mengurutkan created_at.
        Index("ix_ledger_entries_proposal_id_created_at", "proposal_id", "created_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    proposal_id: UUID = Field(foreign_key="proposals.id", index=True)
    entry_type: EntryType = Field(
        sa_column=Column(
            SAEnum(
                EntryType,
                name="ledger_entry_type",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        )
    )
    # sa_column=Column(BigInteger) wajib: SQLModel memetakan int ke INTEGER
    # secara default, dan INTEGER meluap di Rp2,1 miliar (BR-50). Arah dana
    # ada di entry_type, bukan di tanda amount (BR-54): tabel ini hanya
    # menerima nominal positif.
    amount: int = Field(sa_column=Column(BigInteger, nullable=False))
    # Default "" / None, bukan wajib diisi: dipakai menjejak sumber entri
    # (misal ref_type="pledge", ref_id=pledge.id) tapi belum setiap pemanggil
    # catat_entri punya itu di task ini.
    ref_type: str = Field(default="")
    ref_id: UUID | None = Field(default=None, nullable=True)
    actor_id: UUID | None = Field(default=None, foreign_key="users.id", nullable=True)
    # Unique: inilah yang membuat approve atau klik ganda menghasilkan satu
    # entri, bukan harapan bahwa tidak ada yang mengklik dua kali (BR-55).
    idempotency_key: str = Field(unique=True, index=True)
    created_at: datetime

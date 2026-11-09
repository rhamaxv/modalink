"""Skema respons GET /internal/ledger/{proposal_id} (BR-50 sampai BR-55, D-03).

Setiap baris di ledger_entries diperlihatkan utuh, bukan hanya ringkasan:
endpoint ini ada supaya juri bisa memverifikasi uang benar-benar dicatat,
bukan dipercaya begitu saja dari satu angka akhir.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.ledger import EntryType


class LedgerEntryOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    proposal_id: UUID
    entry_type: EntryType
    amount: int
    ref_type: str
    ref_id: UUID | None
    actor_id: UUID | None
    idempotency_key: str
    created_at: datetime


class LedgerOut(BaseModel):
    # balance dihitung di services/ledger.py lewat hitung_saldo atas entries
    # yang sama ini, tidak pernah dibaca dari kolom manapun (BR-52): kolom
    # saldo tidak ada dan tidak boleh ada.
    entries: list[LedgerEntryOut]
    balance: int

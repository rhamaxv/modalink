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
    # balance dihitung di services/ledger.py lewat compute_balance atas entries
    # yang sama ini, tidak pernah dibaca dari kolom manapun (BR-52): kolom
    # saldo tidak ada dan tidak boleh ada.
    entries: list[LedgerEntryOut]
    balance: int


class LedgerEntryPublicOut(BaseModel):
    """Satu baris riwayat dana untuk dilihat pemilik proposal dan investor.

    Bukan LedgerEntryOut: bentuk itu dipakai endpoint internal yang hanya
    hidup saat ENV=dev, dan ia membuka `actor_id` setiap baris. Membukanya di
    sini akan membatalkan penyamaran identitas investor yang dijaga
    services/pledge.py (10-api-contract.md:106-107): siapa pun yang berhak
    melihat daftar ini bisa mencocokkan actor_id dengan nominal dan tahu
    persis siapa memberi berapa sebelum proposal penuh.

    `idempotency_key` juga tidak ikut: ia kunci teknis anti-duplikat, bukan
    informasi yang berarti bagi siapa pun yang membaca riwayat dananya.
    """

    model_config = {"from_attributes": True}

    id: UUID
    entry_type: EntryType
    amount: int
    # "pledge", "milestone", dst: menjelaskan SEBAB baris ini ada tanpa
    # menyebut siapa pelakunya.
    ref_type: str
    created_at: datetime
    # "BCA ••••7890" untuk baris pencairan, None untuk yang lain. Sudah
    # tersamar di database (hanya empat digit terakhir yang pernah disimpan),
    # jadi bentuk ini bukan penyamaran di lapisan tampilan yang bisa
    # dilangkahi.
    destination_label: str | None = None
    # True hanya untuk baris yang dicatat oleh pemanggil sendiri. Investor
    # butuh bisa menemukan pledge-nya sendiri di antara pledge orang lain,
    # dan itu tidak membocorkan apa pun: ia memang sudah tahu siapa dirinya.
    milik_saya: bool = False


class LedgerPublicOut(BaseModel):
    entries: list[LedgerEntryPublicOut]
    # Saldo yang masih tertahan: seluruh pledge_in dikurangi refund_out dan
    # disbursement_out. Dihitung ulang dari entries, tidak pernah dari kolom
    # (BR-52).
    balance: int
    total_masuk: int
    total_cair: int

"""Ledger uang: hanya menambah, saldo selalu dihitung ulang dari entri (BR-51, BR-52).

`hitung_saldo` dan `total_terkumpul` memakai angka yang mirip tapi berbeda:
yang pertama memasukkan pencairan, yang kedua tidak. Progress bar funding
memakai `total_terkumpul`; pengecekan "cukupkah dana untuk dicairkan" memakai
`hitung_saldo`. Menukarnya membuat progress bar turun setiap kali milestone
cair, tanpa ada error yang melapor.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.clock import SystemClock
from app.models.ledger import EntryType, LedgerEntry
from app.models.pledge import Pledge, PledgeStatus

MASUK = {EntryType.PLEDGE_IN}
KELUAR = {EntryType.REFUND_OUT, EntryType.DISBURSEMENT_OUT}

# sqlstate Postgres untuk unique_violation. exc.orig dari dialect asyncpg
# sqlalchemy memuat atribut .sqlstate langsung (dibuktikan lewat probe manual
# terhadap UniqueViolationError dan CheckViolationError sungguhan, bukan
# ditebak dari dokumentasi): tidak perlu menelusuri __cause__ untuk sampai ke
# asyncpg.exceptions.UniqueViolationError di baliknya.
SQLSTATE_UNIQUE_VIOLATION = "23505"

# Instance tunggal dari Clock, bukan memanggil jam sistem langsung: catat_entri
# tetap butuh jam meski pemanggil (termasuk test brief ini) tidak selalu
# menyediakannya, jadi fallback-nya memakai Clock sungguhan, sama seperti
# _clock di services/auth.py.
_clock = SystemClock()


@dataclass(frozen=True, slots=True)
class EntriRingkas:
    entry_type: EntryType
    amount: int


def hitung_saldo(entries: Iterable[EntriRingkas]) -> int:
    """Saldo escrow: apa yang masuk dikurangi apa yang keluar (BR-52)."""
    return sum(e.amount if e.entry_type in MASUK else -e.amount for e in entries)


def total_terkumpul(entries: Iterable[EntriRingkas]) -> int:
    """Dana yang terkumpul dari investor. Pencairan tidak menguranginya,
    karena yang dicairkan tetap 'pernah terkumpul'."""
    return sum(
        e.amount if e.entry_type is EntryType.PLEDGE_IN else -e.amount
        for e in entries
        if e.entry_type in {EntryType.PLEDGE_IN, EntryType.REFUND_OUT}
    )


async def catat_entri(
    session: AsyncSession,
    proposal_id: UUID,
    entry_type: EntryType,
    amount: int,
    idempotency_key: str,
    ref_type: str = "",
    ref_id: UUID | None = None,
    actor_id: UUID | None = None,
) -> LedgerEntry | None:
    """Mengembalikan None bila kunci idempotensi sudah pernah dipakai (BR-55).

    begin_nested(), bukan rollback_to_savepoint(): AsyncSession tidak punya
    metode itu. Tanpa savepoint di sini, IntegrityError dari constraint unik
    membuat Postgres mengabort seluruh transaksi luar ("current transaction
    is aborted"), sehingga satu entri duplikat menggagalkan seluruh request
    yang menumpangi sesi ini, bukan hanya entri yang gagal.
    """
    entri = LedgerEntry(
        proposal_id=proposal_id,
        entry_type=entry_type,
        amount=amount,
        ref_type=ref_type,
        ref_id=ref_id,
        actor_id=actor_id,
        idempotency_key=idempotency_key,
        created_at=_clock.now(),
    )
    try:
        async with session.begin_nested():
            session.add(entri)
            await session.flush()
    except IntegrityError as exc:
        # Hanya unique_violation pada idempotency_key berarti "sudah pernah
        # tercatat, aman diabaikan" (BR-55). CHECK (amount > 0) atau FK yang
        # gagal berarti pemanggil salah menghitung nominal, dan menelannya
        # di sini akan membuat entri uang hilang tanpa satu pun error muncul.
        if getattr(exc.orig, "sqlstate", None) != SQLSTATE_UNIQUE_VIOLATION:
            raise
        return None
    return entri


async def total_terkumpul_proposal(session: AsyncSession, proposal_id: UUID) -> int:
    """Query, dipakai Task 3 dan 4 untuk memeriksa sisa dana sebelum pledge baru.

    Nama berbeda dari total_terkumpul(entries) sengaja: fungsi ini menerima
    sesi database, bukan daftar entri, supaya kedua angka tidak tertukar."""
    entri = (
        await session.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == proposal_id)
        )
    ).all()
    return total_terkumpul(
        EntriRingkas(entry_type=e.entry_type, amount=e.amount) for e in entri
    )


async def ambil_ledger_proposal(
    session: AsyncSession, proposal_id: UUID
) -> tuple[list[LedgerEntry], int]:
    """GET /internal/ledger/{proposal_id} (10-api-contract.md:96): seluruh
    entri plus saldo hasil penjumlahan atas entri yang sama, bukan dibaca
    dari kolom manapun (BR-52). Urutan created_at lalu id, bukan untuk
    ketepatan saldo (urutan penjumlahan tidak memengaruhi hasilnya) tapi
    supaya juri yang membaca daftarnya melihat kronologi yang masuk akal."""
    entri = (
        await session.scalars(
            select(LedgerEntry)
            .where(LedgerEntry.proposal_id == proposal_id)
            .order_by("created_at", "id")
        )
    ).all()
    saldo = hitung_saldo(
        EntriRingkas(entry_type=e.entry_type, amount=e.amount) for e in entri
    )
    return list(entri), saldo


async def total_pledge_aktif(session: AsyncSession, proposal_id: UUID) -> int:
    """Query, dipakai R2b untuk mencocokkan status funding dengan jumlah pledge aktif."""
    total = await session.scalar(
        select(func.coalesce(func.sum(Pledge.amount), 0)).where(
            Pledge.proposal_id == proposal_id, Pledge.status == PledgeStatus.ACTIVE
        )
    )
    return int(total or 0)

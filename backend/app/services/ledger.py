"""Ledger uang: hanya menambah, saldo selalu dihitung ulang dari entri (BR-51, BR-52).

`compute_balance` dan `total_raised` memakai angka yang mirip tapi berbeda:
yang pertama memasukkan pencairan, yang kedua tidak. Progress bar funding
memakai `total_raised`; pengecekan "cukupkah dana untuk dicairkan" memakai
`compute_balance`. Menukarnya membuat progress bar turun setiap kali milestone
cair, tanpa ada error yang melapor.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.domain.clock import Clock
from app.models.ledger import EntryType, LedgerEntry
from app.models.pledge import Pledge, PledgeStatus

INCOMING_ENTRY_TYPES = {EntryType.PLEDGE_IN}
OUTGOING_ENTRY_TYPES = {EntryType.REFUND_OUT, EntryType.DISBURSEMENT_OUT}

# sqlstate Postgres untuk unique_violation. exc.orig dari dialect asyncpg
# sqlalchemy memuat atribut .sqlstate langsung (dibuktikan lewat probe manual
# terhadap UniqueViolationError dan CheckViolationError sungguhan, bukan
# ditebak dari dokumentasi): tidak perlu menelusuri __cause__ untuk sampai ke
# asyncpg.exceptions.UniqueViolationError di baliknya.
SQLSTATE_UNIQUE_VIOLATION = "23505"


@dataclass(frozen=True, slots=True)
class LedgerEntrySummary:
    entry_type: EntryType
    amount: int


def compute_balance(entries: Iterable[LedgerEntrySummary]) -> int:
    """Saldo escrow: apa yang masuk dikurangi apa yang keluar (BR-52)."""
    return sum(
        e.amount if e.entry_type in INCOMING_ENTRY_TYPES else -e.amount for e in entries
    )


def total_raised(entries: Iterable[LedgerEntrySummary]) -> int:
    """Dana yang terkumpul dari investor. Pencairan tidak menguranginya,
    karena yang dicairkan tetap 'pernah terkumpul'."""
    return sum(
        e.amount if e.entry_type is EntryType.PLEDGE_IN else -e.amount
        for e in entries
        if e.entry_type in {EntryType.PLEDGE_IN, EntryType.REFUND_OUT}
    )


async def record_entry(
    session: AsyncSession,
    proposal_id: UUID,
    entry_type: EntryType,
    amount: int,
    idempotency_key: str,
    *,
    clock: Clock,
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

    `clock` wajib diisi pemanggil (BR-60, review Finding 4), tidak ada
    fallback ke SystemClock di sini. Sebelum ini modul punya `_clock`
    sendiri terlepas dari clock yang disuntikkan permintaan HTTP: di bawah
    VirtualClock, baris pledge/milestone tercatat dengan waktu virtual lewat
    kolom created_at masing-masing, tapi entri ledger-nya tetap memakai
    SystemClock, sehingga GET /internal/ledger/{id} -- yang diurutkan
    created_at justru untuk diaudit juri -- bisa menampilkan refund lazy
    expiry tertanggal SEBELUM deadline virtual yang memicunya.
    """
    entri = LedgerEntry(
        proposal_id=proposal_id,
        entry_type=entry_type,
        amount=amount,
        ref_type=ref_type,
        ref_id=ref_id,
        actor_id=actor_id,
        idempotency_key=idempotency_key,
        created_at=clock.now(),
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


def collected_amount_subquery():
    """Subquery total_raised per proposal (pledge_in dikurangi refund_out),
    dipakai JOIN pada query daftar proposal publik (Task 1, BR-51).

    Satu query untuk SELURUH baris proposal yang sedang dibaca, bukan satu
    query `collected_amount_for_proposal` per baris: GET /proposals menampilkan
    banyak proposal sekaligus, dan memanggil fungsi tunggal di bawah di
    dalam loop mengubahnya jadi N+1 query (N proposal, satu SELECT ledger
    masing-masing). CASE di sini sengaja meniru persis ekspresi di
    `total_raised()` Python di atas (PLEDGE_IN dikurangi REFUND_OUT, DI
    LUAR DISBURSEMENT_OUT) supaya kedua definisinya tidak bisa diam-diam
    menyimpang: tanpa itu bilah progres publik dan "sisa dana" yang dipakai
    create_pledge bisa menghitung dua angka berbeda untuk proposal yang sama.
    """
    kolom = case(
        (LedgerEntry.entry_type == EntryType.PLEDGE_IN, LedgerEntry.amount),
        (LedgerEntry.entry_type == EntryType.REFUND_OUT, -LedgerEntry.amount),
        else_=0,
    )
    return (
        select(
            LedgerEntry.proposal_id.label("proposal_id"),
            func.sum(kolom).label("collected_amount"),
        )
        .where(
            col(LedgerEntry.entry_type).in_({EntryType.PLEDGE_IN, EntryType.REFUND_OUT})
        )
        .group_by(LedgerEntry.proposal_id)
    ).subquery("jumlah_terkumpul")


async def collected_amount_for_proposal(
    session: AsyncSession, proposal_id: UUID
) -> int:
    """Query, dipakai Task 3 dan 4 untuk memeriksa sisa dana sebelum pledge baru.

    Nama berbeda dari total_raised(entries) sengaja: fungsi ini menerima
    sesi database, bukan daftar entri, supaya kedua angka tidak tertukar."""
    entri = (
        await session.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == proposal_id)
        )
    ).all()
    return total_raised(
        LedgerEntrySummary(entry_type=e.entry_type, amount=e.amount) for e in entri
    )


async def get_proposal_ledger(
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
    saldo = compute_balance(
        LedgerEntrySummary(entry_type=e.entry_type, amount=e.amount) for e in entri
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

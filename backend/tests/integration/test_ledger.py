"""Entri ledger yang hanya bisa ditambah: constraint database dan idempotensi (BR-51, BR-54, BR-55)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.ledger import EntryType, LedgerEntry
from app.services.ledger import record_entry


async def test_br54_zero_entry_rejected_by_database(db, listed_proposal):
    db.add(
        LedgerEntry(
            proposal_id=listed_proposal.id,
            entry_type=EntryType.PLEDGE_IN,
            amount=0,
            idempotency_key="uji:1",
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_br54_negative_entry_rejected_by_database(db, listed_proposal):
    db.add(
        LedgerEntry(
            proposal_id=listed_proposal.id,
            entry_type=EntryType.PLEDGE_IN,
            amount=-1,
            idempotency_key="uji:2",
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_br55_idempotency_key_prevents_duplicate_entry(
    db, listed_proposal, clock
):
    kunci = f"pledge:{listed_proposal.id}"
    pertama = await record_entry(
        db, listed_proposal.id, EntryType.PLEDGE_IN, 5_000_000, kunci, clock=clock
    )
    kedua = await record_entry(
        db, listed_proposal.id, EntryType.PLEDGE_IN, 5_000_000, kunci, clock=clock
    )
    assert pertama is not None
    assert kedua is None  # panggilan kedua tidak menambah apa pun
    jumlah = await db.scalar(
        select(func.count())
        .select_from(LedgerEntry)
        .where(LedgerEntry.idempotency_key == kunci)
    )
    assert jumlah == 1


async def test_br54_record_entry_does_not_swallow_zero_amount_integrity_error(
    db, listed_proposal, clock
):
    """record_entry hanya boleh menelan pelanggaran unique idempotency_key
    (BR-55). Pelanggaran CHECK (amount > 0, BR-54) wajib tetap meledak,
    bukan diam-diam dikembalikan sebagai None yang di seluruh kode ini
    berarti 'aman, sudah pernah tercatat'."""
    with pytest.raises(IntegrityError):
        await record_entry(
            db,
            listed_proposal.id,
            EntryType.PLEDGE_IN,
            0,
            "uji:nol-ditelan",
            clock=clock,
        )


async def test_br55_next_entry_after_duplicate_still_persists(
    db, listed_proposal, clock
):
    """Savepoint (begin_nested) pada record_entry wajib membatasi kerusakan ke
    entri yang gagal saja: transaksi luar tidak boleh ikut ter-abort, atau
    entri sah berikutnya di request yang sama akan ikut hilang."""
    kunci_duplikat = f"pledge:{listed_proposal.id}"
    await record_entry(
        db,
        listed_proposal.id,
        EntryType.PLEDGE_IN,
        5_000_000,
        kunci_duplikat,
        clock=clock,
    )
    gagal = await record_entry(
        db,
        listed_proposal.id,
        EntryType.PLEDGE_IN,
        5_000_000,
        kunci_duplikat,
        clock=clock,
    )
    assert gagal is None

    berikutnya = await record_entry(
        db,
        listed_proposal.id,
        EntryType.PLEDGE_IN,
        2_000_000,
        f"pledge-lain:{listed_proposal.id}",
        clock=clock,
    )
    assert berikutnya is not None
    await db.flush()

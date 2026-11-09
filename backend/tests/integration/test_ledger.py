"""Entri ledger yang hanya bisa ditambah: constraint database dan idempotensi (BR-51, BR-54, BR-55)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models.ledger import EntryType, LedgerEntry
from app.services.ledger import catat_entri


async def test_br54_entri_nol_ditolak_database(db, listed_proposal):
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


async def test_br54_entri_negatif_ditolak_database(db, listed_proposal):
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


async def test_br55_idempotency_key_mencegah_entri_ganda(db, listed_proposal):
    kunci = f"pledge:{listed_proposal.id}"
    pertama = await catat_entri(
        db, listed_proposal.id, EntryType.PLEDGE_IN, 5_000_000, kunci
    )
    kedua = await catat_entri(
        db, listed_proposal.id, EntryType.PLEDGE_IN, 5_000_000, kunci
    )
    assert pertama is not None
    assert kedua is None  # panggilan kedua tidak menambah apa pun
    jumlah = await db.scalar(
        select(func.count())
        .select_from(LedgerEntry)
        .where(LedgerEntry.idempotency_key == kunci)
    )
    assert jumlah == 1


async def test_0a_catat_entri_nol_mengangkat_integrity_error_bukan_menelan(
    db, listed_proposal
):
    """catat_entri hanya boleh menelan pelanggaran unique idempotency_key
    (BR-55). Pelanggaran CHECK (amount > 0, BR-54) wajib tetap meledak,
    bukan diam-diam dikembalikan sebagai None yang di seluruh kode ini
    berarti 'aman, sudah pernah tercatat'."""
    with pytest.raises(IntegrityError):
        await catat_entri(
            db, listed_proposal.id, EntryType.PLEDGE_IN, 0, "uji:nol-ditelan"
        )


async def test_br55_entri_berikutnya_setelah_duplikat_tetap_tersimpan(
    db, listed_proposal
):
    """Savepoint (begin_nested) pada catat_entri wajib membatasi kerusakan ke
    entri yang gagal saja: transaksi luar tidak boleh ikut ter-abort, atau
    entri sah berikutnya di request yang sama akan ikut hilang."""
    kunci_duplikat = f"pledge:{listed_proposal.id}"
    await catat_entri(
        db, listed_proposal.id, EntryType.PLEDGE_IN, 5_000_000, kunci_duplikat
    )
    gagal = await catat_entri(
        db, listed_proposal.id, EntryType.PLEDGE_IN, 5_000_000, kunci_duplikat
    )
    assert gagal is None

    berikutnya = await catat_entri(
        db,
        listed_proposal.id,
        EntryType.PLEDGE_IN,
        2_000_000,
        f"pledge-lain:{listed_proposal.id}",
    )
    assert berikutnya is not None
    await db.flush()

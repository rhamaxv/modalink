"""R2: invarian uang, diperiksa setelah SETIAP operasi di skenario end-to-end (BR-50..BR-55).

Pencairan milestone (`disbursement_out`) belum punya service sendiri di fase
ini (fase 07, lihat .claude/plan/README.md baris RF-5); di sini entrinya
ditulis langsung lewat `catat_entri`, primitif yang sama yang akan dipakai
service pencairan nanti. Yang diuji adalah invarian ledger itu sendiri, yang
berlaku untuk entri apa pun yang pernah masuk, bukan jalur HTTP milestone yang
belum ada.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.ledger import EntryType, LedgerEntry
from app.models.proposal import Proposal
from app.services.ledger import catat_entri, hitung_saldo, total_terkumpul
from app.services.pledge import cancel_pledge, create_pledge


async def check_invariants(db, proposal_id: UUID, requested: int) -> None:
    entries = (
        await db.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == proposal_id)
        )
    ).all()

    assert all(e.amount > 0 for e in entries), (
        "ada entri dengan nominal nol atau negatif"
    )

    # BR-53: total pencairan tidak pernah melebihi dana yang terkumpul.
    disbursed = sum(
        e.amount for e in entries if e.entry_type is EntryType.DISBURSEMENT_OUT
    )
    assert disbursed <= total_terkumpul(entries), "dana cair melebihi dana terkumpul"
    assert hitung_saldo(entries) >= 0, "saldo escrow negatif"
    assert total_terkumpul(entries) <= requested, "terkumpul melebihi dana yang diminta"

    keys = [e.idempotency_key for e in entries]
    assert len(keys) == len(set(keys)), "idempotency_key duplikat"


@pytest.fixture
def full_scenario(
    db, investor, investor_lain, listed_proposal, clock
) -> Callable[
    [Callable[[object, UUID, int], Awaitable[None]]], AsyncIterator[Proposal]
]:
    """Skenario naik-turun-cair: pledge, pledge, batal, pledge lagi sampai pas
    target, lalu dua pencairan yang bersama-sama pas menghabiskan saldo.
    Memanggil `periksa_setelah_tiap_langkah` setelah SETIAP langkah, bukan
    hanya di akhir, supaya pelanggaran di tengah skenario tidak lolos hanya
    karena keadaan akhirnya kebetulan benar."""

    async def _run(periksa_setelah_tiap_langkah):
        requested = listed_proposal.requested_amount

        async def _periksa() -> None:
            await periksa_setelah_tiap_langkah(db, listed_proposal.id, requested)

        pertama = await create_pledge(
            db, investor.user, listed_proposal, 4_000_000, clock
        )
        await _periksa()
        yield listed_proposal

        await create_pledge(db, investor_lain.user, listed_proposal, 3_000_000, clock)
        await _periksa()
        yield listed_proposal

        await cancel_pledge(db, listed_proposal, pertama, clock)
        await _periksa()
        yield listed_proposal

        await create_pledge(db, investor.user, listed_proposal, 7_000_000, clock)
        await _periksa()  # total pas 10 juta, proposal funded
        yield listed_proposal

        await catat_entri(
            db,
            listed_proposal.id,
            EntryType.DISBURSEMENT_OUT,
            6_000_000,
            idempotency_key=f"disburse:{listed_proposal.id}:1",
        )
        await _periksa()
        yield listed_proposal

        await catat_entri(
            db,
            listed_proposal.id,
            EntryType.DISBURSEMENT_OUT,
            4_000_000,
            idempotency_key=f"disburse:{listed_proposal.id}:2",
        )
        await _periksa()
        yield listed_proposal

    return _run


async def test_r2_invariants_hold_after_every_step_of_a_full_scenario(
    db, full_scenario
):
    async for _ in full_scenario(check_invariants):
        pass


async def test_r2_calling_the_same_disbursement_twice_does_not_add_a_row(
    db, funded_proposal
):
    key = f"disburse:{funded_proposal.id}:milestone-1"

    pertama = await catat_entri(
        db,
        funded_proposal.id,
        EntryType.DISBURSEMENT_OUT,
        4_000_000,
        idempotency_key=key,
    )
    kedua = await catat_entri(
        db,
        funded_proposal.id,
        EntryType.DISBURSEMENT_OUT,
        4_000_000,
        idempotency_key=key,
    )
    assert pertama is not None
    assert kedua is None  # panggilan kedua dengan kunci yang sama tidak menambah baris

    jumlah = (
        await db.scalars(
            select(LedgerEntry).where(
                LedgerEntry.proposal_id == funded_proposal.id,
                LedgerEntry.idempotency_key == key,
            )
        )
    ).all()
    assert len(jumlah) == 1


async def _ledger_fingerprint(db, proposal_id: UUID) -> frozenset[tuple]:
    """Himpunan (id, entry_type, amount, idempotency_key) seluruh baris
    ledger milik satu proposal. Himpunan lama yang tetap jadi himpunan bagian
    dari yang baru membuktikan tidak ada baris yang berubah atau hilang; UPDATE
    mengubah elemen di posisi id yang sama, DELETE menghapusnya, keduanya
    membuat anggota lama hilang dari himpunan baru."""
    entries = (
        await db.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == proposal_id)
        )
    ).all()
    return frozenset((e.id, e.entry_type, e.amount, e.idempotency_key) for e in entries)


async def test_r2_ledger_rows_are_never_altered_after_insert(db, funded_proposal):
    before = await _ledger_fingerprint(db, funded_proposal.id)
    await catat_entri(
        db,
        funded_proposal.id,
        EntryType.DISBURSEMENT_OUT,
        5_000_000,
        idempotency_key=f"disburse:{funded_proposal.id}:milestone-1",
    )
    after = await _ledger_fingerprint(db, funded_proposal.id)
    assert before <= after, "ada baris lama yang berubah atau hilang"

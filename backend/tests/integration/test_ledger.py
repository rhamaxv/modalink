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


async def test_investor_can_read_the_money_trail_of_a_proposal_they_funded(
    client, listed_proposal, investor
):
    """Catatan ledger sudah ada sejak awal, tapi satu-satunya jalan membacanya
    adalah endpoint internal yang hanya hidup saat ENV=dev. Di produksi,
    investor yang menaruh uang tidak bisa melihat apa pun."""
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        json={"amount": 3_000_000},
        headers=investor.headers,
    )
    body = (
        await client.get(
            f"/api/v1/proposals/{listed_proposal.id}/ledger",
            headers=investor.headers,
        )
    ).json()

    assert body["total_masuk"] == 3_000_000
    assert body["total_cair"] == 0
    assert body["balance"] == 3_000_000
    assert [e["entry_type"] for e in body["entries"]] == ["pledge_in"]
    # Baris yang dicatat pemanggil sendiri ditandai, supaya investor bisa
    # menemukan pledge-nya di antara pledge orang lain.
    assert body["entries"][0]["milik_saya"] is True


async def test_the_money_trail_never_names_who_made_each_entry(
    client, listed_proposal, investor, investor_lain
):
    """Penyamaran identitas investor (10-api-contract.md:106-107) tidak boleh
    dibatalkan lewat pintu belakang ini: actor_id setiap baris akan membuat
    siapa pun yang berhak membaca daftar ini bisa mencocokkan nominal dengan
    orangnya, persis yang dilarang pada daftar pledge."""
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        json={"amount": 3_000_000},
        headers=investor.headers,
    )
    body = (
        await client.get(
            f"/api/v1/proposals/{listed_proposal.id}/ledger",
            headers=investor_lain.headers,
        )
    ).json()

    for entri in body["entries"]:
        assert "actor_id" not in entri
        assert "idempotency_key" not in entri
        # Baris milik orang lain tidak pernah ditandai sebagai milik sendiri.
        assert entri["milik_saya"] is False


async def test_a_cancelled_pledge_shows_as_a_refund_line_not_a_deleted_one(
    client, listed_proposal, investor
):
    """Ledger append-only: pembatalan menambah baris refund_out, tidak pernah
    menghapus baris pledge_in. Riwayatnya harus memperlihatkan keduanya."""
    pledge = (
        await client.post(
            f"/api/v1/proposals/{listed_proposal.id}/pledges",
            json={"amount": 3_000_000},
            headers=investor.headers,
        )
    ).json()
    await client.delete(f"/api/v1/pledges/{pledge['id']}", headers=investor.headers)

    body = (
        await client.get(
            f"/api/v1/proposals/{listed_proposal.id}/ledger",
            headers=investor.headers,
        )
    ).json()
    assert [e["entry_type"] for e in body["entries"]] == ["pledge_in", "refund_out"]
    assert body["balance"] == 0
    assert body["total_masuk"] == 0


async def test_an_unrelated_umkm_cannot_read_someone_elses_money_trail(
    client, listed_proposal, umkm
):
    """404, bukan 403: UMKM lain tidak boleh sekaligus mengonfirmasi bahwa
    proposal ini ada. listed_proposal dimiliki umkm_lain (tests/conftest.py)."""
    r = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/ledger", headers=umkm.headers
    )
    assert r.status_code == 404


async def test_an_anonymous_visitor_cannot_read_the_money_trail(
    client, listed_proposal
):
    assert (
        await client.get(f"/api/v1/proposals/{listed_proposal.id}/ledger")
    ).status_code == 401


async def test_a_disbursement_records_where_the_money_went(
    client, db, funded_proposal, investor
):
    """Rekening tujuan dicatat pada baris pencairannya sendiri.

    Tanpa ini, riwayat dana menjawab "berapa" dan "kapan" tapi tidak pernah
    "ke mana", padahal itu pertanyaan pertama siapa pun yang mengecek apakah
    dananya sungguh sampai.
    """
    from sqlmodel import select

    from app.models.proposal import ProposalMilestone

    milestone = await db.scalar(
        select(ProposalMilestone)
        .where(ProposalMilestone.proposal_id == funded_proposal.id)
        .order_by(ProposalMilestone.seq)
    )
    assert milestone is not None
    r = await client.post(
        f"/api/v1/milestones/{milestone.id}/approve", headers=investor.headers
    )
    assert r.status_code == 200, r.text

    body = (
        await client.get(
            f"/api/v1/proposals/{funded_proposal.id}/ledger", headers=investor.headers
        )
    ).json()
    cair = [e for e in body["entries"] if e["entry_type"] == "disbursement_out"]
    assert len(cair) == 1
    # Bank dan empat digit terakhir, tidak pernah nomor penuh: yang tersimpan
    # di database sejak awal memang hanya empat digit itu.
    assert cair[0]["destination_label"] is not None
    assert "••••" in cair[0]["destination_label"]
    assert "4321" in cair[0]["destination_label"]

    # Baris pledge tidak punya rekening tujuan: uang masuk tidak dikirim ke
    # mana pun.
    masuk = [e for e in body["entries"] if e["entry_type"] == "pledge_in"]
    assert masuk and all(e["destination_label"] is None for e in masuk)

"""Evaluasi kedaluwarsa pendanaan secara lazy (D-06, BR-61, BR-62, BR-65, T-05, T-08)."""

from sqlalchemy import select

from app.models.ledger import EntryType, LedgerEntry
from app.models.pledge import Pledge, PledgeStatus
from app.models.proposal import ProposalStatus
from app.services.ledger import hitung_saldo


async def ambil_ledger(db, proposal_id):
    hasil = await db.scalars(
        select(LedgerEntry).where(LedgerEntry.proposal_id == proposal_id)
    )
    return list(hasil)


# Alias: brief fase ini memakai dua nama berbeda untuk query yang sama
# (`ambil_ledger` di test_t08/test_br65, `ambil_entri` di test_br62).
ambil_entri = ambil_ledger


async def total_pledge_aktif(db, proposal_id):
    hasil = await db.scalars(
        select(Pledge).where(
            Pledge.proposal_id == proposal_id, Pledge.status == PledgeStatus.ACTIVE
        )
    )
    return sum(p.amount for p in hasil)


async def test_t05_listed_without_pledge_becomes_failed_after_deadline(
    client, db, listed_proposal, majukan
):
    await majukan(hari=30)
    detail = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert detail["status"] == "failed"


async def test_t08_partially_funded_becomes_failed_and_pledge_refunded(
    client, db, listed_proposal, investor, majukan
):
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    await majukan(hari=30)

    detail = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert detail["status"] == "failed"

    entri = await ambil_ledger(db, listed_proposal.id)
    assert any(
        e.entry_type is EntryType.REFUND_OUT and e.amount == 4_000_000 for e in entri
    )
    assert hitung_saldo(entri) == 0


async def test_funded_proposal_unaffected_by_deadline(
    client, db, funded_proposal, majukan
):
    await majukan(hari=365)
    detail = (await client.get(f"/api/v1/proposals/{funded_proposal.id}")).json()
    assert detail["status"] == "funded"


async def test_evaluation_is_idempotent_does_not_refund_twice(
    client, db, listed_proposal, investor, majukan
):
    """Test keempat yang paling penting di task ini: evaluasi lazy berjalan di
    setiap pembacaan, jadi tanpa penjagaan idempotensi ia mencatat refund
    berkali-kali. Jumlah pembacaan dikontrol eksplisit (5), bukan
    "beberapa kali", supaya kalau suatu hari ini merah, alasannya jelas:
    ada entri refund_out ekstra per pembacaan ekstra."""
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    await majukan(hari=30)

    JUMLAH_PEMBACAAN = 5
    for _ in range(JUMLAH_PEMBACAAN):
        await client.get(f"/api/v1/proposals/{listed_proposal.id}")

    refund = [
        e
        for e in await ambil_ledger(db, listed_proposal.id)
        if e.entry_type is EntryType.REFUND_OUT
    ]
    assert len(refund) == 1


async def test_br65_proposal_submitted_just_before_apply_deadline_still_has_funding_window(
    client, db, campaign, umkm, investor, majukan, body_proposal
):
    """Proposal masuk sehari sebelum apply_deadline, lalu didanai setelahnya (D-16)."""
    await majukan(hari=6)  # apply_deadline hari ke-7, funding_deadline hari ke-21
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    pid = res.json()["id"]

    await majukan(hari=5)  # hari ke-11, masih di dalam jendela pendanaan
    pledge = await client.post(
        f"/api/v1/proposals/{pid}/pledges",
        headers=investor.headers,
        json={"amount": 10_000_000},
    )
    assert pledge.status_code == 201
    assert (await client.get(f"/api/v1/proposals/{pid}")).json()["status"] == "funded"


async def test_br62_failed_proposal_with_active_pledge_still_refunded(
    client, db, listed_proposal, investor, clock, majukan
):
    """Proposal yang sudah failed tapi masih memegang pledge aktif wajib ikut direkonsiliasi.

    Kasus ini nyata: pledge yang diterima tepat setelah funding_deadline lewat
    membuat recompute_funding_status menulis failed sementara pledge-nya tetap
    aktif. Kalau evaluasi_kedaluwarsa menyaring status saja lewat AKTIF,
    proposal itu dilewati selamanya dan uangnya tidak pernah kembali.
    """
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 4_000_000},
    )
    await majukan(hari=30)

    # Paksa keadaan yang dilaporkan review f06-b: failed, tapi pledge masih aktif.
    listed_proposal.status = ProposalStatus.FAILED
    await db.flush()

    await client.get(f"/api/v1/proposals/{listed_proposal.id}")

    entri = await ambil_entri(db, listed_proposal.id)
    assert any(e.entry_type is EntryType.REFUND_OUT for e in entri), (
        "proposal failed dengan pledge aktif tidak direfund; uang investor terjebak"
    )
    assert await total_pledge_aktif(db, listed_proposal.id) == 0

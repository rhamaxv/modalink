"""R4: jalur-jalur yang berakhir tanpa pendanaan atau ditolak."""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

import pytest
from sqlalchemy import select

from app.models.ledger import EntryType, LedgerEntry
from app.models.proposal import Proposal, ProposalMilestone, ProposalStatus
from app.models.user import Role
from app.services.ledger import compute_balance, total_pledge_aktif


@pytest.fixture
async def investor_a(db, buat_akun):
    return await buat_akun(db, "investor-a-r4@contoh.id", Role.INVESTOR)


@pytest.fixture
async def investor_b(db, buat_akun):
    return await buat_akun(db, "investor-b-r4@contoh.id", Role.INVESTOR)


@pytest.fixture
async def investor_kecil(db, buat_akun):
    """Investor terdaftar, tapi tidak pernah pledge pada funded_proposal --
    bukan lead investor-nya (BR-23), dipakai menguji 403 approve milestone."""
    return await buat_akun(db, "investor-kecil-r4@contoh.id", Role.INVESTOR)


@dataclass
class ProposalWithMilestones:
    """Pembungkus tipis yang sama polanya dengan ProposalWithPledge di
    tests/conftest.py: Proposal sengaja tidak punya relationship() ke
    ProposalMilestone, jadi `.milestones` di sini query langsung, bukan
    atribut ORM."""

    proposal: Proposal
    milestones: list[ProposalMilestone]

    def __getattr__(self, name: str):
        return getattr(self.proposal, name)


@pytest.fixture
async def failed_proposal(client, db, campaign, umkm, majukan, body_proposal):
    """Proposal `failed` sungguhan lewat jalur HTTP asli (submit -> listed
    lewat scoring mock -> deadline lewat tanpa satu pledge pun), bukan status
    yang diset langsung -- sama alasannya dengan fixture lain di
    tests/conftest.py."""
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    pid = UUID(res.json()["id"])

    await majukan(hari=30)  # funding_deadline campaign fixture jatuh di hari ke-21
    await client.get(f"/api/v1/proposals/{pid}")

    proposal = await db.get(Proposal, pid)
    await db.refresh(proposal)
    milestones = list(
        (
            await db.scalars(
                select(ProposalMilestone)
                .where(ProposalMilestone.proposal_id == pid)
                .order_by(ProposalMilestone.seq)
            )
        ).all()
    )
    return ProposalWithMilestones(proposal=proposal, milestones=milestones)


async def ambil_ledger(db, proposal_id):
    hasil = await db.scalars(
        select(LedgerEntry).where(LedgerEntry.proposal_id == proposal_id)
    )
    return list(hasil)


async def pledge(client, investor, proposal: Proposal, amount: int):
    return await client.post(
        f"/api/v1/proposals/{proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": amount},
    )


async def test_r4_no_failed_proposal_still_holds_active_pledge(db):
    """Invarian, bukan skenario: diperiksa untuk semua proposal failed yang ada.

    Dua jalan menuju keadaan rusak ini sudah pernah direproduksi terhadap database
    sungguhan di review fase 06: pledge yang diterima setelah funding_deadline lewat,
    dan pembatalan yang menjatuhkan total di bawah target setelah tenggat. Keduanya
    meninggalkan pledge_in tanpa refund_out dan escrow menggantung.

    Memeriksa seluruh proposal failed, bukan satu yang diketahui, supaya jalan ketiga
    yang belum terpikirkan pun tertangkap.
    """
    gagal = (
        await db.scalars(
            select(Proposal).where(Proposal.status == ProposalStatus.FAILED)
        )
    ).all()

    for p in gagal:
        aktif = await total_pledge_aktif(db, p.id)
        assert aktif == 0, (
            f"proposal {p.id} berstatus failed tapi masih memegang pledge aktif "
            f"senilai {aktif}; uang investor terjebak tanpa refund_out"
        )


async def test_r4_deadline_past_refunds_all_pledges(
    client, db, listed_proposal, investor_a, investor_b, majukan
):
    await pledge(client, investor_a, listed_proposal, 3_000_000)
    await pledge(client, investor_b, listed_proposal, 4_000_000)
    await majukan(hari=30)
    await client.get(f"/api/v1/proposals/{listed_proposal.id}")

    entri = await ambil_ledger(db, listed_proposal.id)
    refund = sum(e.amount for e in entri if e.entry_type is EntryType.REFUND_OUT)
    assert refund == 7_000_000
    assert compute_balance(entri) == 0
    await db.refresh(listed_proposal)
    assert listed_proposal.status is ProposalStatus.FAILED


async def test_br60_lazy_expiry_refund_uses_injected_clock_not_wall_clock(
    client, db, listed_proposal, investor_a, majukan
):
    """Finding 4: record_entry dulu punya jam sendiri (SystemClock module-level)
    lepas dari clock yang disuntikkan permintaan. Refund yang ditulis lazy
    expiry (evaluate_expiry) tetap tertanggal mendekati jam dinding,
    bukan tanggal virtual yang memicunya -- padahal pledge_in yang sama
    sudah tercatat jauh lebih awal. GET /internal/ledger/{id}, yang
    diurutkan created_at supaya juri bisa mengaudit uang, bisa menampilkan
    refund SEBELUM deadline virtual yang menyebabkannya."""
    await pledge(client, investor_a, listed_proposal, 3_000_000)
    pledge_in = next(
        e
        for e in await ambil_ledger(db, listed_proposal.id)
        if e.entry_type is EntryType.PLEDGE_IN
    )

    await majukan(hari=30)
    await client.get(f"/api/v1/proposals/{listed_proposal.id}")

    refund = next(
        e
        for e in await ambil_ledger(db, listed_proposal.id)
        if e.entry_type is EntryType.REFUND_OUT
    )
    assert refund.created_at - pledge_in.created_at >= timedelta(days=29)


async def test_r4_pledge_exceeding_remaining_includes_correct_remaining_amount(
    client, investor, listed_proposal
):
    await pledge(client, investor, listed_proposal, 7_000_000)
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 5_000_000},
    )
    assert res.status_code == 409
    assert res.json()["error"]["detail"]["remaining_amount"] == 3_000_000


async def test_r4_second_proposal_in_same_campaign_rejected(
    client, umkm, campaign, body_proposal
):
    await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    assert res.status_code == 409


async def test_r4_skipped_milestone_rejected(client, umkm_lain, funded_proposal):
    # `umkm_lain`, bukan `umkm`: funded_proposal berasal dari listed_proposal
    # yang pemiliknya umkm_lain. Memakai akun yang salah membuat test ini
    # berhenti di pemeriksaan kepemilikan (404) sebelum sempat membuktikan
    # prasyarat urutan milestone (409), jadi ia akan hijau karena alasan
    # yang keliru.
    m2 = funded_proposal.milestones[1]
    res = await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json={"narrative": "x" * 60},
    )
    assert res.status_code == 409


async def test_r4_non_lead_investor_cannot_approve(
    client, investor_kecil, funded_proposal
):
    m1 = funded_proposal.milestones[0]
    res = await client.post(
        f"/api/v1/milestones/{m1.id}/approve", headers=investor_kecil.headers
    )
    # 404, bukan 403: pola seluruh project ini adalah menolak tanpa
    # memberitahu bahwa sumber dayanya ada. 403 akan mengonfirmasi ke
    # investor mana pun bahwa milestone dengan id itu nyata.
    assert res.status_code == 404


async def test_r4_funded_proposal_rejects_new_pledge(
    client, investor_b, funded_proposal
):
    res = await client.post(
        f"/api/v1/proposals/{funded_proposal.id}/pledges",
        headers=investor_b.headers,
        json={"amount": 1_000_000},
    )
    assert res.status_code == 409


async def test_r4_failed_proposal_rejects_new_pledge(client, investor, failed_proposal):
    res = await client.post(
        f"/api/v1/proposals/{failed_proposal.id}/pledges",
        headers=investor.headers,
        json={"amount": 1_000_000},
    )
    assert res.status_code == 409


async def test_r4_failed_proposal_never_disburses(
    client, db, investor, failed_proposal
):
    """Yang dijamin adalah tidak ada dana cair, bukan satu kode status tertentu.

    `failed_proposal` gagal tanpa satu pledge pun, jadi ia tidak punya lead
    investor dan pagar otorisasi menolak lebih dulu dengan 404. Kode mana yang
    muncul tergantung pagar mana yang lebih dulu kena, dan itu detail
    implementasi; yang tidak boleh berubah adalah ledgernya tetap bersih.
    """
    m1 = failed_proposal.milestones[0]
    res = await client.post(
        f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers
    )
    assert res.status_code >= 400

    entri = await ambil_ledger(db, failed_proposal.id)
    assert not [e for e in entri if e.entry_type is EntryType.DISBURSEMENT_OUT], (
        "ada disbursement_out pada proposal failed; dana cair dari campaign gagal"
    )

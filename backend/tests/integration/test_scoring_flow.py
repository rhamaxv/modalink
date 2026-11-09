"""Orkestrasi scoring: job langsung terpicu saat proposal masuk (BR-70 sampai BR-78)."""

from sqlalchemy import func, select

from app.models.proposal import ProposalStatus, ScoringStatus
from app.models.scoring import ScoringResult


async def test_proposal_masuk_langsung_dapat_skor(
    client, umkm, campaign, body_proposal
):
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(),
    )
    pid = res.json()["id"]
    detail = (await client.get(f"/api/v1/proposals/{pid}", headers=umkm.headers)).json()
    assert detail["scoring_status"] == "done"
    assert detail["status"] == "listed"


async def test_br73_skor_di_bawah_threshold_jadi_rejected(
    client, umkm, campaign, body_proposal
):
    body = body_proposal()
    body["business_profile"] += " [[SCORE:40]]"  # threshold campaign 60
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body,
    )
    pid = res.json()["id"]
    detail = (await client.get(f"/api/v1/proposals/{pid}", headers=umkm.headers)).json()
    assert detail["status"] == "rejected"


async def test_br76_rescore_menambah_baris_bukan_menimpa(
    client, db, umkm, proposal_scoring_gagal
):
    await client.post(
        f"/api/v1/proposals/{proposal_scoring_gagal.id}/rescore", headers=umkm.headers
    )
    jumlah = await db.scalar(
        select(func.count())
        .select_from(ScoringResult)
        .where(ScoringResult.proposal_id == proposal_scoring_gagal.id)
    )
    assert jumlah >= 1


async def test_br76_dua_percobaan_scoring_sungguhan_meninggalkan_dua_baris(
    db, submitted_proposal, engine_mock, clock
):
    """H-3: test di atas mulai dari nol baris, jadi `jumlah >= 1` tidak bisa
    membedakan "menambah" dari "menimpa" (kedua kasus lolos). Test ini
    menjalankan scoring sungguhan dua kali dan memeriksa dua baris itu
    berbeda dan keduanya tetap ada, bukan baris pertama tertimpa baris
    kedua.

    Proposal dipaksa balik ke submitted langsung di sini, bukan lewat
    minta_rescore (yang hanya mengizinkan rescore dari status failed):
    tujuannya murni membuktikan tabel scoring_results append-only, bukan
    mengulang aturan kapan rescore boleh dipicu (sudah diuji R6/BR-75).
    """
    from app.services.scoring import jalankan_scoring

    await jalankan_scoring(db, submitted_proposal.id, engine_mock, clock)
    await db.refresh(submitted_proposal)
    baris_pertama = (
        await db.scalars(
            select(ScoringResult).where(
                ScoringResult.proposal_id == submitted_proposal.id
            )
        )
    ).one()

    submitted_proposal.scoring_status = ScoringStatus.PENDING
    submitted_proposal.status = ProposalStatus.SUBMITTED
    # Penanda skor berbeda dari skor dasar baris pertama supaya kedua baris
    # terbukti dibedakan oleh total_score, bukan cuma oleh id.
    submitted_proposal.business_profile += " [[SCORE:80]]"
    await db.flush()
    await jalankan_scoring(db, submitted_proposal.id, engine_mock, clock)

    semua_baris = (
        await db.scalars(
            select(ScoringResult)
            .where(ScoringResult.proposal_id == submitted_proposal.id)
            .order_by("created_at", "id")
        )
    ).all()
    assert len(semua_baris) == 2
    assert baris_pertama.id in {b.id for b in semua_baris}
    baris_kedua = next(b for b in semua_baris if b.id != baris_pertama.id)
    assert baris_kedua.total_score == 80
    assert baris_kedua.total_score != baris_pertama.total_score


async def test_br75_job_terpicu_dua_kali_tidak_menghasilkan_dua_transisi(
    db, listed_proposal, engine_mock, clock
):
    from app.services.scoring import jalankan_scoring

    await jalankan_scoring(db, listed_proposal.id, engine_mock, clock)
    await db.refresh(listed_proposal)
    assert listed_proposal.status is ProposalStatus.LISTED  # tidak berubah, tidak error


async def test_t50_t51_scoring_status_berjalan_pending_processing_done(
    db, submitted_proposal, engine_mock, clock
):
    from app.services.scoring import jalankan_scoring

    assert submitted_proposal.scoring_status is ScoringStatus.PENDING
    await jalankan_scoring(db, submitted_proposal.id, engine_mock, clock)
    await db.refresh(submitted_proposal)
    assert submitted_proposal.scoring_status is ScoringStatus.DONE


async def test_t52_scoring_status_jadi_failed_saat_engine_meledak(
    db, submitted_proposal, engine_meledak, clock
):
    from app.services.scoring import jalankan_scoring

    await jalankan_scoring(db, submitted_proposal.id, engine_meledak, clock)
    await db.refresh(submitted_proposal)
    assert submitted_proposal.scoring_status is ScoringStatus.FAILED


async def test_t53_rescore_mengembalikan_scoring_status_ke_pending(
    client, db, umkm, proposal_scoring_gagal
):
    await client.post(
        f"/api/v1/proposals/{proposal_scoring_gagal.id}/rescore", headers=umkm.headers
    )
    await db.refresh(proposal_scoring_gagal)
    assert proposal_scoring_gagal.scoring_status in {
        ScoringStatus.PENDING,
        ScoringStatus.PROCESSING,
        ScoringStatus.DONE,
    }


async def test_br35_komunitas_tidak_bisa_melihat_red_flag(
    client, community, listed_proposal
):
    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/scoring", headers=community.headers
    )
    assert res.status_code == 403


async def test_rescore_ditolak_404_untuk_umkm_bukan_pemilik_proposal(
    client, umkm_lain, proposal_scoring_gagal
):
    """H-2: proposal_scoring_gagal milik `umkm`, bukan `umkm_lain`. Peran
    sudah benar (require_role meloloskan UMKM), tapi bukan pemilik; 404,
    bukan 403, karena keberadaan proposal orang lain sendiri sudah bocor."""
    res = await client.post(
        f"/api/v1/proposals/{proposal_scoring_gagal.id}/rescore",
        headers=umkm_lain.headers,
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "proposal_tidak_ada"


async def test_rescore_ditolak_404_untuk_investor_bukan_pemilik_campaign(
    client, investor_lain, proposal_scoring_gagal
):
    """H-2: campaign dari proposal_scoring_gagal milik `investor`, bukan
    `investor_lain`. Sebelumnya investor manapun lolos lewat peran saja dan
    bisa memicu rescore (membakar kuota Gemini) atas proposal orang lain."""
    res = await client.post(
        f"/api/v1/proposals/{proposal_scoring_gagal.id}/rescore",
        headers=investor_lain.headers,
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "proposal_tidak_ada"


async def test_rescore_diterima_untuk_pemilik_campaign_bukan_pemilik_proposal(
    client, investor, proposal_scoring_gagal
):
    """H-2: `investor` bukan pemilik proposal (itu `umkm`), tapi pemilik
    campaign-nya, dan kontrak (10-api-contract.md) mengizinkan keduanya."""
    res = await client.post(
        f"/api/v1/proposals/{proposal_scoring_gagal.id}/rescore",
        headers=investor.headers,
    )
    assert res.status_code == 202


async def test_scoring_get_ditolak_404_untuk_umkm_bukan_pemilik_proposal(
    client, umkm, listed_proposal
):
    """H-2: listed_proposal milik `umkm_lain`, bukan `umkm`. Sebelumnya UMKM
    manapun lolos lewat peran saja dan bisa membaca red flag serta brief
    proposal UMKM lain."""
    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/scoring", headers=umkm.headers
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "proposal_tidak_ada"


async def test_scoring_get_diterima_untuk_investor_manapun(
    client, investor_lain, listed_proposal
):
    """Kontrak mengizinkan "investor" secara blanket di endpoint ini (bukan
    "pemilik campaign"), beda dari rescore; `investor_lain` bukan pemilik
    campaign dari listed_proposal tapi tetap harus lolos."""
    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/scoring", headers=investor_lain.headers
    )
    assert res.status_code == 200

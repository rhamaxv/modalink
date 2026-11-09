"""R6: tidak ada mode kegagalan AI yang menghasilkan 'rejected' (D-09, BR-74)."""

import pytest
from sqlalchemy import func, select

from app.models.proposal import ProposalStatus, ScoringStatus
from app.models.scoring import ScoringResult
from app.services.scoring import jalankan_scoring


class EngineMeledak:
    name, model = "palsu", "palsu"

    def __init__(self, exc):
        self._exc = exc

    async def score(self, proposal, campaign):
        raise self._exc


MODE_GAGAL = [
    pytest.param(TimeoutError(), id="timeout"),
    pytest.param(ConnectionError("jaringan putus"), id="jaringan"),
    pytest.param(ValueError("output gagal validasi"), id="schema"),
    pytest.param(RuntimeError("GEMINI_API_KEY tidak ada"), id="tanpa-api-key"),
]


@pytest.mark.parametrize("kegagalan", MODE_GAGAL)
async def test_r6_kegagalan_tidak_mengubah_status_proposal(
    db, submitted_proposal, clock, kegagalan
):
    await jalankan_scoring(db, submitted_proposal.id, EngineMeledak(kegagalan), clock)
    await db.refresh(submitted_proposal)

    assert submitted_proposal.scoring_status is ScoringStatus.FAILED
    assert submitted_proposal.status is ProposalStatus.SUBMITTED  # bukan rejected


@pytest.mark.parametrize("kegagalan", MODE_GAGAL)
async def test_r6_kegagalan_tidak_meninggalkan_baris_scoring(
    db, submitted_proposal, clock, kegagalan
):
    await jalankan_scoring(db, submitted_proposal.id, EngineMeledak(kegagalan), clock)
    jumlah = await db.scalar(
        select(func.count())
        .select_from(ScoringResult)
        .where(ScoringResult.proposal_id == submitted_proposal.id)
    )
    assert jumlah == 0


async def test_r6_rescore_mengembalikan_ke_pending(
    client, umkm, proposal_scoring_gagal
):
    res = await client.post(
        f"/api/v1/proposals/{proposal_scoring_gagal.id}/rescore", headers=umkm.headers
    )
    assert res.status_code == 202


async def test_r6_rescore_ditolak_saat_scoring_sudah_selesai(
    client, umkm, listed_proposal
):
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/rescore", headers=umkm.headers
    )
    assert res.status_code == 409


async def test_r6_job_dua_kali_hanya_satu_transisi(
    db, submitted_proposal, engine_mock, clock
):
    await jalankan_scoring(db, submitted_proposal.id, engine_mock, clock)
    status_pertama = submitted_proposal.status
    await jalankan_scoring(db, submitted_proposal.id, engine_mock, clock)
    await db.refresh(submitted_proposal)
    assert submitted_proposal.status is status_pertama

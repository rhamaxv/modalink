"""Test kontrak Gemini sungguhan (D-07, D-09). Di-skip default, dijalankan
manual lewat `make test-live` setelah prompt atau schema berubah."""

import pytest

from app.domain.verdict import total_score

pytestmark = pytest.mark.live


async def test_live_output_lolos_validasi(
    gemini_engine, proposal_bagus, campaign_draft
):
    skor = await gemini_engine.score(proposal_bagus, campaign_draft)
    assert 0 <= total_score(skor) <= 100


async def test_live_urutan_skor_masuk_akal(
    gemini_engine, proposal_bagus, proposal_biasa, proposal_red_flag, campaign_draft
):
    bagus = total_score(await gemini_engine.score(proposal_bagus, campaign_draft))
    biasa = total_score(await gemini_engine.score(proposal_biasa, campaign_draft))
    buruk = total_score(await gemini_engine.score(proposal_red_flag, campaign_draft))
    assert bagus > biasa > buruk


async def test_live_proyeksi_berlebihan_memicu_red_flag_kritis(
    gemini_engine, proposal_red_flag, campaign_draft
):
    skor = await gemini_engine.score(proposal_red_flag, campaign_draft)
    assert any(f.severity == "critical" for f in skor.red_flags)


async def test_live_setiap_evidence_benar_benar_ada_di_proposal(
    gemini_engine, proposal_red_flag, campaign_draft
):
    """Paling sering jebol saat prompt diubah, dan paling berguna."""
    skor = await gemini_engine.score(proposal_red_flag, campaign_draft)
    isi = (
        f"{proposal_red_flag.business_profile} {proposal_red_flag.fund_usage_plan} "
        f"{proposal_red_flag.business_projection}"
    ).casefold()
    for f in skor.red_flags:
        assert f.evidence.casefold() in isi, f"kutipan karangan: {f.evidence!r}"

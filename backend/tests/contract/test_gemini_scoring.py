"""Test kontrak Gemini sungguhan (D-07, D-09). Di-skip default, dijalankan
manual lewat `make test-live` setelah prompt atau schema berubah."""

import pytest

from app.domain.verdict import total_score

pytestmark = pytest.mark.live


async def test_live_output_passes_validation(
    gemini_engine, proposal_bagus, campaign_draft
):
    skor = await gemini_engine.score(proposal_bagus, campaign_draft)
    assert 0 <= total_score(skor) <= 100


async def test_live_score_ordering_makes_sense(
    gemini_engine, proposal_bagus, proposal_biasa, proposal_red_flag, campaign_draft
):
    bagus = total_score(await gemini_engine.score(proposal_bagus, campaign_draft))
    biasa = total_score(await gemini_engine.score(proposal_biasa, campaign_draft))
    buruk = total_score(await gemini_engine.score(proposal_red_flag, campaign_draft))
    assert bagus > biasa > buruk


async def test_live_excessive_projection_triggers_critical_red_flag(
    gemini_engine, proposal_red_flag, campaign_draft
):
    skor = await gemini_engine.score(proposal_red_flag, campaign_draft)
    assert any(f.severity == "critical" for f in skor.red_flags)


async def test_live_every_evidence_actually_exists_in_proposal(
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

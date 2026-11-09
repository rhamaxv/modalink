"""Test MockScoringEngine: deterministik, dan mock tetap masuk akal (D-07)."""

import pytest

from app.ai.engine import build_engine
from app.ai.mock_engine import MockScoringEngine
from app.config import settings
from app.domain.verdict import total_score


async def test_mock_is_deterministic(proposal_draft, campaign_draft):
    engine = MockScoringEngine()
    a = await engine.score(proposal_draft, campaign_draft)
    b = await engine.score(proposal_draft, campaign_draft)
    assert a == b


async def test_score_marker_forces_total(proposal_draft, campaign_draft):
    proposal_draft.business_profile += " [[SCORE:59]]"
    skor = await MockScoringEngine().score(proposal_draft, campaign_draft)
    assert total_score(skor) == 59


async def test_red_flag_marker_produces_critical_flag(proposal_draft, campaign_draft):
    proposal_draft.business_projection += " [[RED_FLAG:critical]]"
    skor = await MockScoringEngine().score(proposal_draft, campaign_draft)
    assert any(f.severity == "critical" for f in skor.red_flags)


async def test_complete_proposal_scores_higher_than_thin_one(
    proposal_draft, proposal_draft_tipis, campaign_draft
):
    engine = MockScoringEngine()
    lengkap = total_score(await engine.score(proposal_draft, campaign_draft))
    tipis = total_score(await engine.score(proposal_draft_tipis, campaign_draft))
    assert lengkap > tipis


def test_build_engine_scoring_engine_mock_returns_mock():
    engine = build_engine(settings.model_copy(update={"scoring_engine": "mock"}))
    assert isinstance(engine, MockScoringEngine)


def test_build_engine_other_scoring_engine_not_yet_supported():
    with pytest.raises(NotImplementedError):
        build_engine(settings.model_copy(update={"scoring_engine": "entah"}))


def test_build_engine_scoring_engine_gemini_without_key_fails_clearly():
    """build_engine membangun GeminiEngine lewat from_settings, yang menolak
    dibuat tanpa GEMINI_API_KEY alih-alih gagal samar belakangan."""
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        build_engine(
            settings.model_copy(
                update={"scoring_engine": "gemini", "gemini_api_key": None}
            )
        )

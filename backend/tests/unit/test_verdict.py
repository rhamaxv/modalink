"""Test skema skor AI dan keputusan verdict yang murni di kode (BR-70 sampai BR-78)."""

import pytest
from pydantic import ValidationError

from app.ai.models import Brief, ProposalScore, RedFlag
from app.domain.verdict import Verdict, decide_verdict, total_score


def skor(fit=30, data=20, impact=20, flags=()):
    return ProposalScore(
        fit_score=fit,
        data_quality_score=data,
        impact_score=impact,
        red_flags=list(flags),
        brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
    )


def test_br70_total_is_summed_from_three_components():
    assert total_score(skor(34, 21, 18)) == 73


def test_br70_total_field_from_model_is_discarded():
    """Model yang mengarang 'total' tidak boleh mempengaruhi apa pun."""
    mentah = {
        "fit_score": 10,
        "data_quality_score": 10,
        "impact_score": 10,
        "total": 99,
        "red_flags": [],
        "brief": {"strengths": ["a"], "risks": ["b"], "recommendation": "c"},
    }
    assert total_score(ProposalScore.model_validate(mentah)) == 30


def test_br73_below_threshold_becomes_rejected():
    assert decide_verdict(skor(10, 10, 10), threshold=60) is Verdict.REJECTED


def test_br73_exactly_at_threshold_becomes_listed():
    assert decide_verdict(skor(20, 20, 20), threshold=60) is Verdict.LISTED


def test_br71_threshold_never_enters_the_prompt():
    """Model tidak boleh tahu ambangnya, supaya penilaiannya tidak condong
    menyesuaikan ambang."""
    from pathlib import Path

    prompt = (Path("app/ai/prompts/score_proposal.md")).read_text()
    assert "threshold" not in prompt.lower()
    assert "{score_threshold" not in prompt


def test_br71_verdict_changes_with_different_threshold():
    s = skor(20, 20, 20)  # total 60
    assert decide_verdict(s, threshold=60) is Verdict.LISTED
    assert decide_verdict(s, threshold=61) is Verdict.REJECTED


def test_br72_critical_red_flag_rejects_despite_high_score():
    kritis = RedFlag(
        code="projeksi_tidak_realistis",
        severity="critical",
        message="x",
        evidence="y",
    )
    assert decide_verdict(skor(40, 30, 30, [kritis]), threshold=60) is Verdict.REJECTED


def test_red_flag_warning_does_not_reject():
    ringan = RedFlag(
        code="isian_template", severity="warning", message="x", evidence="y"
    )
    assert decide_verdict(skor(40, 30, 30, [ringan]), threshold=60) is Verdict.LISTED


def test_br78_fit_score_above_40_rejected():
    with pytest.raises(ValidationError):
        ProposalScore(
            fit_score=41,
            data_quality_score=0,
            impact_score=0,
            red_flags=[],
            brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
        )


def test_br78_data_quality_score_above_30_rejected():
    with pytest.raises(ValidationError):
        ProposalScore(
            fit_score=0,
            data_quality_score=31,
            impact_score=0,
            red_flags=[],
            brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
        )


def test_br78_impact_score_above_30_rejected():
    with pytest.raises(ValidationError):
        ProposalScore(
            fit_score=0,
            data_quality_score=0,
            impact_score=31,
            red_flags=[],
            brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
        )


def test_br78_negative_fit_score_rejected():
    with pytest.raises(ValidationError):
        ProposalScore(
            fit_score=-1,
            data_quality_score=0,
            impact_score=0,
            red_flags=[],
            brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
        )

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


def test_br70_total_dijumlahkan_dari_tiga_komponen():
    assert total_score(skor(34, 21, 18)) == 73


def test_br70_field_total_dari_model_dibuang():
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


def test_br73_di_bawah_threshold_jadi_rejected():
    assert decide_verdict(skor(10, 10, 10), threshold=60) is Verdict.REJECTED


def test_br73_tepat_di_threshold_jadi_listed():
    assert decide_verdict(skor(20, 20, 20), threshold=60) is Verdict.LISTED


def test_br71_threshold_tidak_pernah_masuk_ke_prompt():
    """Model tidak boleh tahu ambangnya, supaya penilaiannya tidak condong
    menyesuaikan ambang."""
    from pathlib import Path

    prompt = (Path("app/ai/prompts/score_proposal.md")).read_text()
    assert "threshold" not in prompt.lower()
    assert "{score_threshold" not in prompt


def test_br71_verdict_berubah_mengikuti_threshold_yang_berbeda():
    s = skor(20, 20, 20)  # total 60
    assert decide_verdict(s, threshold=60) is Verdict.LISTED
    assert decide_verdict(s, threshold=61) is Verdict.REJECTED


def test_br72_red_flag_kritis_menolak_meski_skor_tinggi():
    kritis = RedFlag(
        code="projeksi_tidak_realistis",
        severity="critical",
        message="x",
        evidence="y",
    )
    assert decide_verdict(skor(40, 30, 30, [kritis]), threshold=60) is Verdict.REJECTED


def test_red_flag_warning_tidak_menolak():
    ringan = RedFlag(
        code="isian_template", severity="warning", message="x", evidence="y"
    )
    assert decide_verdict(skor(40, 30, 30, [ringan]), threshold=60) is Verdict.LISTED


def test_br78_fit_score_di_atas_40_ditolak():
    with pytest.raises(ValidationError):
        ProposalScore(
            fit_score=41,
            data_quality_score=0,
            impact_score=0,
            red_flags=[],
            brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
        )


def test_br78_data_quality_score_di_atas_30_ditolak():
    with pytest.raises(ValidationError):
        ProposalScore(
            fit_score=0,
            data_quality_score=31,
            impact_score=0,
            red_flags=[],
            brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
        )


def test_br78_impact_score_di_atas_30_ditolak():
    with pytest.raises(ValidationError):
        ProposalScore(
            fit_score=0,
            data_quality_score=0,
            impact_score=31,
            red_flags=[],
            brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
        )


def test_br78_fit_score_negatif_ditolak():
    with pytest.raises(ValidationError):
        ProposalScore(
            fit_score=-1,
            data_quality_score=0,
            impact_score=0,
            red_flags=[],
            brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
        )

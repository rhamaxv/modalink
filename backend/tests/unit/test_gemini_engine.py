"""Test buang_evidence_halusinasi (RF-3): kutipan karangan tidak boleh
sampai ke pemilik usaha sebagai alasan penolakan."""

import pytest

from app.ai.gemini_engine import GeminiEngine, buang_evidence_halusinasi
from app.ai.models import Brief, ProposalScore, RedFlag
from app.config import Settings, settings


def skor_dengan(evidence: str) -> ProposalScore:
    return ProposalScore(
        fit_score=30,
        data_quality_score=20,
        impact_score=20,
        red_flags=[
            RedFlag(
                code="angka_tidak_konsisten",
                severity="critical",
                message="x",
                evidence=evidence,
            )
        ],
        brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
    )


ISI_PROPOSAL = "Omzet rata-rata Rp12 juta per bulan dengan dua pekerja."


def test_rf3_evidence_yang_ada_di_proposal_dipertahankan():
    hasil = buang_evidence_halusinasi(
        skor_dengan("Omzet rata-rata Rp12 juta"), ISI_PROPOSAL
    )
    assert len(hasil.red_flags) == 1


def test_rf3_evidence_yang_tidak_ada_di_proposal_dibuang():
    hasil = buang_evidence_halusinasi(
        skor_dengan("Omzet Rp900 juta per hari"), ISI_PROPOSAL
    )
    assert hasil.red_flags == []


def test_rf3_membuang_red_flag_kritis_halusinasi_mengubah_verdict():
    """Konsekuensi yang harus disadari: proposal tidak jadi ditolak
    karena kutipan yang mendasarinya ternyata karangan."""
    from app.domain.verdict import Verdict, decide_verdict

    kotor = skor_dengan("Omzet Rp900 juta per hari")
    assert decide_verdict(kotor, 60) is Verdict.REJECTED
    bersih = buang_evidence_halusinasi(kotor, ISI_PROPOSAL)
    assert decide_verdict(bersih, 60) is Verdict.LISTED


def test_rf3_pembandingan_mengabaikan_beda_spasi_dan_huruf_besar():
    hasil = buang_evidence_halusinasi(
        skor_dengan("OMZET   RATA-RATA  rp12 JUTA"), ISI_PROPOSAL
    )
    assert len(hasil.red_flags) == 1


def test_rf3_pembandingan_menolak_parafrase():
    """Beda spasi dan huruf besar diabaikan, tapi parafrase tetap dibuang:
    'omzet bulanan dua belas juta' bukan kutipan persis dari isi proposal."""
    hasil = buang_evidence_halusinasi(
        skor_dengan("omzet bulanan dua belas juta"), ISI_PROPOSAL
    )
    assert hasil.red_flags == []


def test_gemini_engine_menolak_dibuat_tanpa_kunci_api():
    """GeminiEngine.from_settings menolak membangun client, bukan gagal
    samar saat score() baru dipanggil belakangan."""
    tanpa_kunci = settings.model_copy(update={"gemini_api_key": None})
    assert isinstance(tanpa_kunci, Settings)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiEngine.from_settings(tanpa_kunci)

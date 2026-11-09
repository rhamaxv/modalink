"""Test buang_evidence_halusinasi (RF-3): kutipan karangan tidak boleh
sampai ke pemilik usaha sebagai alasan penolakan."""

from dataclasses import dataclass

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


class _StubCompletions:
    """Pengganti instructor.AsyncInstructor.chat.completions, tanpa jaringan
    (C-28). Mencatat messages yang dikirim supaya test bisa memeriksa prompt
    yang sungguh dirakit _rakit_isi(), bukan cuma bahwa score() mengembalikan
    sesuatu."""

    def __init__(self, hasil: ProposalScore) -> None:
        self._hasil = hasil
        self.messages_terkirim: list[dict[str, str]] | None = None

    async def create(self, *, model, response_model, max_retries, messages):
        self.messages_terkirim = messages
        return self._hasil


class _StubChat:
    def __init__(self, completions: _StubCompletions) -> None:
        self.completions = completions


class _StubClient:
    def __init__(self, hasil: ProposalScore) -> None:
        self.chat = _StubChat(_StubCompletions(hasil))


@dataclass
class _CampaignLengkap:
    """campaign_draft di unit/conftest.py sengaja cuma punya target_amount
    (C-25: hanya field yang dibaca MockScoringEngine). GeminiEngine._rakit_isi
    juga membaca title/sector/description, jadi test ini butuh draft sendiri
    yang lebih lengkap."""

    title: str
    sector: str
    description: str
    target_amount: int


@pytest.fixture
def campaign_gemini_draft() -> _CampaignLengkap:
    return _CampaignLengkap(
        title="Modal warung kopi Jakarta Timur",
        sector="kuliner",
        description="Mendanai warung kopi skala rumahan.",
        target_amount=50_000_000,
    )


def _bangun_engine_dengan_stub(stub: _StubClient) -> GeminiEngine:
    # __new__, bukan GeminiEngine(client, model, timeout_s): __init__
    # membungkus client lewat instructor.from_genai(client, use_async=True),
    # yang menolak objek selain genai.Client sungguhan. Stub ini menggantikan
    # _client secara langsung, menjaga score() dan _rakit_isi() tetap
    # kode sungguhan yang diuji, tanpa menyentuh jaringan maupun instructor.
    engine = GeminiEngine.__new__(GeminiEngine)
    engine._client = stub
    engine.model = "gemini-2.5-flash"
    engine._timeout_s = 20
    return engine


async def test_score_memanggil_stub_dan_membuang_evidence_halusinasi(
    proposal_draft, campaign_gemini_draft
):
    hasil_mentah = ProposalScore(
        fit_score=30,
        data_quality_score=20,
        impact_score=20,
        red_flags=[
            RedFlag(
                code="angka_tidak_konsisten",
                severity="critical",
                message="genuine",
                # Persis ada di proposal_draft.business_profile (unit/conftest.py).
                evidence="omzet rata-rata Rp12 juta per bulan",
            ),
            RedFlag(
                code="projeksi_tidak_realistis",
                severity="critical",
                message="halusinasi",
                evidence="proyeksi Rp900 juta per hari",
            ),
        ],
        brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
    )
    stub = _StubClient(hasil_mentah)
    engine = _bangun_engine_dengan_stub(stub)

    skor = await engine.score(proposal_draft, campaign_gemini_draft)

    assert [f.code for f in skor.red_flags] == ["angka_tidak_konsisten"]

    prompt_terkirim = stub.chat.completions.messages_terkirim[0]["content"]
    assert proposal_draft.business_name in prompt_terkirim
    assert proposal_draft.business_profile in prompt_terkirim
    assert proposal_draft.fund_usage_plan in prompt_terkirim
    assert proposal_draft.business_projection in prompt_terkirim
    assert str(proposal_draft.requested_amount) in prompt_terkirim

"""Test drop_hallucinated_evidence (RF-3): kutipan karangan tidak boleh
sampai ke pemilik usaha sebagai alasan penolakan."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from app.ai.gemini_engine import (
    DailyQuotaExceeded,
    GeminiEngine,
    PromptTooLarge,
    _DailyBudget,
    drop_hallucinated_evidence,
)
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


def test_rf3_evidence_present_in_proposal_is_kept():
    hasil = drop_hallucinated_evidence(
        skor_dengan("Omzet rata-rata Rp12 juta"), ISI_PROPOSAL
    )
    assert len(hasil.red_flags) == 1


def test_rf3_evidence_not_in_proposal_is_dropped():
    hasil = drop_hallucinated_evidence(
        skor_dengan("Omzet Rp900 juta per hari"), ISI_PROPOSAL
    )
    assert hasil.red_flags == []


def test_rf3_dropping_hallucinated_critical_red_flag_changes_verdict():
    """Konsekuensi yang harus disadari: proposal tidak jadi ditolak
    karena kutipan yang mendasarinya ternyata karangan."""
    from app.domain.verdict import Verdict, decide_verdict

    kotor = skor_dengan("Omzet Rp900 juta per hari")
    assert decide_verdict(kotor, 60) is Verdict.REJECTED
    bersih = drop_hallucinated_evidence(kotor, ISI_PROPOSAL)
    assert decide_verdict(bersih, 60) is Verdict.LISTED


def test_rf3_comparison_ignores_whitespace_and_case_differences():
    hasil = drop_hallucinated_evidence(
        skor_dengan("OMZET   RATA-RATA  rp12 JUTA"), ISI_PROPOSAL
    )
    assert len(hasil.red_flags) == 1


def test_rf3_comparison_rejects_paraphrasing():
    """Beda spasi dan huruf besar diabaikan, tapi parafrase tetap dibuang:
    'omzet bulanan dua belas juta' bukan kutipan persis dari isi proposal."""
    hasil = drop_hallucinated_evidence(
        skor_dengan("omzet bulanan dua belas juta"), ISI_PROPOSAL
    )
    assert hasil.red_flags == []


def test_gemini_engine_refuses_to_build_without_api_key():
    """GeminiEngine.from_settings menolak membangun client, bukan gagal
    samar saat score() baru dipanggil belakangan."""
    tanpa_kunci = settings.model_copy(update={"gemini_api_key": None})
    assert isinstance(tanpa_kunci, Settings)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        GeminiEngine.from_settings(tanpa_kunci)


class _StubCompletions:
    """Pengganti instructor.AsyncInstructor.chat.completions, tanpa jaringan
    (C-28). Mencatat messages yang dikirim supaya test bisa memeriksa prompt
    yang sungguh dirakit _assemble_content(), bukan cuma bahwa score() mengembalikan
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
    (C-25: hanya field yang dibaca MockScoringEngine). GeminiEngine._assemble_content
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


def _bangun_engine_dengan_stub(
    stub: _StubClient, max_prompt_chars: int = 100_000, daily_budget: int = 1_000
) -> GeminiEngine:
    # __new__, bukan GeminiEngine(client, model, timeout_s): __init__
    # membungkus client lewat instructor.from_genai(client, use_async=True),
    # yang menolak objek selain genai.Client sungguhan. Stub ini menggantikan
    # _client secara langsung, menjaga score() dan _assemble_content() tetap
    # kode sungguhan yang diuji, tanpa menyentuh jaringan maupun instructor.
    engine = GeminiEngine.__new__(GeminiEngine)
    engine._client = stub
    engine.model = "gemini-2.5-flash"
    engine._timeout_s = 20
    # Default longgar sengaja: test yang tidak menguji batas prompt/kuota
    # (review keamanan Finding 2) tidak boleh ikut tersandung olehnya.
    engine._max_prompt_chars = max_prompt_chars
    engine._budget = _DailyBudget(daily_budget)
    return engine


async def test_score_calls_stub_and_drops_hallucinated_evidence(
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


async def test_rf2_score_rejects_a_prompt_larger_than_the_configured_cap(
    proposal_draft, campaign_gemini_draft
):
    """Review keamanan Finding 2: batas prompt ditegakkan SEBELUM panggilan
    jaringan terjadi, bukan sesudahnya. stub tidak pernah terpanggil kalau
    ini benar."""
    stub = _StubClient(skor_dengan("evidence apa pun"))
    engine = _bangun_engine_dengan_stub(stub, max_prompt_chars=10)

    with pytest.raises(PromptTooLarge):
        await engine.score(proposal_draft, campaign_gemini_draft)

    assert stub.chat.completions.messages_terkirim is None, (
        "panggilan model tidak boleh terjadi saat prompt melebihi batas"
    )


async def test_rf2_score_is_rejected_once_the_daily_budget_is_exhausted(
    proposal_draft, campaign_gemini_draft
):
    """Kuota harian gagal tertutup: panggilan ke-(limit+1) harus ditolak
    tanpa pernah menyentuh stub/jaringan, bukan diam-diam lolos."""
    stub = _StubClient(skor_dengan("evidence apa pun"))
    engine = _bangun_engine_dengan_stub(stub, daily_budget=2)

    await engine.score(proposal_draft, campaign_gemini_draft)
    await engine.score(proposal_draft, campaign_gemini_draft)
    with pytest.raises(DailyQuotaExceeded):
        await engine.score(proposal_draft, campaign_gemini_draft)


def test_rf2_daily_budget_resets_on_a_new_day():
    hari_1 = [date(2026, 11, 9)]
    anggaran = _DailyBudget(limit=1)
    anggaran._date = hari_1[0]
    anggaran._used = 1

    class _JamBesok:
        def now(self):
            return datetime(2026, 11, 10, tzinfo=UTC)

    import app.ai.gemini_engine as modul_gemini

    asli = modul_gemini._clock
    modul_gemini._clock = _JamBesok()
    try:
        anggaran.use()  # tidak melempar: hari baru, hitungan direset
    finally:
        modul_gemini._clock = asli

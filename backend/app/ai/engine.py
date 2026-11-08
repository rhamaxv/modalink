"""Protocol ScoringEngine dan pemilihannya dari konfigurasi (D-07, D-08).

Import mock_engine dan gemini_engine dilakukan di dalam build_engine, bukan
di level modul: engine_gemini.py akan mengimpor ScoringEngine dari sini untuk
anotasi tipe, dan import di level modul pada kedua arah akan jadi lingkaran.
"""

from typing import Protocol

from app.ai.models import ProposalScore
from app.config import Settings


class ProposalLike(Protocol):
    """Field proposal yang sungguh dibaca engine skoring (C-25).

    Protocol sempit ini menggantikan Any pada parameter proposal/campaign di
    ScoringEngine.score. Alasannya bukan hipotetis: batch sebelumnya menulis
    MockScoringEngine membaca proposal.sector, field yang tidak ada di model
    Proposal sungguhan, dan Any membuat mypy tidak melihatnya. Protocol ini
    hanya menyebut field yang benar-benar dipakai salah satu engine, supaya
    nama field yang salah tertangkap saat type-check, bukan saat runtime.
    """

    business_name: str
    business_profile: str
    fund_usage_plan: str
    business_projection: str
    requested_amount: int


class CampaignLike(Protocol):
    """Field campaign yang sungguh dibaca engine skoring (C-25).

    title ikut disebut meski MockScoringEngine tidak membacanya: prompt
    GeminiEngine menyertakan judul campaign, dan Protocol yang tidak
    menyebutnya akan gagal menangkap kesalahan di jalur itu.
    """

    title: str
    sector: str
    target_amount: int
    description: str


class ScoringEngine(Protocol):
    name: str
    model: str

    async def score(
        self, proposal: ProposalLike, campaign: CampaignLike
    ) -> ProposalScore: ...


def build_engine(settings: Settings) -> ScoringEngine:
    if settings.scoring_engine == "mock":
        from app.ai.mock_engine import MockScoringEngine

        return MockScoringEngine()
    if settings.scoring_engine == "gemini":
        from app.ai.gemini_engine import GeminiEngine

        return GeminiEngine.from_settings(settings)
    raise NotImplementedError(
        f"scoring engine '{settings.scoring_engine}' belum didukung."
    )

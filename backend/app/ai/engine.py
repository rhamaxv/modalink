"""Protocol ScoringEngine dan pemilihannya dari konfigurasi (D-07, D-08).

Import mock_engine dan gemini_engine dilakukan di dalam build_engine, bukan
di level modul: engine_gemini.py akan mengimpor ScoringEngine dari sini untuk
anotasi tipe, dan import di level modul pada kedua arah akan jadi lingkaran.
"""

from typing import Any, Protocol

from app.ai.models import ProposalScore
from app.config import Settings


class ScoringEngine(Protocol):
    name: str
    model: str

    async def score(self, proposal: Any, campaign: Any) -> ProposalScore: ...


def build_engine(settings: Settings) -> ScoringEngine:
    if settings.scoring_engine == "mock":
        from app.ai.mock_engine import MockScoringEngine

        return MockScoringEngine()
    # GeminiEngine menyusul di batch berikutnya (D-07); sampai saat itu,
    # nilai apa pun selain "mock" dianggap belum didukung alih-alih diam-diam
    # jatuh balik ke mock.
    raise NotImplementedError(
        f"scoring engine '{settings.scoring_engine}' belum didukung."
    )

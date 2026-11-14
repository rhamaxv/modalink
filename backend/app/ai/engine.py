"""Protocol ScoringEngine dan pemilihannya dari konfigurasi (D-07, D-08).

Import mock_engine dan gemini_engine dilakukan di dalam build_engine, bukan
di level modul: engine_gemini.py akan mengimpor ScoringEngine dari sini untuk
anotasi tipe, dan import di level modul pada kedua arah akan jadi lingkaran.
"""

from collections.abc import Sequence
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

    Daftarnya pendek sekarang karena uraian proposal sudah pindah ke PDF
    (DocumentLike di bawah); yang tersisa di sini hanya yang diketik UMKM
    sebagai metadata.
    """

    business_name: str
    business_summary: str
    requested_amount: int


class MilestoneLike(Protocol):
    """Satu tahap pencairan, apa adanya dari rencana yang didaftarkan pengaju.

    Ikut dikirim ke model supaya ia bisa membandingkan rencana tahapan
    terhadap isi dokumen: rencana yang nominalnya tidak muncul di mana pun
    pada dokumen adalah justru pola yang red flag `angka_tidak_konsisten`
    cari, dan tanpa daftar ini model tidak punya sisi kedua untuk
    dibandingkan.
    """

    seq: int
    title: str
    amount: int


class DocumentLike(Protocol):
    """Dokumen proposal yang dibaca engine skoring.

    `data` adalah byte PDF-nya, dikirim apa adanya ke model yang membacanya
    secara native. `extracted_text` TIDAK dikirim ke model; ia dipakai
    memeriksa bahwa kutipan pada red flag sungguh ada di dokumen. Lihat
    app/models/proposal_document.py untuk alasan keduanya hidup berdampingan.
    """

    data: bytes
    extracted_text: str


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
        self,
        proposal: ProposalLike,
        campaign: CampaignLike,
        document: DocumentLike,
        milestones: Sequence[MilestoneLike],
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

"""Engine skoring sungguhan lewat Gemini (D-07, D-08). Satu-satunya modul di
proyek ini yang boleh memanggil jaringan untuk menilai proposal.

RF-3 ditegakkan di sini: evidence yang tidak ada di isi proposal adalah
kutipan halusinasi, dan buang_evidence_halusinasi() membuangnya sebelum hasil
dipakai, supaya tidak pernah ditampilkan ke UMKM sebagai alasan penolakan.
"""

import re
from pathlib import Path
from typing import Self

import instructor
from google import genai
from google.genai import types

from app.ai.engine import CampaignLike, ProposalLike
from app.ai.models import ProposalScore
from app.config import Settings

PROMPT = (Path(__file__).parent / "prompts" / "score_proposal.md").read_text()


def _normalkan(teks: str) -> str:
    return re.sub(r"\s+", " ", teks).strip().casefold()


def buang_evidence_halusinasi(score: ProposalScore, isi_proposal: str) -> ProposalScore:
    """Red flag dengan kutipan yang tidak ada di proposal dibuang (RF-3).

    Kutipan karangan yang ditampilkan ke UMKM sebagai alasan penolakan lebih
    merusak daripada red flag yang terlewat, jadi yang ragu dibuang. Ini bisa
    berarti red flag kritis ikut terbuang dan verdict berubah dari rejected
    jadi listed; itu konsekuensi yang disengaja, bukan efek samping.
    """
    sumber = _normalkan(isi_proposal)
    bersih = [f for f in score.red_flags if _normalkan(f.evidence) in sumber]
    return score.model_copy(update={"red_flags": bersih})


class GeminiEngine:
    name = "gemini"

    def __init__(self, client: genai.Client, model: str, timeout_s: int) -> None:
        # use_async=True wajib: score() di bawah memakai await, dan tanpa ini
        # instructor.from_genai mengembalikan client sinkron (Instructor,
        # bukan AsyncInstructor) yang create()-nya bukan coroutine sama
        # sekali, jadi await di baris itu akan gagal pada setiap pemanggilan,
        # bukan hanya saat timeout.
        self._client = instructor.from_genai(client, use_async=True)
        self.model = model
        # Disimpan tapi sudah mati: timeout sekarang diterapkan lewat
        # http_options client (lihat from_settings), bukan per-panggilan.
        self._timeout_s = timeout_s

    @classmethod
    def from_settings(cls, settings: Settings) -> Self:
        """Menolak membangun engine tanpa kunci API, bukan gagal samar saat
        score() baru dipanggil belakangan dengan error autentikasi yang
        tidak jelas asalnya."""
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY tidak diset; scoring engine 'gemini' butuh "
                "kunci ini untuk dibuat."
            )
        # Timeout diterapkan lewat http_options milik client, bukan lewat
        # kwarg timeout= pada panggilan create(): generate_content() di
        # google-genai hanya menerima model/contents/config, dan kwarg
        # timeout= yang diteruskan Instructor berakhir sebagai argumen tak
        # dikenal yang dilempar balik sebagai TypeError pada tiap
        # pemanggilan. http_options di level client sudah diverifikasi
        # memangkas panggilan yang menggantung sesuai batas yang diminta.
        # api_version="v1beta" wajib, bukan preferensi: Instructor meminta
        # structured output lewat function calling, dan endpoint v1 menolaknya
        # dengan 400 INVALID_ARGUMENT "Function calling is not enabled for api
        # version v1". Kegagalannya hanya muncul dengan kunci sungguhan, jadi
        # seluruh test bermock tetap hijau tanpa baris ini.
        client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                api_version="v1beta",
                timeout=settings.gemini_timeout_s * 1000,
            ),
        )
        return cls(
            client=client,
            model=settings.gemini_model,
            timeout_s=settings.gemini_timeout_s,
        )

    async def score(
        self, proposal: ProposalLike, campaign: CampaignLike
    ) -> ProposalScore:
        isi = self._rakit_isi(proposal, campaign)
        hasil = await self._client.chat.completions.create(
            model=self.model,
            response_model=ProposalScore,
            # Instructor mengirim ulang saat validasi gagal; digabung timeout
            # di level client, worst case satu pemanggilan score() bisa
            # menggantung sampai hampir 3x gemini_timeout_s sebelum menyerah.
            max_retries=2,
            messages=[{"role": "user", "content": PROMPT.format(**isi)}],
        )
        return buang_evidence_halusinasi(hasil, isi["isi_proposal"])

    def _rakit_isi(
        self, proposal: ProposalLike, campaign: CampaignLike
    ) -> dict[str, str]:
        isi_proposal = (
            f"{proposal.business_profile} {proposal.fund_usage_plan} "
            f"{proposal.business_projection}"
        )
        return {
            "judul_campaign": campaign.title,
            "sektor_campaign": campaign.sector,
            "deskripsi_campaign": campaign.description,
            "target_amount_campaign": str(campaign.target_amount),
            "business_name": proposal.business_name,
            "business_profile": proposal.business_profile,
            "requested_amount": str(proposal.requested_amount),
            "fund_usage_plan": proposal.fund_usage_plan,
            "business_projection": proposal.business_projection,
            "isi_proposal": isi_proposal,
        }

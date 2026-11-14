"""Engine skoring sungguhan lewat Gemini (D-07, D-08). Satu-satunya modul di
proyek ini yang boleh memanggil jaringan untuk menilai proposal.

RF-3 ditegakkan di sini: evidence yang tidak ada di isi proposal adalah
kutipan halusinasi, dan drop_hallucinated_evidence() membuangnya sebelum hasil
dipakai, supaya tidak pernah ditampilkan ke UMKM sebagai alasan penolakan.

Isi proposal sekarang adalah PDF, dikirim apa adanya lewat instructor PDF
(`PDF.from_raw_base64`) dan dibaca Gemini secara native -- tidak ada langkah
OCR terpisah, termasuk untuk dokumen hasil pindai. Yang dicocokkan
drop_hallucinated_evidence bukan PDF itu melainkan `extracted_text` miliknya,
dan untuk dokumen pindai teks itu kosong sehingga seluruh red flag terbuang.
Arah kegagalannya disengaja; lihat app/models/proposal_document.py.
"""

import base64
import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any, Self, cast

import instructor
from google import genai
from google.genai import types
from instructor.v2.core.multimodal import PDF

from app.ai.engine import CampaignLike, DocumentLike, MilestoneLike, ProposalLike
from app.ai.models import ProposalScore
from app.config import Settings
from app.domain.clock import SystemClock

PROMPT = (Path(__file__).parent / "prompts" / "score_proposal.md").read_text()

# SystemClock(), bukan datetime.now() langsung: BR-60 (app/domain/clock.py)
# melarang itu di luar domain/clock.py sendiri. Modul ini bukan services/
# atau domain/ sehingga pagar AST test_domain_murni.py tidak memeriksanya,
# tapi aturannya tetap berlaku -- pola yang sama dengan `_clock = SystemClock()`
# di app/services/auth.py untuk kedaluwarsa JWT.
_clock = SystemClock()


class PromptTooLarge(ValueError):
    """Isi proposal yang dirakit melebihi batas prompt (review keamanan
    Finding 2). ValueError, bukan DomainError: modul ini tidak pernah
    tersentuh app/api/, dan run_scoring (services/scoring.py) sudah
    menangkap *semua* Exception dari engine.score dan menjadikannya
    scoring_status=failed (D-09) -- tidak ada penanganan khusus yang perlu
    ditambahkan di sana untuk kelas ini."""


class DailyQuotaExceeded(RuntimeError):
    """Kuota harian panggilan Gemini (lihat _DailyBudget) sudah tercapai."""


class _DailyBudget:
    """Kuota harian kasar untuk seluruh panggilan `GeminiEngine.score`,
    dibagi proses -- review keamanan Finding 2 menilai banjir registrasi
    tanpa captcha/limit sebagai risiko tertinggi ke kuota Gemini selama
    judging. Rate limit per-IP/akun (app/middleware.py) dan batas konkurensi
    (app/jobs/inline.py) sama-sama menahan SEBERAPA CEPAT job baru dibuat;
    counter ini adalah lapisan terakhir yang menahan TOTAL per hari, apa pun
    kombinasi IP dan akun yang dipakai untuk mencapainya.

    Di memori proses, bukan database: sama alasannya dengan
    InMemoryRateLimiter (D-01, satu container, tidak ada Redis). Reset saat
    proses restart adalah kelemahan yang disadari, diterima karena lebih
    baik daripada tidak ada batas harian sama sekali, dan direstart di
    tengah jam sibuk judging adalah risiko yang jauh lebih kecil daripada
    kuota terbakar oleh crawler.

    Gagal tertutup: `use()` melempar, bukan diam-diam meloloskan, begitu
    kuota tercapai.
    """

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._date: date | None = None
        self._used = 0

    def use(self) -> None:
        hari_ini = _clock.now().date()
        if self._date != hari_ini:
            self._date = hari_ini
            self._used = 0
        if self._used >= self._limit:
            raise DailyQuotaExceeded(
                f"Kuota harian panggilan Gemini ({self._limit}) sudah tercapai."
            )
        self._used += 1


def _normalize(teks: str) -> str:
    return re.sub(r"\s+", " ", teks).strip().casefold()


def _format_milestone(milestones: Sequence[MilestoneLike]) -> str:
    """Rencana tahapan sebagai daftar baris, diurutkan sesuai `seq`.

    Diurutkan di sini dan tidak dipercayakan pada urutan baris dari
    database: model diminta memeriksa konsistensi nominal antar-tahap, dan
    tahap yang tiba dengan urutan acak membuat pemeriksaan itu menilai
    rencana yang bukan rencana pengaju.
    """
    if not milestones:
        return "(tidak ada tahap yang didaftarkan)"
    return "\n".join(
        f"  {m.seq}. {m.title} — {m.amount}"
        for m in sorted(milestones, key=lambda m: m.seq)
    )


def drop_hallucinated_evidence(
    score: ProposalScore, isi_proposal: str
) -> ProposalScore:
    """Red flag dengan kutipan yang tidak ada di proposal dibuang (RF-3).

    Kutipan karangan yang ditampilkan ke UMKM sebagai alasan penolakan lebih
    merusak daripada red flag yang terlewat, jadi yang ragu dibuang. Ini bisa
    berarti red flag kritis ikut terbuang dan verdict berubah dari rejected
    jadi listed; itu konsekuensi yang disengaja, bukan efek samping.
    """
    sumber = _normalize(isi_proposal)
    # `kutipan and` wajib ada di depan, dan bukan detail gaya: tanpa itu red
    # flag dengan evidence kosong lolos selalu, karena "" adalah substring
    # dari string apa pun termasuk sumber yang juga kosong. Lubang ini sudah
    # ada sejak RF-3 ditulis, tapi baru bisa dipicu sekarang: dokumen hasil
    # pindai tidak punya lapisan teks, sumbernya kosong, dan satu-satunya
    # kutipan yang bisa "cocok" adalah kutipan yang tidak mengutip apa pun --
    # persis alasan tuduhan tanpa bukti yang pagar ini ada untuk mencegah.
    bersih = [
        f
        for f in score.red_flags
        if (kutipan := _normalize(f.evidence)) and kutipan in sumber
    ]
    return score.model_copy(update={"red_flags": bersih})


class GeminiEngine:
    name = "gemini"

    def __init__(
        self,
        client: genai.Client,
        model: str,
        timeout_s: int,
        max_prompt_chars: int,
        daily_budget: int,
    ) -> None:
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
        self._max_prompt_chars = max_prompt_chars
        # Satu _DailyBudget per instance, bukan per panggilan: build_engine
        # (app/ai/engine.py) hanya membangun satu GeminiEngine untuk seluruh
        # proses (app/api/deps.py:_scoring_engine), jadi ini sudah otomatis
        # dibagi seluruh request, sama seperti _SCORING_SEMAPHORE di
        # app/jobs/inline.py.
        self._budget = _DailyBudget(daily_budget)

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
            max_prompt_chars=settings.gemini_max_prompt_chars,
            daily_budget=settings.gemini_daily_budget,
        )

    async def score(
        self,
        proposal: ProposalLike,
        campaign: CampaignLike,
        document: DocumentLike,
        milestones: Sequence[MilestoneLike],
    ) -> ProposalScore:
        isi = self._assemble_content(proposal, campaign, milestones)
        panjang_prompt = len(PROMPT.format(**isi))
        if panjang_prompt > self._max_prompt_chars:
            # Review keamanan Finding 2: proposal bisa diterima apa adanya
            # (batas panjang per-field ada di app/schemas/proposal.py, bukan
            # berkas ini), tapi panggilan ke MODEL tetap harus punya batas
            # keras sendiri sebelum network call benar-benar terjadi --
            # batas skema melindungi satu kolom, bukan gabungan ketiganya
            # yang sungguh dikirim. ValueError, bukan diam-diam dipotong:
            # memotong isi proposal diam-diam membuat model menilai teks
            # yang sudah terpenggal tanpa UMKM tahu bagian mana yang hilang.
            raise PromptTooLarge(
                f"Prompt {panjang_prompt} karakter melebihi batas "
                f"{self._max_prompt_chars}."
            )
        self._budget.use()
        hasil = await self._client.chat.completions.create(
            model=self.model,
            response_model=ProposalScore,
            # Instructor mengirim ulang saat validasi gagal; digabung timeout
            # di level client, worst case satu pemanggilan score() bisa
            # menggantung sampai hampir 3x gemini_timeout_s sebelum menyerah.
            max_retries=2,
            # Daftar [teks, PDF], bukan satu string: inilah satu-satunya
            # bentuk yang diterima provider gemini milik Instructor. Part
            # mentah dari google-genai maupun dict gaya OpenAI sama-sama
            # ditolak dengan "Unsupported content item type" -- isi daftarnya
            # harus str atau instance Image/Audio/PDF miliknya sendiri.
            # cast, dan alasannya ada di pustakanya, bukan di kode ini:
            # tipe `messages` milik Instructor disalin dari OpenAI, yang
            # `content`-nya hanya string atau potongan teks/gambar. Daftar
            # berisi instance PDF adalah bentuk yang provider gemini-nya
            # sendiri tuntut (instructor/v2/providers/gemini/utils.py), jadi
            # anotasinya yang tidak menyusul, bukan pemanggilan ini yang
            # salah.
            messages=cast(
                list[Any],
                [
                    {
                        "role": "user",
                        "content": [
                            PROMPT.format(**isi),
                            PDF.from_raw_base64(
                                base64.b64encode(document.data).decode("ascii")
                            ),
                        ],
                    }
                ],
            ),
        )
        return drop_hallucinated_evidence(hasil, document.extracted_text)

    def _assemble_content(
        self,
        proposal: ProposalLike,
        campaign: CampaignLike,
        milestones: Sequence[MilestoneLike],
    ) -> dict[str, str]:
        return {
            "judul_campaign": campaign.title,
            "sektor_campaign": campaign.sector,
            "deskripsi_campaign": campaign.description,
            "target_amount_campaign": str(campaign.target_amount),
            "business_name": proposal.business_name,
            "business_summary": proposal.business_summary,
            "requested_amount": str(proposal.requested_amount),
            "rencana_milestone": _format_milestone(milestones),
        }

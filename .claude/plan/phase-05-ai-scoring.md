# Fase 05. AI scoring

**Hasil:** proposal yang masuk langsung dinilai dan mendapat brief. Regression test R6 hijau:
kegagalan teknis tidak pernah berarti penolakan.

**Spec terkait:** [11-ai-scoring-spec](../prd/11-ai-scoring-spec.md), [06-feature-ai](../prd/06-feature-ai.md), [D-07, D-08, D-09](../docs/decisions.md)

## Struktur file

```
backend/app/
  ai/
    __init__.py
    models.py            # ProposalScore, RedFlag, Brief (Pydantic)
    engine.py            # protocol ScoringEngine + factory dari settings
    mock_engine.py       # deterministik, dipakai seluruh test
    gemini_engine.py     # Instructor + google-genai
    prompts/score_proposal.md
  domain/verdict.py      # keputusan listed vs rejected, murni
  jobs/runner.py         # protocol JobRunner
  jobs/inline.py         # InlineRunner di atas BackgroundTasks
  services/scoring.py    # orkestrasi: panggil engine, simpan, transisi
backend/tests/
  unit/test_verdict.py
  unit/test_mock_engine.py
  integration/test_scoring_flow.py
  regression/test_r6_ai_failure.py
  contract/test_gemini_scoring.py
```

---

### Task 1: Schema output dan keputusan verdict

**Files:**
- Create: `backend/app/ai/models.py`, `backend/app/domain/verdict.py`
- Test: `backend/tests/unit/test_verdict.py`

**Interfaces:**
- Produces: `ProposalScore`, `RedFlag`, `Brief`, `decide_verdict(score, threshold) -> Verdict`,
  `total_score(score) -> int`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_verdict.py
import pytest
from pydantic import ValidationError
from app.ai.models import Brief, ProposalScore, RedFlag
from app.domain.verdict import Verdict, decide_verdict, total_score

def skor(fit=30, data=20, impact=20, flags=()):
    return ProposalScore(
        fit_score=fit, data_quality_score=data, impact_score=impact,
        red_flags=list(flags),
        brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
    )

def test_br70_total_dijumlahkan_dari_tiga_komponen():
    assert total_score(skor(34, 21, 18)) == 73

def test_br70_field_total_dari_model_dibuang():
    """Model yang mengarang 'total' tidak boleh mempengaruhi apa pun."""
    mentah = {
        "fit_score": 10, "data_quality_score": 10, "impact_score": 10, "total": 99,
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
    s = skor(20, 20, 20)   # total 60
    assert decide_verdict(s, threshold=60) is Verdict.LISTED
    assert decide_verdict(s, threshold=61) is Verdict.REJECTED

def test_br72_red_flag_kritis_menolak_meski_skor_tinggi():
    kritis = RedFlag(code="projeksi_tidak_realistis", severity="critical",
                     message="x", evidence="y")
    assert decide_verdict(skor(40, 30, 30, [kritis]), threshold=60) is Verdict.REJECTED

def test_red_flag_warning_tidak_menolak():
    ringan = RedFlag(code="isian_template", severity="warning", message="x", evidence="y")
    assert decide_verdict(skor(40, 30, 30, [ringan]), threshold=60) is Verdict.LISTED

@pytest.mark.parametrize("field,nilai", [
    ("fit_score", 41), ("data_quality_score", 31), ("impact_score", 31),
    ("fit_score", -1),
])
def test_br78_komponen_di_luar_rentang_ditolak_validator(field, nilai):
    with pytest.raises(ValidationError):
        skor(**{field.replace("_score", ""): nilai} if False else {})  # lihat catatan
```

Test terakhir ditulis eksplisit per field agar jelas, bukan lewat trik `**kwargs`:

```python
def test_br78_fit_score_di_atas_40_ditolak():
    with pytest.raises(ValidationError):
        ProposalScore(fit_score=41, data_quality_score=0, impact_score=0,
                      red_flags=[],
                      brief=Brief(strengths=["a"], risks=["b"], recommendation="c"))
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_verdict.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/ai/models.py
from typing import Literal
from pydantic import BaseModel, Field

class RedFlag(BaseModel):
    code: str
    severity: Literal["info", "warning", "critical"]
    message: str
    evidence: str   # kutipan persis dari isi proposal, bukan parafrase

class Brief(BaseModel):
    strengths: list[str] = Field(min_length=1, max_length=5)
    risks: list[str] = Field(min_length=1, max_length=5)
    recommendation: str

class ProposalScore(BaseModel):
    """Tidak ada field 'total' di sini, dan itu disengaja (BR-70).

    Model hanya menilai komponen. Total dan verdict diputuskan oleh kode.
    Field tambahan apa pun yang dikembalikan model akan diabaikan Pydantic.
    """
    fit_score: int = Field(ge=0, le=40)
    data_quality_score: int = Field(ge=0, le=30)
    impact_score: int = Field(ge=0, le=30)
    red_flags: list[RedFlag] = Field(default_factory=list, max_length=8)
    brief: Brief
```

```python
# backend/app/domain/verdict.py
from enum import StrEnum
from app.ai.models import ProposalScore

class Verdict(StrEnum):
    LISTED = "listed"
    REJECTED = "rejected"

def total_score(score: ProposalScore) -> int:
    return score.fit_score + score.data_quality_score + score.impact_score

def decide_verdict(score: ProposalScore, threshold: int) -> Verdict:
    # Urutan penting: red flag kritis menolak tanpa memandang total (BR-72).
    if any(f.severity == "critical" for f in score.red_flags):
        return Verdict.REJECTED
    if total_score(score) < threshold:
        return Verdict.REJECTED
    return Verdict.LISTED
```

`domain/verdict.py` mengimpor `ai/models.py`, dan itu tidak melanggar pagar arsitektur karena
`ai/models.py` hanya berisi Pydantic, tanpa database dan tanpa jaringan.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_verdict.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add scoring schema and code-side verdict decision"
```

---

### Task 2: MockScoringEngine

**Files:**
- Create: `backend/app/ai/engine.py`, `backend/app/ai/mock_engine.py`
- Test: `backend/tests/unit/test_mock_engine.py`

**Interfaces:**
- Produces: protocol `ScoringEngine` dengan `async score(proposal, campaign) -> ProposalScore`,
  `MockScoringEngine`, `build_engine(settings) -> ScoringEngine`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_mock_engine.py
from app.ai.mock_engine import MockScoringEngine
from app.domain.verdict import total_score

async def test_mock_deterministik(proposal_draft, campaign_draft):
    engine = MockScoringEngine()
    a = await engine.score(proposal_draft, campaign_draft)
    b = await engine.score(proposal_draft, campaign_draft)
    assert a == b

async def test_penanda_score_memaksa_total(proposal_draft, campaign_draft):
    proposal_draft.business_profile += " [[SCORE:59]]"
    skor = await MockScoringEngine().score(proposal_draft, campaign_draft)
    assert total_score(skor) == 59

async def test_penanda_red_flag_menghasilkan_flag_kritis(proposal_draft, campaign_draft):
    proposal_draft.business_projection += " [[RED_FLAG:critical]]"
    skor = await MockScoringEngine().score(proposal_draft, campaign_draft)
    assert any(f.severity == "critical" for f in skor.red_flags)

async def test_proposal_lengkap_dapat_skor_lebih_tinggi_dari_yang_tipis(
    proposal_draft, proposal_draft_tipis, campaign_draft
):
    engine = MockScoringEngine()
    lengkap = total_score(await engine.score(proposal_draft, campaign_draft))
    tipis = total_score(await engine.score(proposal_draft_tipis, campaign_draft))
    assert lengkap > tipis
```

Test terakhir menjaga mock tetap masuk akal. Mock yang memberi skor acak membuat seluruh
integration test kehilangan arti.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_mock_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/ai/mock_engine.py
"""Engine deterministik untuk seluruh test dan untuk demo tanpa jaringan (D-07).

Penanda [[SCORE:n]] dan [[RED_FLAG:level]] hanya dikenali di sini,
tidak pernah dikirim ke Gemini.
"""
import re
from app.ai.models import Brief, ProposalScore, RedFlag

PENANDA_SKOR = re.compile(r"\[\[SCORE:(\d+)\]\]")
PENANDA_FLAG = re.compile(r"\[\[RED_FLAG:(info|warning|critical)\]\]")

class MockScoringEngine:
    name = "mock"
    model = "mock-v1"

    async def score(self, proposal, campaign) -> ProposalScore:
        teks = " ".join([proposal.business_profile, proposal.fund_usage_plan,
                         proposal.business_projection])

        flags = [
            RedFlag(code="penanda_uji", severity=level, message="Dipicu penanda uji.",
                    evidence=f"[[RED_FLAG:{level}]]")
            for level in PENANDA_FLAG.findall(teks)
        ]

        if (paksa := PENANDA_SKOR.search(teks)):
            total = min(int(paksa.group(1)), 100)
            fit = min(total, 40)
            data = min(total - fit, 30)
            return ProposalScore(fit_score=fit, data_quality_score=data,
                                 impact_score=total - fit - data,
                                 red_flags=flags, brief=self._brief(proposal))

        # Skor dasar dari kelengkapan isian, dibatasi rentangnya.
        # Kecocokan diukur dari proporsi dana yang diminta terhadap target campaign,
        # bukan dari sektor: `Proposal` tidak punya kolom sector, hanya `Campaign`
        # yang punya, sehingga membandingkan keduanya akan melempar AttributeError
        # begitu baris Proposal sungguhan masuk.
        porsi = proposal.requested_amount / campaign.target_amount
        fit = 40 if porsi <= 0.5 else (30 if porsi <= 0.8 else 22)
        data = min(len(proposal.fund_usage_plan) // 10, 30)
        impact = min(len(proposal.business_projection) // 10, 30)
        return ProposalScore(fit_score=fit, data_quality_score=data, impact_score=impact,
                             red_flags=flags, brief=self._brief(proposal))

    def _brief(self, proposal) -> Brief:
        return Brief(
            strengths=[f"Profil usaha {proposal.business_name} terisi."],
            risks=["Penilaian ini berasal dari engine tiruan, bukan dari model AI."],
            recommendation="Gunakan hanya untuk pengujian.",
        )
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_mock_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add deterministic mock scoring engine"
```

---

### Task 3: GeminiEngine dengan Instructor

**Files:**
- Create: `backend/app/ai/gemini_engine.py`, `backend/app/ai/prompts/score_proposal.md`
- Test: `backend/tests/unit/test_gemini_engine.py` (dengan klien palsu), `backend/tests/contract/test_gemini_scoring.py`

**Interfaces:**
- Produces: `GeminiEngine(client, model, timeout_s)`.

Ini tempat **RF-3** ditegakkan: `evidence` yang tidak ada di isi proposal adalah kutipan
halusinasi, dan tidak boleh ditampilkan ke UMKM sebagai bukti penolakan.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_gemini_engine.py
import pytest
from app.ai.gemini_engine import GeminiEngine, buang_evidence_halusinasi
from app.ai.models import Brief, ProposalScore, RedFlag

def skor_dengan(evidence: str) -> ProposalScore:
    return ProposalScore(
        fit_score=30, data_quality_score=20, impact_score=20,
        red_flags=[RedFlag(code="angka_tidak_konsisten", severity="critical",
                           message="x", evidence=evidence)],
        brief=Brief(strengths=["a"], risks=["b"], recommendation="c"),
    )

ISI_PROPOSAL = "Omzet rata-rata Rp12 juta per bulan dengan dua pekerja."

def test_rf3_evidence_yang_ada_di_proposal_dipertahankan():
    hasil = buang_evidence_halusinasi(skor_dengan("Omzet rata-rata Rp12 juta"), ISI_PROPOSAL)
    assert len(hasil.red_flags) == 1

def test_rf3_evidence_yang_tidak_ada_di_proposal_dibuang():
    hasil = buang_evidence_halusinasi(skor_dengan("Omzet Rp900 juta per hari"), ISI_PROPOSAL)
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
    hasil = buang_evidence_halusinasi(skor_dengan("OMZET   RATA-RATA  rp12 JUTA"), ISI_PROPOSAL)
    assert len(hasil.red_flags) == 1
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_gemini_engine.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/ai/gemini_engine.py
import re
from pathlib import Path
import instructor
from app.ai.models import ProposalScore

PROMPT = (Path(__file__).parent / "prompts" / "score_proposal.md").read_text()

def _normalkan(teks: str) -> str:
    return re.sub(r"\s+", " ", teks).strip().casefold()

def buang_evidence_halusinasi(score: ProposalScore, isi_proposal: str) -> ProposalScore:
    """Red flag dengan kutipan yang tidak ada di proposal dibuang (RF-3).

    Kutipan karangan yang ditampilkan ke UMKM sebagai alasan penolakan lebih merusak
    daripada red flag yang terlewat, jadi yang ragu dibuang.
    """
    sumber = _normalkan(isi_proposal)
    bersih = [f for f in score.red_flags if _normalkan(f.evidence) in sumber]
    return score.model_copy(update={"red_flags": bersih})

class GeminiEngine:
    name = "gemini"

    def __init__(self, client, model: str, timeout_s: int) -> None:
        self._client = instructor.from_genai(client)
        self.model = model
        self._timeout_s = timeout_s

    async def score(self, proposal, campaign) -> ProposalScore:
        isi = self._rakit_isi(proposal, campaign)
        hasil = await self._client.chat.completions.create(
            model=self.model,
            response_model=ProposalScore,
            max_retries=2,          # Instructor mengirim ulang saat validasi gagal
            timeout=self._timeout_s,
            messages=[{"role": "user", "content": PROMPT.format(**isi)}],
        )
        return buang_evidence_halusinasi(hasil, isi["isi_proposal"])
```

Prompt **tidak** memuat `score_threshold`, supaya penilaian model tidak condong menyesuaikan
ambang ([11-ai-scoring-spec](../prd/11-ai-scoring-spec.md)).

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_gemini_engine.py -v`
Expected: PASS

- [ ] **Step 5: Tulis contract test bertanda live**

```python
# backend/tests/contract/test_gemini_scoring.py
import pytest
from app.domain.verdict import total_score

pytestmark = pytest.mark.live

async def test_live_output_lolos_validasi(gemini_engine, proposal_bagus, campaign_draft):
    skor = await gemini_engine.score(proposal_bagus, campaign_draft)
    assert 0 <= total_score(skor) <= 100

async def test_live_urutan_skor_masuk_akal(
    gemini_engine, proposal_bagus, proposal_biasa, proposal_red_flag, campaign_draft
):
    bagus = total_score(await gemini_engine.score(proposal_bagus, campaign_draft))
    biasa = total_score(await gemini_engine.score(proposal_biasa, campaign_draft))
    buruk = total_score(await gemini_engine.score(proposal_red_flag, campaign_draft))
    assert bagus > biasa > buruk

async def test_live_proyeksi_berlebihan_memicu_red_flag_kritis(
    gemini_engine, proposal_red_flag, campaign_draft
):
    skor = await gemini_engine.score(proposal_red_flag, campaign_draft)
    assert any(f.severity == "critical" for f in skor.red_flags)

async def test_live_setiap_evidence_benar_benar_ada_di_proposal(
    gemini_engine, proposal_red_flag, campaign_draft
):
    """Paling sering jebol saat prompt diubah, dan paling berguna."""
    skor = await gemini_engine.score(proposal_red_flag, campaign_draft)
    isi = " ".join([proposal_red_flag.business_profile,
                    proposal_red_flag.fund_usage_plan,
                    proposal_red_flag.business_projection]).casefold()
    for f in skor.red_flags:
        assert f.evidence.casefold() in isi, f"kutipan karangan: {f.evidence!r}"
```

Run: `make test-live` (butuh `GEMINI_API_KEY`)
Expected: PASS. Kalau gagal, perbaiki prompt, bukan testnya.

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: integrate Gemini API for proposal scoring via Instructor"
```

---

### Task 4: JobRunner dan orkestrasi scoring

**Files:**
- Create: `backend/app/jobs/runner.py`, `backend/app/jobs/inline.py`, `backend/app/services/scoring.py`
- Test: `backend/tests/integration/test_scoring_flow.py`

**Interfaces:**
- Produces: protocol `JobRunner.submit(coro_factory)`, `InlineRunner`,
  `jalankan_scoring(session, proposal_id, engine, clock) -> None`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_scoring_flow.py
async def test_proposal_masuk_langsung_dapat_skor(client, umkm, campaign, body_proposal):
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
                            headers=umkm.headers, json=body_proposal())
    pid = res.json()["id"]
    detail = (await client.get(f"/api/v1/proposals/{pid}", headers=umkm.headers)).json()
    assert detail["scoring_status"] == "done"
    assert detail["status"] == "listed"

async def test_br73_skor_di_bawah_threshold_jadi_rejected(
    client, umkm, campaign, body_proposal
):
    body = body_proposal()
    body["business_profile"] += " [[SCORE:40]]"      # threshold campaign 60
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
                            headers=umkm.headers, json=body)
    pid = res.json()["id"]
    detail = (await client.get(f"/api/v1/proposals/{pid}", headers=umkm.headers)).json()
    assert detail["status"] == "rejected"

async def test_br76_rescore_menambah_baris_bukan_menimpa(
    client, db, umkm, proposal_scoring_gagal
):
    await client.post(f"/api/v1/proposals/{proposal_scoring_gagal.id}/rescore",
                      headers=umkm.headers)
    jumlah = await db.scalar(
        select(func.count()).select_from(ScoringResult)
        .where(ScoringResult.proposal_id == proposal_scoring_gagal.id))
    assert jumlah >= 1

async def test_br75_job_terpicu_dua_kali_tidak_menghasilkan_dua_transisi(
    db, listed_proposal, engine_mock, clock
):
    from app.services.scoring import jalankan_scoring
    await jalankan_scoring(db, listed_proposal.id, engine_mock, clock)
    await db.refresh(listed_proposal)
    assert listed_proposal.status is ProposalStatus.LISTED   # tidak berubah, tidak error

async def test_t50_t51_scoring_status_berjalan_pending_processing_done(
    db, submitted_proposal, engine_mock, clock
):
    from app.services.scoring import jalankan_scoring
    assert submitted_proposal.scoring_status is ScoringStatus.PENDING
    await jalankan_scoring(db, submitted_proposal.id, engine_mock, clock)
    await db.refresh(submitted_proposal)
    assert submitted_proposal.scoring_status is ScoringStatus.DONE

async def test_t52_scoring_status_jadi_failed_saat_engine_meledak(
    db, submitted_proposal, engine_meledak, clock
):
    from app.services.scoring import jalankan_scoring
    await jalankan_scoring(db, submitted_proposal.id, engine_meledak, clock)
    await db.refresh(submitted_proposal)
    assert submitted_proposal.scoring_status is ScoringStatus.FAILED

async def test_t53_rescore_mengembalikan_scoring_status_ke_pending(
    client, db, umkm, proposal_scoring_gagal
):
    await client.post(f"/api/v1/proposals/{proposal_scoring_gagal.id}/rescore",
                      headers=umkm.headers)
    await db.refresh(proposal_scoring_gagal)
    assert proposal_scoring_gagal.scoring_status in {ScoringStatus.PENDING,
                                                     ScoringStatus.PROCESSING,
                                                     ScoringStatus.DONE}

async def test_br35_komunitas_tidak_bisa_melihat_red_flag(client, community, listed_proposal):
    res = await client.get(f"/api/v1/proposals/{listed_proposal.id}/scoring",
                           headers=community.headers)
    assert res.status_code == 403
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_scoring_flow.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/services/scoring.py
from app.domain.transitions import ProposalEvent, ProposalStatus, ScoringStatus, apply_proposal
from app.domain.verdict import Verdict, decide_verdict, total_score

async def jalankan_scoring(session, proposal_id, engine, clock) -> None:
    proposal = await session.get(Proposal, proposal_id)
    if proposal is None or proposal.status is not ProposalStatus.SUBMITTED:
        return   # compare-and-set: job kedua tidak melakukan apa-apa (BR-75)

    proposal.scoring_status = ScoringStatus.PROCESSING
    await session.flush()

    campaign = await session.get(Campaign, proposal.campaign_id)
    mulai = clock.now()
    try:
        skor = await engine.score(proposal, campaign)
    except Exception:
        # Kegagalan teknis tidak pernah berarti penolakan (D-09, BR-74).
        # Status proposal sengaja tidak disentuh.
        proposal.scoring_status = ScoringStatus.FAILED
        await session.flush()
        return

    verdict = decide_verdict(skor, campaign.score_threshold)
    session.add(ScoringResult(
        proposal_id=proposal.id, engine_name=engine.name, model_name=engine.model,
        fit_score=skor.fit_score, data_quality_score=skor.data_quality_score,
        impact_score=skor.impact_score, total_score=total_score(skor),
        red_flags=[f.model_dump() for f in skor.red_flags],
        brief=skor.brief.model_dump(), threshold_used=campaign.score_threshold,
        verdict=verdict, latency_ms=int((clock.now() - mulai).total_seconds() * 1000),
    ))

    event = (ProposalEvent.SCORING_LULUS if verdict is Verdict.LISTED
             else ProposalEvent.SCORING_GAGAL)
    proposal.status = apply_proposal(proposal.status, event)
    proposal.scoring_status = ScoringStatus.DONE
    await session.flush()
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_scoring_flow.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add scoring orchestration with compare-and-set transition"
```

---

### Task 5: Regression R6

**Files:**
- Create: `backend/tests/regression/test_r6_ai_failure.py`

- [ ] **Step 1: Tulis test**

```python
# backend/tests/regression/test_r6_ai_failure.py
"""R6: tidak ada mode kegagalan AI yang menghasilkan 'rejected' (D-09, BR-74)."""
import asyncio
import pytest
from app.domain.transitions import ProposalStatus, ScoringStatus
from app.services.scoring import jalankan_scoring

class EngineMeledak:
    name, model = "palsu", "palsu"
    def __init__(self, exc): self._exc = exc
    async def score(self, proposal, campaign): raise self._exc

MODE_GAGAL = [
    pytest.param(asyncio.TimeoutError(), id="timeout"),
    pytest.param(ConnectionError("jaringan putus"), id="jaringan"),
    pytest.param(ValueError("output gagal validasi"), id="schema"),
    pytest.param(RuntimeError("GEMINI_API_KEY tidak ada"), id="tanpa-api-key"),
]

@pytest.mark.parametrize("kegagalan", MODE_GAGAL)
async def test_r6_kegagalan_tidak_mengubah_status_proposal(
    db, submitted_proposal, clock, kegagalan
):
    await jalankan_scoring(db, submitted_proposal.id, EngineMeledak(kegagalan), clock)
    await db.refresh(submitted_proposal)

    assert submitted_proposal.scoring_status is ScoringStatus.FAILED
    assert submitted_proposal.status is ProposalStatus.SUBMITTED   # bukan rejected

@pytest.mark.parametrize("kegagalan", MODE_GAGAL)
async def test_r6_kegagalan_tidak_meninggalkan_baris_scoring(
    db, submitted_proposal, clock, kegagalan
):
    await jalankan_scoring(db, submitted_proposal.id, EngineMeledak(kegagalan), clock)
    jumlah = await db.scalar(
        select(func.count()).select_from(ScoringResult)
        .where(ScoringResult.proposal_id == submitted_proposal.id))
    assert jumlah == 0

async def test_r6_rescore_mengembalikan_ke_pending(client, umkm, proposal_scoring_gagal):
    res = await client.post(f"/api/v1/proposals/{proposal_scoring_gagal.id}/rescore",
                            headers=umkm.headers)
    assert res.status_code == 202

async def test_r6_rescore_ditolak_saat_scoring_sudah_selesai(client, umkm, listed_proposal):
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/rescore",
                            headers=umkm.headers)
    assert res.status_code == 409

async def test_r6_job_dua_kali_hanya_satu_transisi(db, submitted_proposal, engine_mock, clock):
    await jalankan_scoring(db, submitted_proposal.id, engine_mock, clock)
    status_pertama = submitted_proposal.status
    await jalankan_scoring(db, submitted_proposal.id, engine_mock, clock)
    await db.refresh(submitted_proposal)
    assert submitted_proposal.status is status_pertama
```

- [ ] **Step 2: Jalankan, pastikan hijau**

Run: `pytest tests/regression -v`
Expected: PASS, R1, R5, R6 semuanya

- [ ] **Step 3: Commit**

```bash
git add backend/tests/regression/test_r6_ai_failure.py
git commit -m "feat: add regression suite ensuring AI failure never rejects a proposal"
```

## Gerbang keluar fase 05

- [ ] `make test` dan `make test-regression` hijau
- [ ] `SCORING_ENGINE=mock` membuat seluruh suite berjalan tanpa jaringan
- [ ] `make test-live` lolos (dijalankan manual sekali, dicatat hasilnya)
- [ ] Tidak ada test di luar `tests/contract/` yang menyentuh jaringan, diperiksa dengan
      menjalankan suite tanpa koneksi internet

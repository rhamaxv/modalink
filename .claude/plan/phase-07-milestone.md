# Fase 07. Milestone dan pencairan

**Hasil:** flow `funded` sampai `completed` berjalan end-to-end. Regression R3 hijau.

**Spec terkait:** [BR-40..BR-48](../prd/07-business-rules.md), [T-20..T-31](../prd/08-state-machines.md), [D-13](../docs/decisions.md)

## Struktur file

```
backend/app/
  models/milestone_report.py
  domain/milestone_rules.py    # prasyarat pelaporan dan pencairan, murni
  services/status.py           # jembatan enum domain <-> enum kolom, satu tempat
  services/milestone.py
  api/v1/milestones.py
backend/tests/
  unit/test_milestone_rules.py
  unit/test_transition_guard.py
  integration/test_milestone_lapor.py
  integration/test_milestone_cair.py
  regression/test_r3_happy_path.py
```

---

### Task 0: Satu tempat untuk jembatan enum transisi

Dikerjakan lebih dulu, karena Task 3 dan Task 4 fase ini akan menambah dua pemanggil
`apply_*` lagi dan pola yang mereka contoh sekarang adalah pola yang salah.

**Kenapa task ini ada.** Mesin transisi di `app/domain/transitions.py` memakai enum domain.
Kolom database memakai enum di `app/models/`. Nilai stringnya sama, kelasnya tidak. Hasil
`apply_*` karena itu tidak boleh langsung ditulis ke kolom: mypy menolaknya, dan perbandingan
`is` di test akan selalu `False` tanpa satu pun pesan error muncul. Project ini sudah kena
sekali, di `test_recompute.py` fase 06.

Konversinya sudah ditulis tiga kali di tempat berbeda (`services/scoring.py` dua helper,
`services/campaign.py` satu). Docstring `services/scoring.py` bahkan mencatat sendiri bahwa
pola ini berulang. Fase ini akan menjadikannya lima. Konversi yang wajib, mudah lupa, dan
tidak bersuara saat dilupakan adalah kandidat yang tepat untuk dipusatkan dan dipagari,
alasan yang sama dengan [D-04](../docs/decisions.md) memusatkan peta transisinya.

**Files:**
- Create: `backend/app/services/status.py`
- Create: `backend/tests/unit/test_transition_guard.py`
- Modify: `backend/app/services/scoring.py` (buang `_advance_proposal`, `_advance_scoring`)
- Modify: `backend/app/services/campaign.py` (buang konversi inline di `_tutup`)

**Interfaces:**
- Produces: `advance_proposal(proposal, event) -> None`,
  `advance_scoring(proposal, event) -> None`,
  `advance_campaign(campaign, event) -> None`. Task 3 dan 4 fase ini menambahkan
  `advance_milestone` dan `advance_report` ke modul yang sama.

- [ ] **Step 1: Tulis pagarnya lebih dulu, dan pastikan ia merah**

Pagar ditulis sebelum modulnya, karena pagar inilah deliverable yang sebenarnya. Tanpa dia
task ini hanya memindahkan tiga salinan menjadi satu, dan salinan keempat akan muncul lagi
di fase berikutnya.

```python
# backend/tests/unit/test_transition_guard.py
"""Hanya app/services/status.py yang boleh memanggil apply_* dari luar domain.

Pagar ini ada karena hasil apply_* adalah enum domain, bukan enum kolom, dan
menulisnya langsung ke kolom gagal tanpa bersuara."""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
TRANSITIONS = {"apply_proposal", "apply_scoring", "apply_campaign",
            "apply_milestone", "apply_report"}
ALLOWED = {"services/status.py"}


def _callers(tree: ast.AST) -> set[str]:
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in TRANSITIONS:
                names.add(node.func.id)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in TRANSITIONS:
                names.add(node.func.attr)
    return names


def test_apply_transitions_only_called_from_services_status():
    violations = {}
    for f in APP.rglob("*.py"):
        rel = f.relative_to(APP).as_posix()
        if rel.startswith("domain/") or rel in ALLOWED:
            continue
        used = _callers(ast.parse(f.read_text()))
        if used:
            violations[rel] = sorted(used)
    assert not violations, (
        "apply_* dipanggil di luar app/services/status.py: "
        f"{violations}. Pakai advance_* dari modul itu, karena hasil apply_* "
        "adalah enum domain dan kolom database memakai enum lain."
    )


def test_this_guard_actually_detects_a_violation():
    """Tanpa test ini, pagar di atas bisa hijau karena detektornya rusak."""
    synthetic = ast.parse("def f(p, e):\n    p.status = apply_proposal(p.status, e)\n")
    assert _callers(synthetic) == {"apply_proposal"}
```

- [ ] **Step 2: Jalankan pagarnya, pastikan merah di dua file yang sudah ada**

Run: `cd backend && .venv/bin/pytest tests/unit/test_transition_guard.py -v`

Expected: `test_apply_transitions_only_called_from_services_status` FAIL, dan pesannya
menyebut `services/scoring.py` dan `services/campaign.py`. Kalau ia langsung hijau,
detektornya rusak, bukan kodenya bersih. Yang kedua harus PASS.

Catat output merahnya di laporan. Pagar yang tidak pernah terlihat merah belum terbukti.

- [ ] **Step 3: Tulis modulnya**

```python
# backend/app/services/status.py
"""Jembatan nilai antara enum transisi domain dan enum kolom database.

Nilai stringnya sama, kelasnya beda, dan menulis hasil apply_* langsung ke kolom
gagal tanpa bersuara: mypy menolaknya dan perbandingan `is` di test selalu salah.
Konversinya dipusatkan di sini supaya tests/unit/test_transition_guard.py bisa
menegakkannya, bukan supaya lebih singkat."""

from app.domain.transitions import (
    CampaignEvent,
    ProposalEvent,
    ScoringEvent,
    apply_campaign,
    apply_proposal,
    apply_scoring,
)
from app.domain.transitions import CampaignStatus as DomainCampaignStatus
from app.domain.transitions import ProposalStatus as DomainProposalStatus
from app.domain.transitions import ScoringStatus as DomainScoringStatus
from app.models.campaign import Campaign, CampaignStatus
from app.models.proposal import Proposal, ProposalStatus, ScoringStatus


def advance_proposal(proposal: Proposal, event: ProposalEvent) -> None:
    baru = apply_proposal(DomainProposalStatus(proposal.status.value), event)
    proposal.status = ProposalStatus(baru.value)


def advance_scoring(proposal: Proposal, event: ScoringEvent) -> None:
    baru = apply_scoring(DomainScoringStatus(proposal.scoring_status.value), event)
    proposal.scoring_status = ScoringStatus(baru.value)


def advance_campaign(campaign: Campaign, event: CampaignEvent) -> None:
    baru = apply_campaign(DomainCampaignStatus(campaign.status.value), event)
    campaign.status = CampaignStatus(baru.value)
```

`IllegalTransition` tetap dilempar oleh `apply_*` dan menembus fungsi-fungsi ini tanpa
ditangkap. Pemanggil yang perlu mengubahnya menjadi `409` tetap menangkapnya sendiri,
seperti sekarang.

- [ ] **Step 4: Pindahkan tiga pemanggil yang sudah ada**

Di `services/scoring.py`: hapus `_advance_proposal` dan `_advance_scoring`, impor
`advance_proposal` dan `advance_scoring` dari `app.services.status`, ganti pemanggilannya.
Buang impor `apply_proposal`, `apply_scoring`, `DomainProposalStatus`, `DomainScoringStatus`
yang jadi tidak terpakai. Perbarui docstring modulnya: paragraf yang menjelaskan jembatan
enum sekarang tinggal menunjuk ke `services/status.py`.

Di `services/campaign.py`: hal yang sama untuk `_tutup` dan `advance_campaign`.

Jangan ubah perilaku apa pun. Tidak ada test yang boleh berubah di step ini, dan itulah
buktinya pemindahan ini benar.

- [ ] **Step 5: Jalankan semuanya**

Run: `make check && make test-regression`

Expected: pagar hijau, dan jumlah test yang lolos **sama** dengan sebelum task ini
dimulai. Catat kedua angkanya di laporan. Angka yang turun berarti ada test yang hilang,
bukan ada test yang membaik.

- [ ] **Step 6: Commit**

```bash
git commit -am "refactor: centralize the domain to column enum bridge"
```

---

### Task 1: Prasyarat milestone sebagai fungsi murni

**Files:**
- Create: `backend/app/domain/milestone_rules.py`
- Test: `backend/tests/unit/test_milestone_rules.py`

**Interfaces:**
- Produces: `boleh_dilaporkan(seq, status_sebelumnya) -> bool`,
  `butuh_laporan(seq) -> bool`, `prasyarat_pencairan(...) -> None` yang melempar `ValueError`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_milestone_rules.py
import pytest
from app.domain.milestone_rules import boleh_dilaporkan, butuh_laporan, prasyarat_pencairan
from app.domain.transitions import MilestoneStatus as M

def test_d13_milestone_pertama_tidak_butuh_laporan():
    assert butuh_laporan(seq=1) is False

@pytest.mark.parametrize("seq", [2, 3, 7])
def test_br42_milestone_berikutnya_butuh_laporan(seq):
    assert butuh_laporan(seq) is True

def test_br41_milestone_pertama_tidak_bisa_dilaporkan():
    assert boleh_dilaporkan(seq=1, status_sebelumnya=None) is False

def test_br43_milestone_kedua_bisa_dilaporkan_setelah_pertama_cair():
    assert boleh_dilaporkan(seq=2, status_sebelumnya=M.DISBURSED) is True

@pytest.mark.parametrize("status", [M.PENDING, M.REPORTED])
def test_br43_milestone_kedua_belum_bisa_dilaporkan_kalau_pertama_belum_cair(status):
    assert boleh_dilaporkan(seq=2, status_sebelumnya=status) is False

def test_br43_prasyarat_pencairan_menolak_lompatan():
    with pytest.raises(ValueError, match="milestone sebelumnya"):
        prasyarat_pencairan(seq=3, status_sebelumnya=M.PENDING, proposal_funded=True)

def test_br40_prasyarat_pencairan_menolak_proposal_belum_funded():
    with pytest.raises(ValueError, match="belum funded"):
        prasyarat_pencairan(seq=1, status_sebelumnya=None, proposal_funded=False)
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_milestone_rules.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/domain/milestone_rules.py
"""Prasyarat pelaporan dan pencairan milestone. Murni, tanpa database."""
from app.domain.transitions import MilestoneStatus

def butuh_laporan(seq: int) -> bool:
    """Milestone pertama cair tanpa laporan, tetap butuh approve lead investor (D-13)."""
    return seq > 1

def boleh_dilaporkan(seq: int, status_sebelumnya: MilestoneStatus | None) -> bool:
    if not butuh_laporan(seq):
        return False
    return status_sebelumnya is MilestoneStatus.DISBURSED

def prasyarat_pencairan(
    seq: int, status_sebelumnya: MilestoneStatus | None, proposal_funded: bool
) -> None:
    if not proposal_funded:
        raise ValueError("Proposal belum funded, pencairan belum bisa dilakukan.")
    if seq > 1 and status_sebelumnya is not MilestoneStatus.DISBURSED:
        raise ValueError("Milestone sebelumnya belum cair.")
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_milestone_rules.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add milestone reporting and disbursement preconditions"
```

---

### Task 2: Laporan progres dengan jejak revisi

**Files:**
- Create: `backend/app/models/milestone_report.py`, `backend/app/api/v1/milestones.py`
- Test: `backend/tests/integration/test_milestone_lapor.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_milestone_lapor.py
def body_laporan(**ubah):
    return {"narrative": "Mesin kopi sudah dibeli dan dipasang. "
                         "Omzet minggu pertama naik 15 persen.",
            "metrics": {"omzet_minggu_1": 3_200_000}} | ubah

async def test_umkm_bisa_lapor_milestone_kedua(client, umkm, funded_proposal):
    m1, m2 = funded_proposal.milestones
    await cairkan_lewat_api(client, m1)
    res = await client.post(f"/api/v1/milestones/{m2.id}/reports",
                            headers=umkm.headers, json=body_laporan())
    assert res.status_code == 201

async def test_br41_milestone_pertama_tidak_bisa_dilaporkan(client, umkm, funded_proposal):
    m1 = funded_proposal.milestones[0]
    res = await client.post(f"/api/v1/milestones/{m1.id}/reports",
                            headers=umkm.headers, json=body_laporan())
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "milestone_pertama_tanpa_laporan"

async def test_br43_milestone_kedua_dilaporkan_sebelum_pertama_cair_ditolak(
    client, umkm, funded_proposal
):
    m2 = funded_proposal.milestones[1]
    res = await client.post(f"/api/v1/milestones/{m2.id}/reports",
                            headers=umkm.headers, json=body_laporan())
    assert res.status_code == 409

async def test_br46_laporan_yang_direject_tidak_dihapus_dan_revisi_jadi_baris_baru(
    client, db, umkm, investor, funded_proposal
):
    m1, m2 = funded_proposal.milestones
    await cairkan_lewat_api(client, m1)

    pertama = await client.post(f"/api/v1/milestones/{m2.id}/reports",
                                headers=umkm.headers, json=body_laporan())
    await client.post(f"/api/v1/milestones/{m2.id}/reject", headers=investor.headers,
                      json={"note": "Angka omzet belum disertai bukti."})
    await client.post(f"/api/v1/milestones/{m2.id}/reports", headers=umkm.headers,
                      json=body_laporan(narrative="Revisi: bukti terlampir." + "x" * 40))

    laporan = (await db.scalars(select(MilestoneReport)
               .where(MilestoneReport.milestone_id == m2.id)
               .order_by(MilestoneReport.submitted_at))).all()
    assert len(laporan) == 2
    assert laporan[0].review_status is ReportStatus.REJECTED
    assert laporan[0].reviewer_note == "Angka omzet belum disertai bukti."
    assert laporan[1].review_status is ReportStatus.PENDING

async def test_t30_approve_marks_report_approved(client, db, investor,
                                                      milestone_reported):
    await client.post(f"/api/v1/milestones/{milestone_reported.id}/approve",
                      headers=investor.headers)
    laporan = await laporan_terakhir(db, milestone_reported.id)
    assert laporan.review_status is ReportStatus.APPROVED
    assert laporan.reviewed_by == investor.user.id

async def test_t31_reject_menandai_laporan_rejected_beserta_catatan(
    client, db, investor, milestone_reported
):
    await client.post(f"/api/v1/milestones/{milestone_reported.id}/reject",
                      headers=investor.headers,
                      json={"note": "Angka omzet belum disertai bukti."})
    laporan = await laporan_terakhir(db, milestone_reported.id)
    assert laporan.review_status is ReportStatus.REJECTED
    assert laporan.reviewer_note == "Angka omzet belum disertai bukti."
    assert laporan.reviewed_at is not None

async def test_br45_reject_tanpa_catatan_ditolak(client, investor, milestone_reported):
    res = await client.post(f"/api/v1/milestones/{milestone_reported.id}/reject",
                            headers=investor.headers, json={"note": "x"})
    assert res.status_code == 422

async def test_umkm_lain_tidak_bisa_lapor(client, umkm_lain, funded_proposal):
    m2 = funded_proposal.milestones[1]
    res = await client.post(f"/api/v1/milestones/{m2.id}/reports",
                            headers=umkm_lain.headers, json=body_laporan())
    assert res.status_code in {403, 404}
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_milestone_lapor.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Model `MilestoneReport` seperti di [09-data-model](../prd/09-data-model.md). Service:

```python
async def kirim_laporan(session, umkm, milestone, body, clock) -> MilestoneReport:
    sebelumnya = await ambil_milestone_sebelumnya(session, milestone)
    if not boleh_dilaporkan(milestone.seq, sebelumnya.status if sebelumnya else None):
        kode = ("milestone_pertama_tanpa_laporan" if milestone.seq == 1
                else "milestone_sebelumnya_belum_cair")
        raise ConflictError(kode, "Milestone ini belum bisa dilaporkan.")

    laporan = MilestoneReport(milestone_id=milestone.id, umkm_id=umkm.id,
                              narrative=body.narrative, metrics=body.metrics,
                              review_status=ReportStatus.PENDING, submitted_at=clock.now())
    session.add(laporan)
    milestone.status = apply_milestone(milestone.status, MilestoneEvent.LAPOR)
    await session.flush()
    return laporan
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_milestone_lapor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add milestone progress reports with revision history"
```

---

### Task 3: Approve, reject, dan pencairan

**Files:**
- Modify: `backend/app/services/milestone.py`, `backend/app/api/v1/milestones.py`
- Test: `backend/tests/integration/test_milestone_cair.py`

**Interfaces:**
- Produces: `approve_milestone(session, lead, milestone, clock) -> None` yang mencatat
  `disbursement_out` dan, bila itu milestone terakhir, mentransisikan proposal ke `completed`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_milestone_cair.py
from app.domain.transitions import MilestoneStatus as M, ProposalStatus as S

async def test_d13_milestone_pertama_cair_tanpa_laporan_setelah_approve(
    client, db, investor, funded_proposal
):
    m1 = funded_proposal.milestones[0]
    res = await client.post(f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers)
    assert res.status_code == 200
    await db.refresh(m1)
    assert m1.status is M.DISBURSED

async def test_br47_approve_mencatat_disbursement_sebesar_amount_milestone(
    client, db, investor, funded_proposal
):
    m1 = funded_proposal.milestones[0]
    await client.post(f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers)
    entri = (await db.scalars(select(LedgerEntry).where(
        LedgerEntry.proposal_id == funded_proposal.id,
        LedgerEntry.entry_type == EntryType.DISBURSEMENT_OUT))).all()
    assert len(entri) == 1
    assert entri[0].amount == m1.amount

async def test_br44_investor_yang_bukan_lead_tidak_bisa_approve(
    client, investor_kecil, funded_proposal
):
    """investor_kecil ikut mendanai tapi bukan pemilik pledge terbesar."""
    m1 = funded_proposal.milestones[0]
    res = await client.post(f"/api/v1/milestones/{m1.id}/approve",
                            headers=investor_kecil.headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "bukan_lead_investor"

async def test_t09_milestone_terakhir_cair_membuat_proposal_completed(
    client, db, investor, umkm, funded_proposal
):
    m1, m2 = funded_proposal.milestones
    await client.post(f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers)
    await client.post(f"/api/v1/milestones/{m2.id}/reports", headers=umkm.headers,
                      json={"narrative": "x" * 60, "metrics": None})
    await client.post(f"/api/v1/milestones/{m2.id}/approve", headers=investor.headers)

    await db.refresh(funded_proposal)
    assert funded_proposal.status is S.COMPLETED

async def test_seluruh_dana_cair_sama_dengan_dana_diminta(client, db, investor, umkm,
                                                          funded_proposal):
    await cairkan_semua(client, investor, umkm, funded_proposal)
    cair = await db.scalar(select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
        LedgerEntry.proposal_id == funded_proposal.id,
        LedgerEntry.entry_type == EntryType.DISBURSEMENT_OUT))
    assert cair == funded_proposal.requested_amount
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_milestone_cair.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
async def approve_milestone(session, aktor, milestone, clock) -> None:
    # Mengunci baris proposal karena di sini uang bergerak (RF-5).
    proposal = await ambil_proposal_terkunci(session, milestone.proposal_id)

    if proposal.lead_investor_id != aktor.id:
        raise ForbiddenError("bukan_lead_investor",
                             "Hanya lead investor yang bisa menyetujui pencairan.")

    sebelumnya = await ambil_milestone_sebelumnya(session, milestone)
    try:
        prasyarat_pencairan(milestone.seq, sebelumnya.status if sebelumnya else None,
                            proposal.status is ProposalStatus.FUNDED)
    except ValueError as exc:
        raise ConflictError("prasyarat_pencairan_belum_terpenuhi", str(exc)) from None

    event = (MilestoneEvent.APPROVE_TANPA_LAPORAN if milestone.seq == 1
             else MilestoneEvent.APPROVE)
    milestone.status = apply_milestone(milestone.status, event)
    milestone.disbursed_at = clock.now()

    # Kunci idempotensi berasal dari milestone, jadi approve ganda hanya
    # menghasilkan satu entri (BR-48, RF-5).
    await record_entry(session, proposal.id, EntryType.DISBURSEMENT_OUT, milestone.amount,
                      idempotency_key=f"disburse:{milestone.id}",
                      ref_type="milestone", ref_id=milestone.id, actor_id=aktor.id)

    if await all_milestones_disbursed(session, proposal.id):
        proposal.status = apply_proposal(proposal.status,
                                         ProposalEvent.SEMUA_MILESTONE_CAIR)
    await session.flush()
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_milestone_cair.py -v`
Expected: PASS

- [ ] **Step 5: Perbarui RBAC_MATRIX, jalankan R5**

Run: `pytest tests/regression -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add milestone approval, rejection and ledger disbursement"
```

---

### Task 4: Approve ganda bersamaan (RF-5)

**Files:**
- Test: `backend/tests/integration/test_approve_bersamaan.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_approve_bersamaan.py
"""RF-5: approve milestone terakhir dikirim dua kali nyaris bersamaan."""
import asyncio
from app.db.session import SessionLocal
from app.domain.transitions import ProposalStatus as S

async def test_rf5_approve_ganda_hanya_satu_pencairan(funded_proposal_tercommit, lead, clock):
    m1 = funded_proposal_tercommit.milestones[0]

    async def approve():
        async with SessionLocal() as sesi, sesi.begin():
            with contextlib.suppress(Exception):
                milestone = await sesi.get(ProposalMilestone, m1.id)
                await approve_milestone(sesi, lead.user, milestone, clock)

    await asyncio.gather(approve(), approve())

    async with SessionLocal() as sesi:
        entri = (await sesi.scalars(select(LedgerEntry).where(
            LedgerEntry.ref_id == m1.id,
            LedgerEntry.entry_type == EntryType.DISBURSEMENT_OUT))).all()
    assert len(entri) == 1, "approve ganda menghasilkan dua pencairan"

async def test_rf5_approve_ganda_milestone_terakhir_hanya_satu_transisi_completed(
    funded_proposal_tercommit, lead, clock
):
    await cairkan(funded_proposal_tercommit.milestones[0])
    await laporkan(funded_proposal_tercommit.milestones[1])
    m_terakhir = funded_proposal_tercommit.milestones[1]

    async def approve():
        async with SessionLocal() as sesi, sesi.begin():
            with contextlib.suppress(Exception):
                milestone = await sesi.get(ProposalMilestone, m_terakhir.id)
                await approve_milestone(sesi, lead.user, milestone, clock)

    await asyncio.gather(approve(), approve())

    async with SessionLocal() as sesi:
        proposal = await sesi.get(Proposal, funded_proposal_tercommit.id)
        cair = await total_disbursement(sesi, proposal.id)
    assert proposal.status is S.COMPLETED
    assert cair == proposal.requested_amount   # bukan dua kali lipat
```

- [ ] **Step 2: Jalankan test**

Run: `pytest tests/integration/test_approve_bersamaan.py -v`
Expected: PASS kalau `ambil_proposal_terkunci` dan `idempotency_key` sudah dipasang di Task 3.
Kalau merah, itu berarti salah satunya terlewat.

- [ ] **Step 3: Buktikan pagarnya benar-benar bekerja**

Hapus sementara `with_for_update()` dari `ambil_proposal_terkunci`, jalankan ulang test, pastikan
**merah**, lalu kembalikan. Test yang tidak pernah bisa merah tidak membuktikan apa-apa.

- [ ] **Step 4: Commit**

```bash
git commit -am "feat: prevent double disbursement on concurrent milestone approval"
```

---

### Task 5: Regression R3, happy path end-to-end

**Files:**
- Create: `backend/tests/regression/test_r3_happy_path.py`

Satu test panjang, sengaja tidak dipecah, karena yang diuji adalah rantainya.

- [ ] **Step 1: Tulis test**

```python
# backend/tests/regression/test_r3_happy_path.py
"""R3: campaign dibuat sampai proposal completed, satu alur utuh."""
from app.domain.transitions import ProposalStatus as S

async def test_r3_alur_penuh_dari_campaign_sampai_completed(client, db, clock):
    # 1. Investor A dan B registrasi, A membuat campaign
    a = await daftar(client, "a@contoh.id", "investor")
    b = await daftar(client, "b@contoh.id", "investor")
    campaign = await create_campaign(client, a, target=50_000_000, threshold=60)

    # 2. UMKM registrasi dan submit proposal dengan dua milestone
    umkm = await daftar(client, "umkm@contoh.id", "umkm")
    proposal = await submit_proposal(client, umkm, campaign, diminta=10_000_000,
                                     milestones=[5_000_000, 5_000_000])

    # 3. MockScoringEngine menilai, proposal menjadi listed
    assert (await get_proposal(client, proposal))["status"] == "listed"

    # 4. Komunitas vote
    warga = await daftar(client, "warga@contoh.id", "community")
    await vote(client, warga, proposal)
    assert (await get_proposal(client, proposal))["vote_count"] == 1

    # 5. Investor A pledge separuh
    await pledge(client, a, proposal, 6_000_000)
    assert (await get_proposal(client, proposal))["status"] == "partially_funded"

    # 6. Investor B pledge sisanya, A jadi lead karena pledge-nya lebih besar
    await pledge(client, b, proposal, 4_000_000)
    detail = await get_proposal(client, proposal)
    assert detail["status"] == "funded"
    assert detail["lead_investor_id"] == a.user_id

    # 7. Lead investor approve milestone 1, tanpa laporan (D-13)
    m1, m2 = (await ambil_milestones(client, proposal))
    await approve(client, a, m1)
    assert (await ambil_milestones(client, proposal))[0]["status"] == "disbursed"

    # 8. UMKM lapor milestone 2, lead investor approve
    await lapor(client, umkm, m2, "Mesin terpasang, omzet naik 15 persen." + "x" * 30)
    await approve(client, a, m2)

    # 9. Proposal completed
    assert (await get_proposal(client, proposal))["status"] == "completed"

    # 10. Seluruh dana cair sama persis dengan dana yang diminta
    ledger = await ambil_ledger(client, a, proposal)
    cair = sum(e["amount"] for e in ledger["entries"]
               if e["entry_type"] == "disbursement_out")
    assert cair == 10_000_000
    assert ledger["saldo"] == 0

async def test_r3_investor_b_tidak_bisa_approve_karena_bukan_lead(client):
    """Cabang kecil dari alur yang sama, dipisah supaya kegagalannya jelas."""
    ...
```

- [ ] **Step 2: Jalankan, pastikan hijau**

Run: `pytest tests/regression -v`
Expected: PASS, R1, R2, R2b, R3, R5, R6

- [ ] **Step 3: Commit**

```bash
git add backend/tests/regression/test_r3_happy_path.py
git commit -m "feat: add end-to-end happy path regression suite"
```

### Task 6: Empat endpoint baca yang dipakai frontend

Task ini ada karena audit controller terhadap `10-api-contract.md` menemukan empat endpoint
yang dideklarasikan kontrak tapi tidak dimiliki task mana pun di seluruh plan. Tiga di
antaranya sudah dipanggil kode frontend yang selesai dibangun hari ini, jadi tanpa task ini
halaman-halaman itu menerima 404 dan demo tidak berjalan.

**Files:**
- Modify: `backend/app/api/v1/proposals.py`, `backend/app/api/v1/pledges.py`
- Create: `backend/app/api/v1/milestones.py` bila Task 3 belum membuatnya
- Create: `backend/app/api/v1/internal.py`
- Modify: `backend/app/schemas/` sesuai kebutuhan tiap respons
- Test: `backend/tests/integration/test_read_endpoints.py`

**Empat endpoint, dengan hak akses yang dipatok spec:**

| Endpoint | Siapa boleh | Isi |
| --- | --- | --- |
| `GET /proposals/mine` | umkm | Proposal milik pengguna saat ini beserta statusnya |
| `GET /proposals/{id}/pledges` | investor, pemilik proposal | Pledge **aktif** beserta nominal dan penanda lead investor |
| `GET /proposals/{id}/milestones` | publik bila proposal publik | Milestone beserta status dan laporan terakhir |
| `GET /internal/ledger/{proposal_id}` | lihat catatan di bawah | Seluruh entri ledger beserta saldo hasil penjumlahan |

`10-api-contract.md` baris 57, 67, 73, dan 96 adalah otoritasnya. Kalau task ini dan baris
itu berselisih, baris itu yang benar.

**Dua hal yang paling mudah salah di sini:**

`GET /proposals/{id}/pledges` mengembalikan pledge **aktif saja**, bukan seluruh riwayat.
Pledge yang dibatalkan tidak muncul. Frontend sudah dibangun dengan asumsi itu, dan asumsi
itu berasal dari kontrak, bukan dari kenyamanan.

`GET /internal/ledger/{proposal_id}` menghitung saldo dengan **menjumlahkan entri**, tidak
pernah membaca kolom saldo, karena kolom itu tidak ada dan tidak boleh ada (BR-51, D-03).
Endpoint ini ada supaya juri bisa memeriksa bahwa uang benar-benar dicatat, jadi ia harus
memperlihatkan entrinya satu per satu, bukan hanya angka akhirnya.

**Soal akses `/internal/`.** Kontrak tidak menyebut perannya. Putuskan sendiri dan tulis
alasannya di docstring, dengan dua batasan: ia tidak boleh membuka data satu pengguna ke
pengguna lain yang tidak berhak melihatnya lewat jalur biasa, dan ia tidak boleh dilindungi
oleh sesuatu yang di-hardcode. Kalau pilihanmu membuat endpoint ini terbuka, katakan
terang-terangan di laporan supaya controller bisa menolaknya.

- [ ] **Step 1: Tulis test yang gagal**

Enam test, masing-masing bisa merah karena alasan berbeda:

1. `GET /proposals/mine` mengembalikan hanya proposal milik akun yang masuk. Test ini wajib
   membuat proposal untuk **dua** UMKM berbeda dan memastikan yang satu tidak melihat milik
   yang lain. Satu UMKM saja akan lolos tanpa membuktikan apa pun.
2. `GET /proposals/mine` ditolak untuk peran investor.
3. `GET /proposals/{id}/pledges` menyembunyikan pledge yang dibatalkan. Test ini membuat dua
   pledge, membatalkan satu, dan memeriksa panjang daftarnya, bukan hanya statusnya.
4. `GET /proposals/{id}/pledges` menandai lead investor dengan benar, dan penandanya ikut
   berpindah setelah pledge terbesar dibatalkan.
5. `GET /proposals/{id}/milestones` memuat laporan terakhir, bukan laporan pertama, untuk
   milestone yang laporannya pernah ditolak lalu dikirim ulang.
6. `GET /internal/ledger/{proposal_id}` menghasilkan saldo yang sama dengan penjumlahan
   manual atas entri yang ia kembalikan. Test ini membandingkan dua angka yang dihitung
   dengan cara berbeda; itulah yang membuatnya berguna.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `cd backend && .venv/bin/pytest tests/integration/test_read_endpoints.py -v`
Expected: keenamnya FAIL karena endpointnya belum ada. Catat outputnya.

- [ ] **Step 3: Implementasi**

Seluruh query hidup di `services/`, bukan di router. Pagar AST di
`tests/unit/test_layering_guard.py` memeriksa setiap file di `app/api/` dan akan menangkapmu.

Hak akses dipasang lewat dependency, bukan lewat `if` di dalam handler, dan mengikuti pola
yang sudah ada: **bukan pemilik mendapat 404, bukan 403**, karena 403 memberi tahu bahwa
sumber dayanya ada. Pengecualiannya `GET /proposals/mine` yang ditolak karena peran, bukan
karena kepemilikan, dan di situ 403 benar.

- [ ] **Step 4: Perbarui RBAC_MATRIX, jalankan R5**

Empat endpoint baru kali setiap peran, ditambah kasus "peran benar tapi bukan pemilik".
R5 adalah regression yang menolak endpoint yang lupa didaftarkan, jadi angka barisnya harus
naik. Catat angka sebelum dan sesudah.

- [ ] **Step 5: Jalankan semuanya**

Run: `make check && make test-regression`

- [ ] **Step 6: Pagar yang membuat lubang ini tidak bisa terulang**

Empat endpoint ini hilang karena tidak ada apa pun yang membandingkan kontrak dengan
kenyataan. `10-api-contract.md` mendeklarasikan 30 endpoint; kode punya 17; tidak satu test
pun menyebut selisihnya. Lubang sejenis pernah terjadi di sisi frontend, di mana fase 11
mendeklarasikan sembilan halaman lalu hanya mengerjakan dua.

```python
# backend/tests/unit/test_contract_coverage.py
# Setiap endpoint di 10-api-contract.md harus benar-benar terdaftar di aplikasi.
# Pagar ini ada karena empat endpoint baca sempat hilang dari seluruh plan: kontrak
# menyebutnya, tidak ada task yang membangunnya, dan tidak ada test yang menyadarinya.
import re
from pathlib import Path

from app.main import app

KONTRAK = Path(__file__).resolve().parents[3] / ".claude/prd/10-api-contract.md"
POLA = re.compile(r"`(GET|POST|PATCH|PUT|DELETE) (/[a-zA-Z0-9{}/_-]+)`")


def _samakan(path: str) -> str:
    # Nama parameter berbeda antara dokumen dan kode ({id} vs {proposal_id}), dan
    # yang dibandingkan adalah bentuk route-nya, bukan ejaan parameternya.
    return re.sub(r"\{[a-zA-Z_]+\}", "{}", path.replace("/api/v1", ""))


def _terdaftar() -> set[str]:
    hasil = set()
    for route in app.routes:
        for method in getattr(route, "methods", set()) or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            hasil.add(f"{method} {_samakan(route.path)}")
    return hasil


def test_every_contract_endpoint_registered_in_app():
    terdaftar = _terdaftar()
    diminta = {
        f"{m} {_samakan(p)}": f"{m} {p}"
        for m, p in POLA.findall(KONTRAK.read_text())
    }
    hilang = sorted(asli for kunci, asli in diminta.items() if kunci not in terdaftar)
    assert not hilang, (
        "endpoint ini ada di 10-api-contract.md tapi tidak terdaftar di aplikasi: "
        f"{hilang}"
    )


def test_this_guard_actually_compares_something():
    # Tanpa test ini, pagar di atas bisa hijau karena daftarnya kosong.
    diminta = POLA.findall(KONTRAK.read_text())
    assert len(diminta) >= 25, (
        f"hanya {len(diminta)} endpoint terbaca dari kontrak; polanya berhenti cocok"
    )
    assert len(_terdaftar()) >= 20
```

`app.routes` **tidak** memperlihatkan route sub-router kalau dibaca secara naif: FastAPI
membungkus `include_router()`, dan pagar sejenis di project ini pernah hijau palsu selama
satu fase penuh dengan matriks 6 baris dari 21. Periksa jumlah yang benar-benar terbaca
lebih dulu, dan kalau `app.routes` ternyata tidak cukup, telusuri `route.routes` secara
rekursif. Test kedua di atas ada untuk itu.

Buktikan pagarnya bisa merah: hapus sementara satu endpoint dari routernya, jalankan, lihat
ia menyebut endpoint itu, lalu pulihkan.

- [ ] **Step 7: Commit**

Satu commit per endpoint kalau pengerjaannya terpisah, atau satu commit untuk keempatnya
kalau dikerjakan bersama. Pagar kontrak masuk commitnya sendiri. Namai sesuai isinya.

---

## Gerbang keluar fase 07

- [ ] `make test` dan `make test-regression` hijau
- [ ] R3 berjalan dari campaign sampai `completed` tanpa intervensi manual
- [ ] Jumlah seluruh `disbursement_out` sama persis dengan `requested_amount`
- [ ] Test approve bersamaan terbukti merah saat penguncian dihapus

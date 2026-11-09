# Fase 01. Domain murni

**Hasil:** seluruh aturan uang dan status hidup sebagai fungsi murni yang bisa diuji tanpa
database dan tanpa HTTP. Regression test R1 (matriks transisi lengkap) hijau.

Fase ini dikerjakan **sebelum** auth dan sebelum model database. Alasannya: kalau aturan ditulis
belakangan, ia akan lahir di dalam router dan tidak akan pernah pindah.

**Spec terkait:** [08-state-machines](../prd/08-state-machines.md), [07-business-rules](../prd/07-business-rules.md)

## Struktur file

```
backend/app/domain/
  __init__.py
  money.py           # parsing, validasi, format rupiah
  clock.py           # satu-satunya sumber waktu
  transitions.py     # peta transisi keempat mesin status
  funding.py         # compute_funding_status, hitung sisa dana
  lead_investor.py   # penentuan lead investor + pemutus seri
backend/tests/unit/
  test_money.py
  test_clock.py
  test_transitions.py
  test_funding.py
  test_lead_investor.py
backend/tests/regression/
  test_r1_transitions.py
```

Tidak ada satu pun file di `domain/` yang boleh mengimpor `sqlmodel`, `sqlalchemy`, atau `fastapi`.
Itu diuji secara eksplisit di Task 6.

---

### Task 1: Aritmetika rupiah

**Files:**
- Create: `backend/app/domain/money.py`
- Test: `backend/tests/unit/test_money.py`

**Interfaces:**
- Produces: `Rupiah = int`, `parse_rupiah(value: object) -> int`, `format_rupiah(amount: int) -> str`,
  `MAX_RUPIAH: int`. Dipakai oleh seluruh schema Pydantic yang menerima nominal.

Ini juga tempat **RF-2** ditegakkan: nominal yang dikirim sebagai string ilmiah, pecahan, atau di
luar jangkauan `BIGINT` ditolak, bukan dibulatkan diam-diam.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_money.py
import pytest
from app.domain.money import MAX_RUPIAH, format_rupiah, parse_rupiah

def test_parse_accepts_positive_integer():
    assert parse_rupiah(5_000_000) == 5_000_000

@pytest.mark.parametrize("nilai", [0, -1, -5_000_000])
def test_br54_parse_rejects_zero_and_negative(nilai):
    with pytest.raises(ValueError, match="harus lebih besar dari nol"):
        parse_rupiah(nilai)

@pytest.mark.parametrize("nilai", ["1e9", 1_000_000.5, "5.000.000", None, "abc", True])
def test_rf2_parse_rejects_non_integer_forms(nilai):
    with pytest.raises(ValueError):
        parse_rupiah(nilai)

def test_rf2_parse_rejects_out_of_bigint_range():
    with pytest.raises(ValueError, match="terlalu besar"):
        parse_rupiah(MAX_RUPIAH + 1)

def test_format_uses_dot_as_thousands_separator():
    assert format_rupiah(5_000_000) == "Rp5.000.000"
    assert format_rupiah(750) == "Rp750"
```

`True` masuk daftar tolak karena `bool` adalah subclass `int` di Python, dan `parse_rupiah(True)`
yang diam-diam menghasilkan 1 adalah bug yang sulit dilacak.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_money.py -v`
Expected: FAIL dengan `ModuleNotFoundError: No module named 'app.domain.money'`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/domain/money.py
"""Rupiah selalu integer penuh. Tidak ada sen, tidak ada float (BR-50)."""

Rupiah = int

MAX_RUPIAH = 9_223_372_036_854_775_807  # batas BIGINT Postgres

def parse_rupiah(value: object) -> Rupiah:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Nominal harus berupa bilangan bulat rupiah, tanpa desimal.")
    if value <= 0:
        raise ValueError("Nominal harus lebih besar dari nol.")
    if value > MAX_RUPIAH:
        raise ValueError("Nominal terlalu besar.")
    return value

def format_rupiah(amount: Rupiah) -> str:
    return f"Rp{amount:,}".replace(",", ".")
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_money.py -v`
Expected: PASS, 11 test

- [ ] **Step 5: Commit**

```bash
git add backend/app/domain/money.py backend/tests/unit/test_money.py
git commit -m "feat: add integer-only rupiah arithmetic"
```

---

### Task 2: Sumber waktu tunggal

**Files:**
- Create: `backend/app/domain/clock.py`
- Test: `backend/tests/unit/test_clock.py`

**Interfaces:**
- Produces: `Clock` protocol dengan `now() -> datetime`, `SystemClock`, `FrozenClock(at)`,
  `VirtualClock(offset)`. Dipakai oleh `funding.py`, service, dan endpoint tick di fase 09.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_clock.py
from datetime import UTC, datetime, timedelta
from app.domain.clock import FrozenClock, SystemClock, VirtualClock

def test_system_clock_returns_aware_time():
    assert SystemClock().now().tzinfo is not None

def test_frozen_clock_always_returns_the_same_time():
    saat = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)
    clock = FrozenClock(saat)
    assert clock.now() == saat == clock.now()

def test_virtual_clock_advances_by_offset():
    dasar = FrozenClock(datetime(2026, 11, 7, tzinfo=UTC))
    virtual = VirtualClock(dasar, offset=timedelta(days=30))
    assert virtual.now() == datetime(2026, 12, 7, tzinfo=UTC)
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_clock.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/domain/clock.py
"""Satu-satunya sumber waktu di seluruh aplikasi (BR-60).

Memanggil datetime.now() di luar modul ini dilarang. Ada test yang memeriksanya.
"""
from datetime import UTC, datetime, timedelta
from typing import Protocol

class Clock(Protocol):
    def now(self) -> datetime: ...

class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

class FrozenClock:
    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        return self._at

class VirtualClock:
    """Jam dasar ditambah offset, dipakai endpoint tick untuk mendemokan deadline (D-06)."""

    def __init__(self, base: Clock, offset: timedelta) -> None:
        self._base = base
        self._offset = offset

    def now(self) -> datetime:
        return self._base.now() + self._offset
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_clock.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add single clock source with frozen and virtual clocks"
```

---

### Task 3: Peta transisi

**Files:**
- Create: `backend/app/domain/transitions.py`
- Test: `backend/tests/unit/test_transitions.py`

**Interfaces:**
- Produces: enum `ProposalStatus`, `MilestoneStatus`, `ReportStatus`, `CampaignStatus`,
  `ScoringStatus`; enum `ProposalEvent`, `MilestoneEvent`; fungsi
  `apply_transition(current, event) -> NewStatus` yang melempar `IllegalTransition`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_transitions.py
import pytest
from app.domain.transitions import (
    IllegalTransition, MilestoneEvent, MilestoneStatus,
    ProposalEvent, ProposalStatus, apply_milestone, apply_proposal,
)

def test_t01_submitted_to_listed():
    assert apply_proposal(ProposalStatus.SUBMITTED, ProposalEvent.SCORING_LULUS) \
        is ProposalStatus.LISTED

def test_t03_listed_to_partially_funded():
    assert apply_proposal(ProposalStatus.LISTED, ProposalEvent.PLEDGE_SEBAGIAN) \
        is ProposalStatus.PARTIALLY_FUNDED

def test_t07_partially_funded_returns_to_listed_when_all_pledges_cancelled():
    assert apply_proposal(ProposalStatus.PARTIALLY_FUNDED, ProposalEvent.PLEDGE_KOSONG) \
        is ProposalStatus.LISTED

@pytest.mark.parametrize("status", [
    ProposalStatus.REJECTED, ProposalStatus.FAILED, ProposalStatus.COMPLETED,
])
@pytest.mark.parametrize("event", list(ProposalEvent))
def test_terminal_status_rejects_every_event(status, event):
    with pytest.raises(IllegalTransition):
        apply_proposal(status, event)

def test_t21_first_milestone_disburses_without_report():
    assert apply_milestone(MilestoneStatus.PENDING, MilestoneEvent.APPROVE_TANPA_LAPORAN) \
        is MilestoneStatus.DISBURSED

def test_t23_reject_returns_milestone_to_pending():
    assert apply_milestone(MilestoneStatus.REPORTED, MilestoneEvent.REJECT) \
        is MilestoneStatus.PENDING

def test_illegal_transition_names_status_and_event():
    with pytest.raises(IllegalTransition) as err:
        apply_proposal(ProposalStatus.FUNDED, ProposalEvent.PLEDGE_SEBAGIAN)
    assert "funded" in str(err.value)
    assert err.value.current is ProposalStatus.FUNDED
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_transitions.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/domain/transitions.py
"""Peta transisi keempat mesin status, ditulis sebagai data (D-04).

Menambah status berarti menambah entri di sini DAN baris di regression test R1.
Suite akan merah sampai keduanya dilakukan. Itu disengaja.
"""
from enum import StrEnum

class ProposalStatus(StrEnum):
    SUBMITTED = "submitted"
    LISTED = "listed"
    PARTIALLY_FUNDED = "partially_funded"
    REJECTED = "rejected"
    FUNDED = "funded"
    FAILED = "failed"
    COMPLETED = "completed"

class ProposalEvent(StrEnum):
    SCORING_LULUS = "scoring_lulus"
    SCORING_GAGAL = "scoring_gagal"
    PLEDGE_SEBAGIAN = "pledge_sebagian"
    PLEDGE_PENUH = "pledge_penuh"
    PLEDGE_KOSONG = "pledge_kosong"
    DEADLINE_LEWAT = "deadline_lewat"
    SEMUA_MILESTONE_CAIR = "semua_milestone_cair"

class MilestoneStatus(StrEnum):
    PENDING = "pending"
    REPORTED = "reported"
    DISBURSED = "disbursed"

class MilestoneEvent(StrEnum):
    LAPOR = "lapor"
    APPROVE_TANPA_LAPORAN = "approve_tanpa_laporan"
    APPROVE = "approve"
    REJECT = "reject"

S, E = ProposalStatus, ProposalEvent
PROPOSAL_MAP: dict[tuple[S, E], S] = {
    (S.SUBMITTED, E.SCORING_LULUS):         S.LISTED,             # T-01
    (S.SUBMITTED, E.SCORING_GAGAL):         S.REJECTED,           # T-02
    (S.LISTED, E.PLEDGE_SEBAGIAN):          S.PARTIALLY_FUNDED,   # T-03
    (S.LISTED, E.PLEDGE_PENUH):             S.FUNDED,             # T-04
    (S.LISTED, E.DEADLINE_LEWAT):           S.FAILED,             # T-05
    (S.PARTIALLY_FUNDED, E.PLEDGE_PENUH):   S.FUNDED,             # T-06
    (S.PARTIALLY_FUNDED, E.PLEDGE_KOSONG):  S.LISTED,             # T-07
    (S.PARTIALLY_FUNDED, E.DEADLINE_LEWAT): S.FAILED,             # T-08
    (S.FUNDED, E.SEMUA_MILESTONE_CAIR):     S.COMPLETED,          # T-09
}

M, ME = MilestoneStatus, MilestoneEvent
MILESTONE_MAP: dict[tuple[M, ME], M] = {
    (M.PENDING, ME.LAPOR):                  M.REPORTED,    # T-20
    (M.PENDING, ME.APPROVE_TANPA_LAPORAN):  M.DISBURSED,   # T-21
    (M.REPORTED, ME.APPROVE):               M.DISBURSED,   # T-22
    (M.REPORTED, ME.REJECT):                M.PENDING,     # T-23
}

class IllegalTransition(Exception):
    def __init__(self, current: StrEnum, event: StrEnum) -> None:
        super().__init__(f"Transisi tidak sah: {current.value} tidak menerima {event.value}.")
        self.current = current
        self.event = event

def apply_proposal(current: ProposalStatus, event: ProposalEvent) -> ProposalStatus:
    try:
        return PROPOSAL_MAP[(current, event)]
    except KeyError:
        raise IllegalTransition(current, event) from None

def apply_milestone(current: MilestoneStatus, event: MilestoneEvent) -> MilestoneStatus:
    try:
        return MILESTONE_MAP[(current, event)]
    except KeyError:
        raise IllegalTransition(current, event) from None
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_transitions.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add centralised status transition map"
```

---

### Task 4: Regression R1, matriks transisi lengkap

**Files:**
- Create: `backend/tests/regression/test_r1_transitions.py`

Ini bukan test fitur. Ini pernyataan bahwa **tidak ada transisi di luar peta yang pernah lolos**.

- [ ] **Step 1: Tulis test**

```python
# backend/tests/regression/test_r1_transitions.py
"""R1: setiap kombinasi status kali event diuji, yang legal maupun yang harus ditolak."""
import itertools
import pytest
from app.domain.transitions import (
    MILESTONE_MAP, PROPOSAL_MAP, IllegalTransition, MilestoneEvent,
    MilestoneStatus, ProposalEvent, ProposalStatus, apply_milestone, apply_proposal,
)

PROPOSAL_KOMBINASI = list(itertools.product(ProposalStatus, ProposalEvent))
MILESTONE_KOMBINASI = list(itertools.product(MilestoneStatus, MilestoneEvent))

@pytest.mark.parametrize("status,event", PROPOSAL_KOMBINASI)
def test_r1_proposal_every_combination_matches_map(status, event):
    if (status, event) in PROPOSAL_MAP:
        assert apply_proposal(status, event) is PROPOSAL_MAP[(status, event)]
    else:
        with pytest.raises(IllegalTransition):
            apply_proposal(status, event)

@pytest.mark.parametrize("status,event", MILESTONE_KOMBINASI)
def test_r1_milestone_every_combination_matches_map(status, event):
    if (status, event) in MILESTONE_MAP:
        assert apply_milestone(status, event) is MILESTONE_MAP[(status, event)]
    else:
        with pytest.raises(IllegalTransition):
            apply_milestone(status, event)

def test_r1_proposal_transition_count_matches_spec():
    """Mengunci jumlahnya ke spec. Menambah transisi tanpa memperbarui
    08-state-machines.md akan membuat test ini merah."""
    assert len(PROPOSAL_MAP) == 9   # T-01 sampai T-09

def test_r1_milestone_transition_count_matches_spec():
    assert len(MILESTONE_MAP) == 4  # T-20 sampai T-23

@pytest.mark.parametrize("terminal", [
    ProposalStatus.REJECTED, ProposalStatus.FAILED, ProposalStatus.COMPLETED,
])
def test_r1_terminal_status_has_no_way_out(terminal):
    assert not any(s is terminal for s, _ in PROPOSAL_MAP)
```

Dua test "jumlah transisi" sengaja ada. Tanpa itu, seseorang bisa menambah transisi baru dan
seluruh suite tetap hijau meski spec tidak diperbarui.

- [ ] **Step 2: Jalankan, pastikan hijau**

Run: `pytest tests/regression/test_r1_transitions.py -v`
Expected: PASS, 49 + 12 + 5 test (7 status kali 7 event untuk proposal, 3 status kali 4 event untuk milestone, lalu 2 test penguncian jumlah dan 3 test status terminal)

- [ ] **Step 3: Commit**

```bash
git add backend/tests/regression/test_r1_transitions.py
git commit -m "feat: add full status transition matrix regression suite"
```

---

### Task 5: Status funding dan lead investor

**Files:**
- Create: `backend/app/domain/funding.py`, `backend/app/domain/lead_investor.py`
- Test: `backend/tests/unit/test_funding.py`, `backend/tests/unit/test_lead_investor.py`

**Interfaces:**
- Produces: `compute_funding_status(total_pledged, requested, now, funding_deadline) -> ProposalStatus`,
  `remaining_amount(total_pledged, requested) -> int`,
  `pick_lead_investor(pledges: Sequence[PledgeSummary]) -> UUID | None`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_funding.py
from datetime import UTC, datetime, timedelta
import pytest
from app.domain.funding import compute_funding_status, remaining_amount
from app.domain.transitions import ProposalStatus as S

SEKARANG = datetime(2026, 11, 7, tzinfo=UTC)
BESOK = SEKARANG + timedelta(days=1)
KEMARIN = SEKARANG - timedelta(days=1)

@pytest.mark.parametrize("terkumpul,diminta,deadline,harapan", [
    (0,          10_000_000, BESOK,   S.LISTED),
    (4_000_000,  10_000_000, BESOK,   S.PARTIALLY_FUNDED),
    (10_000_000, 10_000_000, BESOK,   S.FUNDED),
    (10_000_000, 10_000_000, KEMARIN, S.FUNDED),   # sudah penuh, deadline tak relevan
    (0,          10_000_000, KEMARIN, S.FAILED),
    (4_000_000,  10_000_000, KEMARIN, S.FAILED),
])
def test_compute_funding_status(terkumpul, diminta, deadline, harapan):
    assert compute_funding_status(terkumpul, diminta, SEKARANG, deadline) is harapan

def test_br21_remaining_funds_computed_exactly():
    assert remaining_amount(4_000_000, 10_000_000) == 6_000_000
    assert remaining_amount(10_000_000, 10_000_000) == 0

def test_total_exceeding_requested_never_considered_valid():
    with pytest.raises(ValueError, match="melebihi"):
        compute_funding_status(11_000_000, 10_000_000, SEKARANG, BESOK)
```

Test terakhir penting: kalau keadaan itu pernah tercapai, berarti penguncian baris di fase 06
bocor, dan lebih baik sistem meledak keras daripada diam-diam menyimpan `funded` yang salah.

```python
# backend/tests/unit/test_lead_investor.py
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from app.domain.lead_investor import PledgeSummary, pick_lead_investor

T0 = datetime(2026, 11, 7, tzinfo=UTC)
A, B = uuid4(), uuid4()

def test_no_pledge_means_no_lead():
    assert pick_lead_investor([]) is None

def test_br23_largest_pledge_becomes_lead():
    pledges = [PledgeSummary(A, 3_000_000, T0), PledgeSummary(B, 7_000_000, T0)]
    assert pick_lead_investor(pledges) == B

def test_br24_multiple_pledges_from_same_investor_are_summed():
    pledges = [
        PledgeSummary(A, 4_000_000, T0),
        PledgeSummary(A, 4_000_000, T0 + timedelta(minutes=1)),
        PledgeSummary(B, 7_000_000, T0),
    ]
    assert pick_lead_investor(pledges) == A   # 8 juta mengalahkan 7 juta

def test_br23_tie_won_by_earliest_pledge():
    pledges = [
        PledgeSummary(B, 5_000_000, T0 + timedelta(minutes=5)),
        PledgeSummary(A, 5_000_000, T0),
    ]
    assert pick_lead_investor(pledges) == A
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_funding.py tests/unit/test_lead_investor.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/domain/funding.py
"""Penentuan status funding. Satu-satunya tempat status ini dihitung (D-05)."""
from datetime import datetime
from app.domain.money import Rupiah
from app.domain.transitions import ProposalStatus

def remaining_amount(total_pledged: Rupiah, requested: Rupiah) -> Rupiah:
    return max(requested - total_pledged, 0)

def compute_funding_status(
    total_pledged: Rupiah,
    requested: Rupiah,
    now: datetime,
    funding_deadline: datetime,
) -> ProposalStatus:
    if total_pledged > requested:
        raise ValueError(
            "Total pledge melebihi dana yang diminta. "
            "Ini seharusnya mustahil; penguncian baris proposal bocor."
        )
    if total_pledged == requested:
        return ProposalStatus.FUNDED
    if now >= funding_deadline:
        return ProposalStatus.FAILED
    if total_pledged == 0:
        return ProposalStatus.LISTED
    return ProposalStatus.PARTIALLY_FUNDED
```

```python
# backend/app/domain/lead_investor.py
"""Lead investor adalah pemilik total pledge aktif terbesar (BR-23)."""
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from app.domain.money import Rupiah

@dataclass(frozen=True, slots=True)
class PledgeSummary:
    investor_id: UUID
    amount: Rupiah
    created_at: datetime

def pick_lead_investor(pledges: Sequence[PledgeSummary]) -> UUID | None:
    if not pledges:
        return None

    total: dict[UUID, Rupiah] = defaultdict(int)
    pertama: dict[UUID, datetime] = {}
    for p in pledges:
        total[p.investor_id] += p.amount
        if p.investor_id not in pertama or p.created_at < pertama[p.investor_id]:
            pertama[p.investor_id] = p.created_at

    # Terbesar menang; seri diputus oleh pledge paling awal, bukan oleh urutan dict.
    return max(total, key=lambda inv: (total[inv], -pertama[inv].timestamp()))
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add funding status and lead investor selection"
```

---

### Task 6: Pagar arsitektur

**Files:**
- Create: `backend/tests/unit/test_domain_murni.py`

Tanpa test ini, `domain/` akan perlahan menarik `Session` ke dalamnya dan kemurniannya hilang
tanpa ada yang menyadari.

- [ ] **Step 1: Tulis test**

```python
# backend/tests/unit/test_domain_murni.py
"""Pagar arsitektur: domain/ tidak boleh tahu soal database, HTTP, atau jam sistem."""
import ast
import pathlib
import pytest

DOMAIN = pathlib.Path(__file__).parents[2] / "app" / "domain"
TERLARANG = {"sqlmodel", "sqlalchemy", "fastapi", "httpx", "asyncpg"}
FILE_DOMAIN = sorted(DOMAIN.glob("*.py"))

@pytest.mark.parametrize("berkas", FILE_DOMAIN, ids=lambda p: p.name)
def test_domain_does_not_import_database_or_http(berkas):
    pohon = ast.parse(berkas.read_text())
    diimpor = {
        (node.module or "").split(".")[0]
        for node in ast.walk(pohon)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(pohon)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    bocor = diimpor & TERLARANG
    assert not bocor, f"{berkas.name} mengimpor {bocor}; pindahkan logikanya ke services/"

@pytest.mark.parametrize("berkas", FILE_DOMAIN, ids=lambda p: p.name)
def test_br60_only_clock_may_call_datetime_now(berkas):
    if berkas.name == "clock.py":
        pytest.skip("clock.py adalah satu-satunya yang berhak")
    assert "datetime.now(" not in berkas.read_text(), (
        f"{berkas.name} memanggil datetime.now() langsung. Pakai Clock (BR-60)."
    )
```

- [ ] **Step 2: Jalankan, pastikan hijau**

Run: `pytest tests/unit/test_domain_murni.py -v`
Expected: PASS

- [ ] **Step 3: Perluas pagar ke services dan api**

Tambahkan test serupa yang memindai `app/services/` dan `app/api/` untuk `datetime.now(`,
dengan pesan yang sama. Pagar ini yang menjaga [BR-60](../prd/07-business-rules.md) tetap hidup
saat fase-fase berikutnya menambah banyak file.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_domain_murni.py
git commit -m "feat: add architecture guard for pure domain layer"
```

---

### Task 7: Tiga mesin status yang tersisa

**Files:**
- Modify: `backend/app/domain/transitions.py`
- Modify: `backend/tests/regression/test_r1_transitions.py`

**Interfaces:**
- Produces: `ReportStatus`, `ReportEvent`, `CampaignStatus`, `CampaignEvent`, `ScoringStatus`,
  `ScoringEvent`; `REPORT_MAP`, `CAMPAIGN_MAP`, `SCORING_MAP`; `apply_report()`,
  `apply_campaign()`, `apply_scoring()`.

`08-state-machines.md` mendefinisikan **empat** mesin status plus `scoring_status`, dan
`regression-checklist.md` menjanjikan R1 berlaku untuk semuanya. Task 3 baru mengerjakan proposal
dan milestone. Tiga sisanya dikerjakan di sini, sebelum ada service yang memakainya, supaya tidak
ada fase yang menambahkan enum status sendiri secara ad hoc di luar `transitions.py`.

`ScoringStatus` sengaja **terpisah** dari `ProposalStatus`. Keduanya tidak boleh dicampur:
`scoring_status = failed` berarti penilaian gagal dijalankan, bukan proposal ditolak
([D-09](../docs/decisions.md)).

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_transitions.py (tambahan)
import pytest
from app.domain.transitions import (
    CampaignEvent, CampaignStatus, IllegalTransition, ReportEvent, ReportStatus,
    ScoringEvent, ScoringStatus, apply_campaign, apply_report, apply_scoring,
)

def test_t30_approve_marks_report_approved():
    assert apply_report(ReportStatus.PENDING, ReportEvent.APPROVE) is ReportStatus.APPROVED

def test_t31_reject_marks_report_rejected():
    assert apply_report(ReportStatus.PENDING, ReportEvent.REJECT) is ReportStatus.REJECTED

def test_already_reviewed_report_cannot_be_reviewed_again():
    with pytest.raises(IllegalTransition):
        apply_report(ReportStatus.APPROVED, ReportEvent.REJECT)

def test_t40_campaign_closed_manually():
    assert apply_campaign(CampaignStatus.OPEN, CampaignEvent.TUTUP_MANUAL) \
        is CampaignStatus.CLOSED

def test_t41_campaign_closed_because_apply_deadline_passed():
    assert apply_campaign(CampaignStatus.OPEN, CampaignEvent.APPLY_DEADLINE_LEWAT) \
        is CampaignStatus.CLOSED

def test_closed_campaign_cannot_be_closed_again():
    with pytest.raises(IllegalTransition):
        apply_campaign(CampaignStatus.CLOSED, CampaignEvent.TUTUP_MANUAL)

def test_t50_through_t53_scoring_flow():
    assert apply_scoring(ScoringStatus.PENDING, ScoringEvent.AMBIL) is ScoringStatus.PROCESSING
    assert apply_scoring(ScoringStatus.PROCESSING, ScoringEvent.SELESAI) is ScoringStatus.DONE
    assert apply_scoring(ScoringStatus.PROCESSING, ScoringEvent.GAGAL) is ScoringStatus.FAILED
    assert apply_scoring(ScoringStatus.FAILED, ScoringEvent.NILAI_ULANG) is ScoringStatus.PENDING

def test_scoring_already_done_is_terminal():
    with pytest.raises(IllegalTransition):
        apply_scoring(ScoringStatus.DONE, ScoringEvent.AMBIL)
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `make test-unit`
Expected: FAIL dengan `ImportError: cannot import name 'ReportStatus'`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/domain/transitions.py (tambahan)

class ReportStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class ReportEvent(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"

class CampaignStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"

class CampaignEvent(StrEnum):
    TUTUP_MANUAL = "tutup_manual"
    APPLY_DEADLINE_LEWAT = "apply_deadline_lewat"

class ScoringStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

class ScoringEvent(StrEnum):
    AMBIL = "ambil"
    SELESAI = "selesai"
    GAGAL = "gagal"
    NILAI_ULANG = "nilai_ulang"

REPORT_MAP: dict[tuple[ReportStatus, ReportEvent], ReportStatus] = {
    (ReportStatus.PENDING, ReportEvent.APPROVE): ReportStatus.APPROVED,   # T-30
    (ReportStatus.PENDING, ReportEvent.REJECT):  ReportStatus.REJECTED,   # T-31
}

CAMPAIGN_MAP: dict[tuple[CampaignStatus, CampaignEvent], CampaignStatus] = {
    (CampaignStatus.OPEN, CampaignEvent.TUTUP_MANUAL):         CampaignStatus.CLOSED,  # T-40
    (CampaignStatus.OPEN, CampaignEvent.APPLY_DEADLINE_LEWAT): CampaignStatus.CLOSED,  # T-41
}

SCORING_MAP: dict[tuple[ScoringStatus, ScoringEvent], ScoringStatus] = {
    (ScoringStatus.PENDING, ScoringEvent.AMBIL):         ScoringStatus.PROCESSING,  # T-50
    (ScoringStatus.PROCESSING, ScoringEvent.SELESAI):    ScoringStatus.DONE,        # T-51
    (ScoringStatus.PROCESSING, ScoringEvent.GAGAL):      ScoringStatus.FAILED,      # T-52
    (ScoringStatus.FAILED, ScoringEvent.NILAI_ULANG):    ScoringStatus.PENDING,     # T-53
}
```

Ketiga fungsi `apply_*` mengikuti bentuk `apply_proposal` yang sudah ada: cari di peta, lempar
`IllegalTransition` bila tidak ketemu.

- [ ] **Step 4: Perluas R1 ke keempat mesin**

`test_r1_transitions.py` menambah tiga blok parametrize dengan bentuk yang sama persis seperti
dua yang sudah ada, serta tiga penguncian jumlah:

```python
def test_r1_report_transition_count_matches_spec():
    assert len(REPORT_MAP) == 2    # T-30, T-31

def test_r1_campaign_transition_count_matches_spec():
    assert len(CAMPAIGN_MAP) == 2  # T-40, T-41

def test_r1_scoring_transition_count_matches_spec():
    assert len(SCORING_MAP) == 4   # T-50 sampai T-53
```

- [ ] **Step 5: Jalankan, pastikan hijau**

Run: `make test`
Expected: PASS. R1 kini mencakup empat mesin seperti yang dijanjikan
[regression-checklist.md](regression-checklist.md).

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add report, campaign and scoring status machines"
```

## Gerbang keluar fase 01

- [ ] `make test-unit` hijau, seluruhnya berjalan di bawah 1 detik
- [ ] `make test-regression` hijau, R1 lengkap
- [ ] Tidak ada file di `app/domain/` yang mengimpor sqlmodel, sqlalchemy, atau fastapi
- [ ] Peta transisi di `transitions.py` cocok satu-satu dengan tabel di
      [08-state-machines](../prd/08-state-machines.md)
- [ ] Keempat mesin status ada di `transitions.py`, dan R1 mencakup keempatnya

# Fase 09. Deadline dan refund simulasi

**Hasil:** jalur gagal berjalan. Proposal yang tidak terkumpul sampai `funding_deadline` menjadi
`failed`, seluruh pledge dibatalkan dengan entri `refund_out`, dan saldo escrow kembali nol.
Regression R4 hijau.

**Spec terkait:** [BR-60..BR-65](../prd/07-business-rules.md), [T-05, T-08](../prd/08-state-machines.md), [D-06](../docs/decisions.md)

## Struktur file

```
backend/app/
  models/system_clock.py
  services/clock_service.py     # baca dan ubah jam virtual
  services/expiry.py            # evaluasi lazy, refund simulasi
  api/v1/internal.py            # hanya didaftarkan saat ENV=dev
backend/tests/
  integration/test_deadline.py
  integration/test_clock_tick.py
  regression/test_r4_failure_paths.py
```

---

### Task 1: Jam virtual yang tersimpan

**Files:**
- Create: `backend/app/models/system_clock.py`, `backend/app/services/clock_service.py`, migrasi
- Test: `backend/tests/integration/test_clock_tick.py`

**Interfaces:**
- Produces: `fetch_clock(session) -> Clock` (mengembalikan `VirtualClock` bila ada offset,
  `SystemClock` bila tidak), `advance_clock(session, hari)`, `reset_clock(session)`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_clock_tick.py
from datetime import timedelta

async def test_tanpa_offset_memakai_jam_asli(db):
    from app.domain.clock import SystemClock
    from app.services.clock_service import fetch_clock
    selisih = abs((await fetch_clock(db)).now() - SystemClock().now())
    assert selisih < timedelta(seconds=2)

async def test_tick_memajukan_jam(db):
    from app.services.clock_service import fetch_clock, advance_clock
    sebelum = (await fetch_clock(db)).now()
    await advance_clock(db, hari=30)
    sesudah = (await fetch_clock(db)).now()
    assert timedelta(days=29, hours=23) < sesudah - sebelum < timedelta(days=30, hours=1)

async def test_tick_bersifat_akumulatif(db):
    from app.services.clock_service import fetch_clock, advance_clock
    sebelum = (await fetch_clock(db)).now()
    await advance_clock(db, hari=10)
    await advance_clock(db, hari=10)
    assert (await fetch_clock(db)).now() - sebelum > timedelta(days=19)

async def test_reset_mengembalikan_ke_jam_asli(db):
    from app.services.clock_service import fetch_clock, advance_clock, reset_clock
    from app.domain.clock import SystemClock
    await advance_clock(db, hari=100)
    await reset_clock(db)
    assert abs((await fetch_clock(db)).now() - SystemClock().now()) < timedelta(seconds=2)

async def test_br63_endpoint_tick_tidak_terdaftar_saat_env_prod(monkeypatch):
    from app.config import settings
    from app.main import create_app
    monkeypatch.setattr(settings, "env", "prod")
    rute = {r.path for r in create_app().routes}
    assert "/api/v1/internal/clock/tick" not in rute
```

Test terakhir menegakkan [BR-63](../prd/07-business-rules.md) secara struktural: endpointnya tidak
sekadar mengembalikan `404`, melainkan tidak pernah didaftarkan.

```python
async def test_br62_failed_dengan_pledge_aktif_tetap_direfund(
    client, db, listed_proposal, investor, clock, majukan
):
    """Proposal yang sudah failed tapi masih memegang pledge aktif wajib ikut direkonsiliasi.

    Kasus ini nyata: pledge yang diterima tepat setelah funding_deadline lewat
    membuat recompute_funding_status menulis failed sementara pledge-nya tetap
    aktif. Kalau evaluate_expiry menyaring status saja, proposal itu
    dilewati selamanya dan uangnya tidak pernah kembali.
    """
    await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                      headers=investor.headers, json={"amount": 4_000_000})
    await majukan(hari=30)

    # Paksa keadaan yang dilaporkan review f06-b: failed, tapi pledge masih aktif.
    listed_proposal.status = ProposalStatus.FAILED
    await db.flush()

    await client.get(f"/api/v1/proposals/{listed_proposal.id}")

    entri = await ambil_entri(db, listed_proposal.id)
    assert any(e.entry_type is EntryType.REFUND_OUT for e in entri), (
        "proposal failed dengan pledge aktif tidak direfund; uang investor terjebak"
    )
    assert await total_pledge_aktif(db, listed_proposal.id) == 0
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_clock_tick.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/models/system_clock.py
class SystemClockRow(SQLModel, table=True):
    """Satu baris saja. CHECK id = 1 yang memaksanya."""
    __tablename__ = "system_clock"
    __table_args__ = (CheckConstraint("id = 1", name="ck_system_clock_tunggal"),)

    id: int = Field(default=1, primary_key=True)
    virtual_now: datetime | None = None
```

```python
# backend/app/main.py (bagian pendaftaran router)
if settings.env == "dev":
    # Router internal tidak pernah ada di produksi, bukan sekadar menolak (BR-63).
    app.include_router(internal.router)
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_clock_tick.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add persisted virtual clock and dev-only tick endpoint"
```

---

### Task 2: Evaluasi deadline secara lazy

**Files:**
- Create: `backend/app/services/expiry.py`
- Test: `backend/tests/integration/test_deadline.py`

**Interfaces:**
- Produces: `evaluate_expiry(session, proposal, clock) -> None`. Dipanggil di awal setiap
  pembacaan proposal dan campaign.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_deadline.py
from app.domain.transitions import ProposalStatus as S

async def test_t05_listed_tanpa_pledge_jadi_failed_setelah_deadline(
    client, db, listed_proposal, majukan
):
    await majukan(hari=30)
    detail = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert detail["status"] == "failed"

async def test_t08_partially_funded_jadi_failed_dan_pledge_direfund(
    client, db, listed_proposal, investor, majukan
):
    await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                      headers=investor.headers, json={"amount": 4_000_000})
    await majukan(hari=30)

    detail = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert detail["status"] == "failed"

    entri = await ambil_ledger(db, listed_proposal.id)
    assert any(e.entry_type is EntryType.REFUND_OUT and e.amount == 4_000_000
               for e in entri)
    assert compute_balance(entri) == 0

async def test_proposal_funded_tidak_terpengaruh_deadline(client, db, funded_proposal,
                                                          majukan):
    await majukan(hari=365)
    detail = (await client.get(f"/api/v1/proposals/{funded_proposal.id}")).json()
    assert detail["status"] == "funded"

async def test_evaluasi_idempoten_tidak_merefund_dua_kali(
    client, db, listed_proposal, investor, majukan
):
    await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                      headers=investor.headers, json={"amount": 4_000_000})
    await majukan(hari=30)
    for _ in range(5):
        await client.get(f"/api/v1/proposals/{listed_proposal.id}")

    refund = [e for e in await ambil_ledger(db, listed_proposal.id)
              if e.entry_type is EntryType.REFUND_OUT]
    assert len(refund) == 1

async def test_br65_proposal_yang_masuk_mepet_apply_deadline_tetap_punya_jendela(
    client, db, campaign, umkm, investor, majukan, body_proposal
):
    """Proposal masuk sehari sebelum apply_deadline, lalu didanai setelahnya."""
    await majukan(hari=6)     # apply_deadline hari ke-7, funding_deadline hari ke-21
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
                            headers=umkm.headers, json=body_proposal())
    pid = res.json()["id"]

    await majukan(hari=5)     # hari ke-11, masih di dalam jendela pendanaan
    pledge = await client.post(f"/api/v1/proposals/{pid}/pledges",
                               headers=investor.headers, json={"amount": 10_000_000})
    assert pledge.status_code == 201
    assert (await client.get(f"/api/v1/proposals/{pid}")).json()["status"] == "funded"
```

Test keempat adalah yang paling penting di task ini: evaluasi lazy berjalan di **setiap**
pembacaan, jadi tanpa penjagaan idempotensi ia akan mencatat refund berkali-kali.

Test kelima membuktikan [D-16](../docs/decisions.md) benar-benar menyelesaikan masalah yang
ditemukan saat self-review spec.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_deadline.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/services/expiry.py
ACTIVE_STATUSES = {ProposalStatus.LISTED, ProposalStatus.PARTIALLY_FUNDED}

# FAILED ikut diperiksa, dan ini bukan kehati-hatian berlebihan. Pledge bisa
# masuk atau dibatalkan tepat setelah funding_deadline lewat; recompute_funding_status
# langsung menulis failed, dan pledge aktifnya tertinggal tanpa refund_out.
# Kalau fungsi ini menyaring status saja, proposal itu dilewati selamanya dan
# uang investor lain tidak pernah kembali (BR-62).
NEEDS_RECONCILIATION = ACTIVE_STATUSES | {ProposalStatus.FAILED}

async def evaluate_expiry(session, proposal, clock) -> None:
    """Dipanggil di awal setiap pembacaan proposal (D-06, BR-61).

    Idempoten: kunci idempotensi refund berasal dari pledge, jadi pembacaan
    berulang tidak pernah menghasilkan entri ganda.
    """
    if proposal.status not in NEEDS_RECONCILIATION:
        return

    campaign = await session.get(Campaign, proposal.campaign_id)
    if clock.now() < campaign.funding_deadline:
        return

    terkunci = await ambil_proposal_terkunci(session, proposal.id)
    if terkunci.status not in ACTIVE_STATUSES:
        return      # transaksi lain sudah mengurusnya

    aktif = await ambil_pledge_aktif(session, terkunci.id)
    for p in aktif:
        p.status = PledgeStatus.CANCELLED
        await record_entry(session, terkunci.id, EntryType.REFUND_OUT, p.amount,
                          idempotency_key=f"refund:{p.id}",
                          ref_type="pledge", ref_id=p.id)

    terkunci.status = apply_proposal(terkunci.status, ProposalEvent.DEADLINE_LEWAT)
    await session.flush()
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_deadline.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add lazy deadline evaluation and simulated refunds"
```

---

### Task 3: Regression R4, jalur gagal

**Files:**
- Create: `backend/tests/regression/test_r4_failure_paths.py`

- [ ] **Step 1: Tulis test**

```python
# backend/tests/regression/test_r4_failure_paths.py
"""R4: jalur-jalur yang berakhir tanpa pendanaan atau ditolak."""


async def test_r4_tidak_ada_failed_yang_masih_memegang_pledge_aktif(db):
    """Invarian, bukan skenario: diperiksa untuk semua proposal failed yang ada.

    Dua jalan menuju keadaan rusak ini sudah pernah direproduksi terhadap database
    sungguhan di review fase 06: pledge yang diterima setelah funding_deadline lewat,
    dan pembatalan yang menjatuhkan total di bawah target setelah tenggat. Keduanya
    meninggalkan pledge_in tanpa refund_out dan escrow menggantung.

    Memeriksa seluruh proposal failed, bukan satu yang diketahui, supaya jalan ketiga
    yang belum terpikirkan pun tertangkap.
    """
    gagal = (await db.scalars(
        select(Proposal).where(Proposal.status == ProposalStatus.FAILED)
    )).all()

    for p in gagal:
        aktif = await total_pledge_aktif(db, p.id)
        assert aktif == 0, (
            f"proposal {p.id} berstatus failed tapi masih memegang pledge aktif "
            f"senilai {aktif}; uang investor terjebak tanpa refund_out"
        )
import pytest

async def test_r4_deadline_lewat_merefund_seluruh_pledge(client, db, listed_proposal,
                                                         investor_a, investor_b, majukan):
    await pledge(client, investor_a, listed_proposal, 3_000_000)
    await pledge(client, investor_b, listed_proposal, 4_000_000)
    await majukan(hari=30)
    await client.get(f"/api/v1/proposals/{listed_proposal.id}")

    entri = await ambil_ledger(db, listed_proposal.id)
    refund = sum(e.amount for e in entri if e.entry_type is EntryType.REFUND_OUT)
    assert refund == 7_000_000
    assert compute_balance(entri) == 0
    await db.refresh(listed_proposal)
    assert listed_proposal.status is ProposalStatus.FAILED

async def test_r4_pledge_melebihi_sisa_menyertakan_sisa_yang_benar(client, investor,
                                                                   listed_proposal):
    await pledge(client, investor, listed_proposal, 7_000_000)
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                            headers=investor.headers, json={"amount": 5_000_000})
    assert res.status_code == 409
    assert res.json()["error"]["detail"]["remaining_amount"] == 3_000_000

async def test_r4_proposal_kedua_di_campaign_sama_ditolak(client, umkm, campaign,
                                                          body_proposal):
    await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
                      headers=umkm.headers, json=body_proposal())
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
                            headers=umkm.headers, json=body_proposal())
    assert res.status_code == 409

async def test_r4_milestone_dilangkahi_ditolak(client, umkm, funded_proposal):
    m2 = funded_proposal.milestones[1]
    res = await client.post(f"/api/v1/milestones/{m2.id}/reports",
                            headers=umkm.headers, json={"narrative": "x" * 60})
    assert res.status_code == 409

async def test_r4_bukan_lead_investor_tidak_bisa_approve(client, investor_kecil,
                                                         funded_proposal):
    m1 = funded_proposal.milestones[0]
    res = await client.post(f"/api/v1/milestones/{m1.id}/approve",
                            headers=investor_kecil.headers)
    assert res.status_code == 403

async def test_r4_proposal_funded_menolak_pledge_baru(client, investor_b, funded_proposal):
    res = await client.post(f"/api/v1/proposals/{funded_proposal.id}/pledges",
                            headers=investor_b.headers, json={"amount": 1_000_000})
    assert res.status_code == 409

async def test_r4_proposal_failed_menolak_segala_aksi(client, investor, umkm,
                                                      failed_proposal):
    assert (await client.post(f"/api/v1/proposals/{failed_proposal.id}/pledges",
            headers=investor.headers, json={"amount": 1_000_000})).status_code == 409
    m1 = failed_proposal.milestones[0]
    assert (await client.post(f"/api/v1/milestones/{m1.id}/approve",
            headers=investor.headers)).status_code == 409
```

- [ ] **Step 2: Jalankan seluruh regression**

Run: `make test-regression`
Expected: PASS, R1, R2, R2b, R3, R4, R5, R6

- [ ] **Step 3: Commit**

```bash
git add backend/tests/regression/test_r4_failure_paths.py
git commit -m "feat: add failure path regression suite"
```

## Gerbang keluar fase 09

- [ ] `make test` dan `make test-regression` hijau, keenam kelompok R lengkap
- [ ] Backend selesai: seluruh endpoint di [10-api-contract](../prd/10-api-contract.md) ada dan
      punya baris di matriks RBAC
- [ ] `ENV=prod` membuat router internal tidak terdaftar sama sekali
- [ ] Membaca proposal kedaluwarsa berkali-kali hanya menghasilkan satu refund per pledge

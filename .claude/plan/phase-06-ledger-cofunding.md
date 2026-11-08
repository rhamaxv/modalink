# Fase 06. Ledger dan co-funding

Fase paling berisiko di seluruh project, karena di sinilah uang bergerak. Tiga dari lima baris
[Review Focus](README.md) berakar di sini.

**Hasil:** beberapa investor bisa patungan mendanai satu proposal. Setiap pergerakan dana tercatat
sebagai entri ledger. Regression R2 dan R2b hijau.

**Spec terkait:** [BR-20..BR-28, BR-50..BR-55](../prd/07-business-rules.md), [D-03, D-05, D-11](../docs/decisions.md)

## Struktur file

```
backend/app/
  models/ledger.py           # LedgerEntry, enum EntryType
  models/pledge.py
  services/ledger.py         # catat(), saldo(), total_terkumpul()
  services/pledge.py         # buat_pledge, batalkan_pledge, recompute_funding_status
  api/v1/pledges.py
backend/tests/
  unit/test_ledger_saldo.py
  integration/test_pledge.py
  integration/test_pledge_bersamaan.py
  regression/test_r2_ledger.py
  regression/test_r2b_funding_status.py
```

---

### Task 1: Entri ledger yang hanya bisa ditambah

**Files:**
- Create: `backend/app/models/ledger.py`, `backend/app/services/ledger.py`, migrasi
- Test: `backend/tests/unit/test_ledger_saldo.py`, `backend/tests/integration/test_ledger.py`

**Interfaces:**
- Produces: `EntryType`, `LedgerEntry`, `EntriRingkas`,
  `hitung_saldo(entries) -> int`, `total_terkumpul(entries) -> int`,
  `catat_entri(session, proposal_id, entry_type, amount, idempotency_key, ...) -> LedgerEntry | None`,
  `total_terkumpul_proposal(session, proposal_id) -> int` (query, dipakai Task 3 dan 4),
  `total_pledge_aktif(session, proposal_id) -> int` (query, dipakai R2b)

  Dua yang terakhir adalah query, bukan fungsi murni. Penamaannya sengaja dibedakan dari
  `total_terkumpul(entries)` supaya tidak tertukar: yang satu menerima daftar entri, yang lain
  menerima sesi database.

Ini juga tempat **RF-2** dikunci di batas HTTP: nominal yang bukan integer ditolak `422`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_ledger_saldo.py
import pytest
from app.services.ledger import EntriRingkas, hitung_saldo, total_terkumpul
from app.models.ledger import EntryType as T

def e(tipe, jumlah): return EntriRingkas(entry_type=tipe, amount=jumlah)

def test_br52_saldo_dijumlahkan_dari_entri():
    entri = [e(T.PLEDGE_IN, 5_000_000), e(T.PLEDGE_IN, 5_000_000),
             e(T.DISBURSEMENT_OUT, 3_000_000)]
    assert hitung_saldo(entri) == 7_000_000

def test_br52_refund_mengurangi_saldo():
    entri = [e(T.PLEDGE_IN, 5_000_000), e(T.REFUND_OUT, 5_000_000)]
    assert hitung_saldo(entri) == 0

def test_total_terkumpul_hanya_menghitung_pledge_dikurangi_refund():
    entri = [e(T.PLEDGE_IN, 10_000_000), e(T.REFUND_OUT, 2_000_000),
             e(T.DISBURSEMENT_OUT, 4_000_000)]
    assert total_terkumpul(entri) == 8_000_000   # pencairan tidak mengurangi yang terkumpul
    assert hitung_saldo(entri) == 4_000_000

def test_saldo_kosong_adalah_nol():
    assert hitung_saldo([]) == 0
```

Perbedaan `total_terkumpul` dan `hitung_saldo` halus tapi penting: progress bar funding memakai
yang pertama, pengecekan "cukupkah dana untuk dicairkan" memakai yang kedua. Mencampurnya
membuat progress bar turun setiap kali milestone cair.

```python
# backend/tests/integration/test_ledger.py
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.ledger import EntryType, LedgerEntry
from app.services.ledger import catat_entri

async def test_br54_entri_nol_ditolak_database(db, listed_proposal):
    db.add(LedgerEntry(proposal_id=listed_proposal.id, entry_type=EntryType.PLEDGE_IN,
                       amount=0, idempotency_key="uji:1"))
    with pytest.raises(IntegrityError):
        await db.flush()

async def test_br54_entri_negatif_ditolak_database(db, listed_proposal):
    db.add(LedgerEntry(proposal_id=listed_proposal.id, entry_type=EntryType.PLEDGE_IN,
                       amount=-1, idempotency_key="uji:2"))
    with pytest.raises(IntegrityError):
        await db.flush()

async def test_br55_idempotency_key_mencegah_entri_ganda(db, listed_proposal):
    kunci = f"pledge:{listed_proposal.id}"
    pertama = await catat_entri(db, listed_proposal.id, EntryType.PLEDGE_IN,
                                5_000_000, kunci)
    kedua = await catat_entri(db, listed_proposal.id, EntryType.PLEDGE_IN,
                              5_000_000, kunci)
    assert pertama is not None
    assert kedua is None            # panggilan kedua tidak menambah apa pun
    jumlah = await db.scalar(select(func.count()).select_from(LedgerEntry)
                             .where(LedgerEntry.idempotency_key == kunci))
    assert jumlah == 1
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_ledger_saldo.py tests/integration/test_ledger.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/models/ledger.py
from enum import StrEnum
from sqlalchemy import BigInteger, CheckConstraint, Column

class EntryType(StrEnum):
    PLEDGE_IN = "pledge_in"
    REFUND_OUT = "refund_out"
    DISBURSEMENT_OUT = "disbursement_out"

class LedgerEntry(SQLModel, table=True):
    """Append-only. Tidak ada endpoint, service, atau migrasi yang boleh
    meng-UPDATE atau menghapus baris di tabel ini (BR-51)."""
    __tablename__ = "ledger_entries"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_ledger_amount_positif"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    proposal_id: UUID = Field(foreign_key="proposals.id", index=True)
    entry_type: EntryType
    amount: int = Field(sa_column=Column(BigInteger, nullable=False))
    ref_type: str
    ref_id: UUID
    actor_id: UUID | None = Field(default=None, foreign_key="users.id")
    idempotency_key: str = Field(unique=True)
    created_at: datetime
```

```python
# backend/app/services/ledger.py
MASUK = {EntryType.PLEDGE_IN}
KELUAR = {EntryType.REFUND_OUT, EntryType.DISBURSEMENT_OUT}

def hitung_saldo(entries) -> int:
    """Saldo escrow: apa yang masuk dikurangi apa yang keluar (BR-52)."""
    return sum(e.amount if e.entry_type in MASUK else -e.amount for e in entries)

def total_terkumpul(entries) -> int:
    """Dana yang terkumpul dari investor. Pencairan tidak menguranginya,
    karena yang dicairkan tetap 'pernah terkumpul'."""
    return sum(
        e.amount if e.entry_type is EntryType.PLEDGE_IN else -e.amount
        for e in entries
        if e.entry_type in {EntryType.PLEDGE_IN, EntryType.REFUND_OUT}
    )

async def catat_entri(session, proposal_id, entry_type, amount, idempotency_key,
                      ref_type="", ref_id=None, actor_id=None) -> LedgerEntry | None:
    """Mengembalikan None bila kunci idempotensi sudah pernah dipakai (BR-55)."""
    entri = LedgerEntry(proposal_id=proposal_id, entry_type=entry_type, amount=amount,
                        ref_type=ref_type, ref_id=ref_id, actor_id=actor_id,
                        idempotency_key=idempotency_key, created_at=clock.now())
    session.add(entri)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback_to_savepoint()
        return None
    return entri
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_ledger_saldo.py tests/integration/test_ledger.py -v`
Expected: PASS

- [ ] **Step 5: Tolak nominal bukan integer di batas HTTP (RF-2)**

```python
# backend/tests/integration/test_pledge_nominal.py
import pytest

@pytest.mark.parametrize("nilai", ["1e9", 1_000_000.5, "5.000.000", -1, 0,
                                   9_223_372_036_854_775_808])
async def test_rf2_nominal_tidak_sah_ditolak_422(client, investor, listed_proposal, nilai):
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                            headers=investor.headers, json={"amount": nilai})
    assert res.status_code == 422, f"nilai {nilai!r} lolos padahal seharusnya ditolak"
```

Schema Pydantic memakai `Annotated[int, Field(strict=True, gt=0, le=MAX_RUPIAH)]`.
`strict=True` yang menolak `1_000_000.5` dan `"1e9"`; tanpa itu Pydantic akan membulatkannya
diam-diam.

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add append-only ledger entries with idempotency keys"
```

---

### Task 2: Penulis tunggal status funding

**Files:**
- Create: `backend/app/services/pledge.py`
- Test: `backend/tests/integration/test_recompute.py`

**Interfaces:**
- Produces: `recompute_funding_status(session, proposal, clock) -> None`. **Satu-satunya** fungsi
  yang boleh menulis `listed`, `partially_funded`, `funded` ([D-05](../docs/decisions.md)).

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_recompute.py
from app.domain.transitions import ProposalStatus as S
from app.services.pledge import recompute_funding_status

async def test_status_mengikuti_jumlah_pledge(db, listed_proposal, investor, clock, pledge):
    await pledge(listed_proposal, investor, 4_000_000)       # diminta 10 juta
    await recompute_funding_status(db, listed_proposal, clock)
    assert listed_proposal.status is S.PARTIALLY_FUNDED

    await pledge(listed_proposal, investor, 6_000_000)
    await recompute_funding_status(db, listed_proposal, clock)
    assert listed_proposal.status is S.FUNDED

async def test_t07_semua_pledge_dibatalkan_mengembalikan_ke_listed(
    db, listed_proposal, investor, clock, pledge, batalkan
):
    p = await pledge(listed_proposal, investor, 4_000_000)
    await recompute_funding_status(db, listed_proposal, clock)
    await batalkan(p)
    await recompute_funding_status(db, listed_proposal, clock)
    assert listed_proposal.status is S.LISTED

async def test_recompute_juga_memperbarui_lead_investor(
    db, listed_proposal, investor, investor_lain, clock, pledge
):
    await pledge(listed_proposal, investor, 3_000_000)
    await pledge(listed_proposal, investor_lain, 7_000_000)
    await recompute_funding_status(db, listed_proposal, clock)
    assert listed_proposal.lead_investor_id == investor_lain.user.id
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_recompute.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/services/pledge.py
from app.domain.funding import compute_funding_status
from app.domain.lead_investor import PledgeRingkas, pick_lead_investor

async def recompute_funding_status(session, proposal, clock) -> None:
    """SATU-SATUNYA tempat status funding ditulis (D-05).

    Service lain yang mengubah pledge wajib memanggil fungsi ini di transaksi
    yang sama. Regression test R2b yang menegakkannya.
    """
    aktif = (await session.scalars(
        select(Pledge).where(Pledge.proposal_id == proposal.id,
                             Pledge.status == PledgeStatus.ACTIVE)
    )).all()

    campaign = await session.get(Campaign, proposal.campaign_id)
    total = sum(p.amount for p in aktif)

    proposal.status = compute_funding_status(
        total, proposal.requested_amount, clock.now(), campaign.funding_deadline)
    proposal.lead_investor_id = pick_lead_investor(
        [PledgeRingkas(p.investor_id, p.amount, p.created_at) for p in aktif])
    if proposal.status is ProposalStatus.FUNDED and proposal.funded_at is None:
        proposal.funded_at = clock.now()
    await session.flush()
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_recompute.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add recompute_funding_status as the single funding status writer"
```

---

### Task 3: Endpoint pledge dan pembatalan

**Files:**
- Create: `backend/app/api/v1/pledges.py`
- Test: `backend/tests/integration/test_pledge.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_pledge.py
async def test_br22_investor_mana_pun_boleh_mendanai(client, investor_lain, listed_proposal):
    """Bukan hanya pembuat campaign (D-12)."""
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                            headers=investor_lain.headers, json={"amount": 4_000_000})
    assert res.status_code == 201

async def test_br21_pledge_melebihi_sisa_ditolak_dengan_sisa_di_detail(
    client, investor, listed_proposal
):
    await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                      headers=investor.headers, json={"amount": 7_000_000})
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                            headers=investor.headers, json={"amount": 5_000_000})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pledge_melebihi_sisa"
    assert res.json()["error"]["detail"]["remaining_amount"] == 3_000_000

async def test_br27_pledge_di_bawah_minimum_ditolak(client, investor, listed_proposal):
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                            headers=investor.headers, json={"amount": 50_000})
    assert res.status_code == 422

async def test_br20_proposal_submitted_tidak_bisa_didanai(
    client, investor, submitted_proposal
):
    res = await client.post(f"/api/v1/proposals/{submitted_proposal.id}/pledges",
                            headers=investor.headers, json={"amount": 1_000_000})
    assert res.status_code in {404, 409}

async def test_br25_pledge_tidak_bisa_dibatalkan_setelah_funded(
    client, investor, funded_proposal
):
    pledge_id = funded_proposal.pledges[0].id
    res = await client.delete(f"/api/v1/pledges/{pledge_id}", headers=investor.headers)
    assert res.status_code == 409

async def test_br26_pembatalan_mencatat_refund_bukan_menghapus(
    client, db, investor, listed_proposal
):
    buat = await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                             headers=investor.headers, json={"amount": 4_000_000})
    await client.delete(f"/api/v1/pledges/{buat.json()['id']}", headers=investor.headers)

    entri = (await db.scalars(select(LedgerEntry)
             .where(LedgerEntry.proposal_id == listed_proposal.id))).all()
    tipe = [e.entry_type for e in entri]
    assert EntryType.PLEDGE_IN in tipe
    assert EntryType.REFUND_OUT in tipe
    assert len(entri) == 2          # entri pledge_in tidak dihapus

async def test_br28_umkm_dan_komunitas_tidak_punya_akses_pledge(
    client, umkm, community, listed_proposal
):
    for akun in (umkm, community):
        res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                                headers=akun.headers, json={"amount": 1_000_000})
        assert res.status_code == 403
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_pledge.py -v`
Expected: FAIL dengan `404`

- [ ] **Step 3: Implementasi minimal**

```python
async def buat_pledge(session, investor, proposal, amount, clock) -> Pledge:
    sisa = remaining_amount(await total_terkumpul_proposal(session, proposal.id),
                            proposal.requested_amount)
    if amount > sisa:
        raise ConflictError(
            "pledge_melebihi_sisa",
            f"Pledge melebihi sisa dana yang dibutuhkan, sisa {format_rupiah(sisa)}.",
            detail={"remaining_amount": sisa},
        )

    pledge = Pledge(proposal_id=proposal.id, investor_id=investor.id,
                    amount=amount, status=PledgeStatus.ACTIVE, created_at=clock.now())
    session.add(pledge)
    await session.flush()

    await catat_entri(session, proposal.id, EntryType.PLEDGE_IN, amount,
                      idempotency_key=f"pledge:{pledge.id}",
                      ref_type="pledge", ref_id=pledge.id, actor_id=investor.id)
    await recompute_funding_status(session, proposal, clock)
    return pledge
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_pledge.py -v`
Expected: PASS

- [ ] **Step 5: Perbarui RBAC_MATRIX, jalankan R5**

Run: `pytest tests/regression -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add co-funding pledges that reject amounts over the remainder"
```

---

### Task 4: Penguncian baris untuk pledge bersamaan (RF-1)

**Files:**
- Modify: `backend/app/services/pledge.py`
- Test: `backend/tests/integration/test_pledge_bersamaan.py`

Tanpa task ini, dua investor yang pledge nyaris bersamaan sama-sama membaca "sisa Rp3 juta",
sama-sama lolos pemeriksaan, dan total melampaui dana yang diminta. Pemeriksaan di Python tidak
bisa mencegahnya; penguncian baris bisa.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_pledge_bersamaan.py
"""RF-1: dua pledge bersamaan pada sisa yang sama.

Test ini memakai dua sesi database sungguhan, bukan fixture yang di-rollback,
karena yang diuji adalah perilaku penguncian antar transaksi.
"""
import asyncio
import pytest
from app.db.session import SessionLocal

async def test_rf1_dua_pledge_bersamaan_hanya_satu_yang_lolos(
    listed_proposal_tercommit, investor_a, investor_b, clock
):
    sisa = listed_proposal_tercommit.requested_amount   # belum ada pledge

    async def coba(investor):
        async with SessionLocal() as sesi:
            async with sesi.begin():
                proposal = await ambil_proposal_terkunci(sesi, listed_proposal_tercommit.id)
                try:
                    await buat_pledge(sesi, investor.user, proposal, sisa, clock)
                    return "lolos"
                except ConflictError:
                    return "ditolak"

    hasil = await asyncio.gather(coba(investor_a), coba(investor_b))
    assert sorted(hasil) == ["ditolak", "lolos"]

async def test_rf1_total_pledge_tidak_pernah_melebihi_dana_diminta(
    listed_proposal_tercommit, investor_a, investor_b, clock
):
    separuh = listed_proposal_tercommit.requested_amount // 2 + 1_000_000  # sengaja > separuh

    async def coba(investor):
        async with SessionLocal() as sesi:
            async with sesi.begin():
                proposal = await ambil_proposal_terkunci(sesi, listed_proposal_tercommit.id)
                with contextlib.suppress(ConflictError):
                    await buat_pledge(sesi, investor.user, proposal, separuh, clock)

    await asyncio.gather(coba(investor_a), coba(investor_b))

    async with SessionLocal() as sesi:
        total = await total_terkumpul_proposal(sesi, listed_proposal_tercommit.id)
    assert total <= listed_proposal_tercommit.requested_amount
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_pledge_bersamaan.py -v`
Expected: FAIL. Kedua pledge lolos dan total melampaui dana yang diminta.

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/services/pledge.py (tambahan)
async def ambil_proposal_terkunci(session, proposal_id: UUID) -> Proposal:
    """Mengunci baris proposal sampai transaksi selesai.

    Semua operasi yang membaca lalu menulis uang pada satu proposal harus lewat sini
    (RF-1, RF-4, RF-5). Tanpa kunci ini, dua request bersamaan sama-sama membaca sisa
    yang sama dan sama-sama lolos.
    """
    proposal = await session.scalar(
        select(Proposal).where(Proposal.id == proposal_id).with_for_update()
    )
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return proposal
```

Router pledge, pembatalan, dan (di fase 07) approve milestone semuanya mengambil proposal lewat
fungsi ini, bukan lewat `session.get`.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_pledge_bersamaan.py -v`
Expected: PASS

- [ ] **Step 5: Pasang pagar agar kunci tidak terlupa**

```python
# backend/tests/unit/test_pagar_penguncian.py
"""Service yang menyentuh uang wajib memakai ambil_proposal_terkunci."""
import pathlib, re, pytest

SERVICE_UANG = ["pledge.py", "milestone.py", "ledger.py"]
BASIS = pathlib.Path(__file__).parents[2] / "app" / "services"

@pytest.mark.parametrize("nama", SERVICE_UANG)
def test_service_uang_tidak_memakai_session_get_untuk_proposal(nama):
    isi = (BASIS / nama).read_text()
    assert not re.search(r"session\.get\(\s*Proposal", isi), (
        f"{nama} mengambil Proposal dengan session.get. "
        "Pakai ambil_proposal_terkunci() supaya barisnya terkunci (RF-1)."
    )
```

- [ ] **Step 6: Commit**

```bash
git commit -am "fix: lock proposal row to prevent concurrent over-pledging"
```

---

### Task 5: Lead investor berpindah saat pledge terbesar dibatalkan (RF-4)

**Files:**
- Test: `backend/tests/integration/test_lead_berpindah.py`

- [ ] **Step 1: Tulis test**

```python
# backend/tests/integration/test_lead_berpindah.py
"""RF-4: pledge terbesar dibatalkan tepat saat proposal mencapai target."""
from app.domain.transitions import ProposalStatus as S

async def test_rf4_membatalkan_pledge_terbesar_menurunkan_status_dan_memindah_lead(
    client, db, investor_a, investor_b, listed_proposal
):
    besar = await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                              headers=investor_a.headers, json={"amount": 7_000_000})
    await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                      headers=investor_b.headers, json={"amount": 3_000_000})

    await db.refresh(listed_proposal)
    assert listed_proposal.status is S.FUNDED
    assert listed_proposal.lead_investor_id == investor_a.user.id

    # Dibatalkan setelah funded harus ditolak (BR-25); ini yang melindungi RF-4.
    res = await client.delete(f"/api/v1/pledges/{besar.json()['id']}",
                              headers=investor_a.headers)
    assert res.status_code == 409

async def test_rf4_membatalkan_pledge_terbesar_sebelum_funded_memindah_lead(
    client, db, investor_a, investor_b, listed_proposal
):
    besar = await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                              headers=investor_a.headers, json={"amount": 6_000_000})
    await client.post(f"/api/v1/proposals/{listed_proposal.id}/pledges",
                      headers=investor_b.headers, json={"amount": 3_000_000})

    await client.delete(f"/api/v1/pledges/{besar.json()['id']}", headers=investor_a.headers)
    await db.refresh(listed_proposal)

    assert listed_proposal.status is S.PARTIALLY_FUNDED
    assert listed_proposal.lead_investor_id == investor_b.user.id

async def test_rf4_tidak_pernah_ada_funded_dengan_total_kurang(
    db, listed_proposal, investor_a, investor_b
):
    """Invarian: status funded berarti total == requested, tanpa kecuali."""
    await db.refresh(listed_proposal)
    if listed_proposal.status is S.FUNDED:
        total = await total_terkumpul_proposal(db, listed_proposal.id)
        assert total == listed_proposal.requested_amount
```

Test pertama menemukan sesuatu yang penting: [BR-25](../prd/07-business-rules.md) (pledge terkunci
setelah `funded`) sudah menutup sebagian besar RF-4. Yang tersisa adalah jalur sebelum `funded`,
dan itu yang diuji test kedua.

- [ ] **Step 2: Jalankan, perbaiki kalau merah**

Run: `pytest tests/integration/test_lead_berpindah.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git commit -am "feat: add lead investor reassignment when a pledge is cancelled"
```

---

### Task 6: Regression R2 dan R2b

**Files:**
- Create: `backend/tests/regression/test_r2_ledger.py`, `backend/tests/regression/test_r2b_funding_status.py`

- [ ] **Step 1: Tulis R2**

```python
# backend/tests/regression/test_r2_ledger.py
"""R2: invarian uang, diperiksa setelah setiap operasi di skenario end-to-end."""
import pytest
from app.models.ledger import EntryType, LedgerEntry
from app.services.ledger import hitung_saldo, total_terkumpul

async def periksa_invarian(db, proposal_id, requested):
    entri = (await db.scalars(select(LedgerEntry)
             .where(LedgerEntry.proposal_id == proposal_id))).all()

    assert all(e.amount > 0 for e in entri), "ada entri dengan nominal nol atau negatif"

    # BR-53: total pencairan tidak pernah melebihi dana yang terkumpul.
    cair = sum(e.amount for e in entri if e.entry_type is EntryType.DISBURSEMENT_OUT)
    assert cair <= total_terkumpul(entri), "dana cair melebihi dana terkumpul"
    assert hitung_saldo(entri) >= 0, "saldo escrow negatif"
    assert total_terkumpul(entri) <= requested, "terkumpul melebihi dana yang diminta"

    kunci = [e.idempotency_key for e in entri]
    assert len(kunci) == len(set(kunci)), "idempotency_key duplikat"

async def test_r2_invarian_bertahan_sepanjang_skenario_penuh(db, skenario_penuh):
    """Skenario memanggil periksa_invarian setelah SETIAP langkah, bukan hanya di akhir."""
    async for proposal in skenario_penuh(periksa_setelah_tiap_langkah=periksa_invarian):
        pass

async def test_r2_operasi_yang_sama_dua_kali_tidak_menambah_entri(db, funded_proposal, clock):
    sebelum = await jumlah_entri(db, funded_proposal.id)
    m = funded_proposal.milestones[0]
    await cairkan(db, m, clock)
    await cairkan(db, m, clock)      # panggilan kedua harus tidak berpengaruh
    assert await jumlah_entri(db, funded_proposal.id) == sebelum + 1

async def test_r2_tidak_ada_baris_ledger_yang_pernah_berubah(db, funded_proposal, clock):
    """BR-51: hanya INSERT. Dibandingkan lewat hash seluruh baris sebelum dan sesudah."""
    sidik_sebelum = await sidik_jari_ledger(db, funded_proposal.id)
    await cairkan(db, funded_proposal.milestones[0], clock)
    sidik_sesudah = await sidik_jari_ledger(db, funded_proposal.id)
    assert sidik_sebelum <= sidik_sesudah, "ada baris lama yang berubah atau hilang"
```

`sidik_jari_ledger` mengembalikan himpunan `(id, entry_type, amount, idempotency_key)`. Karena
himpunan lama harus tetap menjadi himpunan bagian dari yang baru, UPDATE maupun DELETE akan
tertangkap.

- [ ] **Step 2: Tulis R2b**

```python
# backend/tests/regression/test_r2b_funding_status.py
"""R2b: status funding selalu cocok dengan jumlah pledge aktif.

Ini penutup risiko dari D-05 (partially_funded sebagai status di database).
"""
import pytest
from app.domain.funding import compute_funding_status
from app.domain.transitions import ProposalStatus as S

async def periksa_konsistensi(db, proposal, clock):
    total = await total_pledge_aktif(db, proposal.id)
    campaign = await db.get(Campaign, proposal.campaign_id)
    harusnya = compute_funding_status(total, proposal.requested_amount,
                                      clock.now(), campaign.funding_deadline)
    assert proposal.status is harusnya, (
        f"status {proposal.status} tidak cocok dengan total pledge {total}; "
        f"harusnya {harusnya}. Ada kode yang menulis status di luar "
        f"recompute_funding_status() (D-05)."
    )

URUTAN_OPERASI = [
    pytest.param(["pledge_30", "pledge_70"], id="naik-sampai-penuh"),
    pytest.param(["pledge_30", "batal_30"], id="kembali-kosong"),
    pytest.param(["pledge_30", "pledge_30", "batal_30"], id="turun-sebagian"),
    pytest.param(["pledge_100"], id="langsung-penuh"),
    pytest.param(["pledge_30", "lewati_deadline"], id="gagal-di-tengah"),
]

@pytest.mark.parametrize("operasi", URUTAN_OPERASI)
async def test_r2b_status_konsisten_setelah_setiap_operasi(
    db, listed_proposal, clock, jalankan_operasi, operasi
):
    for langkah in operasi:
        await jalankan_operasi(langkah, listed_proposal)
        await db.refresh(listed_proposal)
        await periksa_konsistensi(db, listed_proposal, clock)

async def test_r2b_funded_selalu_berarti_total_sama_dengan_diminta(db, funded_proposal):
    total = await total_pledge_aktif(db, funded_proposal.id)
    assert funded_proposal.status is S.FUNDED
    assert total == funded_proposal.requested_amount
```

- [ ] **Step 3: Jalankan, pastikan hijau**

Run: `pytest tests/regression -v`
Expected: PASS, R1, R2, R2b, R5, R6

- [ ] **Step 4: Commit**

```bash
git add backend/tests/regression
git commit -m "feat: add ledger invariant and funding status regression suites"
```

## Gerbang keluar fase 06

- [ ] `make test` dan `make test-regression` hijau
- [ ] Test pledge bersamaan lolos, dan gagal kalau `with_for_update()` dihapus (dibuktikan sekali
      dengan menghapusnya sementara)
- [ ] Tidak ada service uang yang mengambil `Proposal` lewat `session.get`
- [ ] Tidak ada kolom `balance` di mana pun di skema

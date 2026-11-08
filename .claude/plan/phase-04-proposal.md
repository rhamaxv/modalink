# Fase 04. Proposal dan rencana milestone

**Hasil:** UMKM bisa submit proposal beserta rencana milestone. Seluruh validasi
[BR-10 sampai BR-18](../prd/07-business-rules.md) ditegakkan, termasuk partial unique index yang
menjaga satu proposal aktif per UMKM per campaign.

**Spec terkait:** [04-feature-umkm](../prd/04-feature-umkm.md), [09-data-model](../prd/09-data-model.md)

## Struktur file

```
backend/app/
  models/proposal.py          # Proposal + ProposalMilestone
  schemas/proposal.py
  services/proposal.py        # submit_proposal, validasi lintas baris
  api/v1/proposals.py
backend/tests/
  unit/test_proposal_rules.py
  integration/test_proposal_submit.py
  integration/test_proposal_akses.py
```

---

### Task 1: Validasi rencana milestone sebagai fungsi murni

**Files:**
- Create: `backend/app/domain/milestone_plan.py`
- Test: `backend/tests/unit/test_proposal_rules.py`

**Interfaces:**
- Produces: `validate_milestone_plan(milestones: Sequence[MilestoneDraft], requested: int) -> None`,
  dataclass `MilestoneDraft(seq, title, description, amount)`.

Validasi ini murni dan tidak butuh database, jadi ia milik `domain/`, bukan service.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/unit/test_proposal_rules.py
import pytest
from app.domain.milestone_plan import MilestoneDraft, validate_milestone_plan

def draft(seq: int, amount: int) -> MilestoneDraft:
    return MilestoneDraft(seq=seq, title=f"Tahap {seq}",
                          description="x" * 20, amount=amount)

def test_rencana_valid_lolos():
    validate_milestone_plan([draft(1, 5_000_000), draft(2, 5_000_000)], 10_000_000)

def test_br14_kurang_dari_dua_milestone_ditolak():
    with pytest.raises(ValueError, match="minimal dua"):
        validate_milestone_plan([draft(1, 10_000_000)], 10_000_000)

def test_br14_jumlah_tidak_sama_ditolak_dan_menyebut_selisihnya():
    with pytest.raises(ValueError, match="kurang Rp1.000.000"):
        validate_milestone_plan([draft(1, 5_000_000), draft(2, 4_000_000)], 10_000_000)

def test_br14_jumlah_berlebih_juga_menyebut_selisihnya():
    with pytest.raises(ValueError, match="lebih Rp2.000.000"):
        validate_milestone_plan([draft(1, 6_000_000), draft(2, 6_000_000)], 10_000_000)

def test_br15_seq_harus_berurutan_dari_satu():
    with pytest.raises(ValueError, match="berurutan"):
        validate_milestone_plan([draft(1, 5_000_000), draft(3, 5_000_000)], 10_000_000)

def test_br16_amount_nol_ditolak():
    with pytest.raises(ValueError):
        validate_milestone_plan([draft(1, 10_000_000), draft(2, 0)], 10_000_000)
```

Dua test "selisih" penting: pesan "jumlah tidak sesuai" membuat UMKM harus menghitung sendiri.
Menyebut selisihnya mengubah error jadi petunjuk.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/unit/test_proposal_rules.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/domain/milestone_plan.py
"""Validasi rencana milestone (BR-14, BR-15, BR-16). Murni, tanpa database."""
from collections.abc import Sequence
from dataclasses import dataclass
from app.domain.money import Rupiah, format_rupiah, parse_rupiah

MINIMAL_MILESTONE = 2

@dataclass(frozen=True, slots=True)
class MilestoneDraft:
    seq: int
    title: str
    description: str
    amount: Rupiah

def validate_milestone_plan(milestones: Sequence[MilestoneDraft], requested: Rupiah) -> None:
    if len(milestones) < MINIMAL_MILESTONE:
        raise ValueError("Rencana milestone harus berisi minimal dua tahap.")

    for m in milestones:
        parse_rupiah(m.amount)   # menolak nol, negatif, dan bentuk bukan integer

    urutan = [m.seq for m in milestones]
    if urutan != list(range(1, len(milestones) + 1)):
        raise ValueError("Nomor urut milestone harus berurutan mulai dari 1, tanpa lompatan.")

    total = sum(m.amount for m in milestones)
    if total < requested:
        raise ValueError(
            f"Jumlah nominal milestone kurang {format_rupiah(requested - total)} "
            f"dari dana yang diminta."
        )
    if total > requested:
        raise ValueError(
            f"Jumlah nominal milestone lebih {format_rupiah(total - requested)} "
            f"dari dana yang diminta."
        )
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/unit/test_proposal_rules.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add milestone plan validation with difference message"
```

---

### Task 2: Model proposal dan partial unique index

**Files:**
- Create: `backend/app/models/proposal.py`, migrasi manual untuk partial index
- Test: `backend/tests/integration/test_proposal_model.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_proposal_model.py
import pytest
from sqlalchemy.exc import IntegrityError
from app.domain.transitions import ProposalStatus
from app.models.proposal import Proposal

async def test_br13_umkm_tidak_bisa_punya_dua_proposal_aktif_di_campaign_sama(
    db, umkm, campaign, buat_proposal
):
    await buat_proposal(status=ProposalStatus.LISTED)
    with pytest.raises(IntegrityError):
        await buat_proposal(status=ProposalStatus.SUBMITTED)

@pytest.mark.parametrize("status_mati", [ProposalStatus.REJECTED, ProposalStatus.FAILED])
async def test_br13_proposal_yang_sudah_mati_tidak_menghalangi_pengajuan_baru(
    db, buat_proposal, status_mati
):
    await buat_proposal(status=status_mati)
    await buat_proposal(status=ProposalStatus.SUBMITTED)   # harus lolos
```

Test kedua adalah alasan index-nya **partial**: UMKM yang ditolak harus bisa mencoba lagi.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_proposal_model.py -v`
Expected: FAIL

- [ ] **Step 3: Tulis migrasi manual untuk partial index**

`alembic --autogenerate` tidak menghasilkan partial index, jadi ditulis tangan:

```python
# backend/alembic/versions/xxxx_proposals.py
def upgrade() -> None:
    # ... create_table proposals ...
    op.create_index(
        "uq_proposal_aktif_per_umkm_per_campaign",
        "proposals", ["campaign_id", "umkm_id"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('rejected', 'failed')"),
    )

def downgrade() -> None:
    op.drop_index("uq_proposal_aktif_per_umkm_per_campaign", table_name="proposals")
    # ... drop_table proposals ...
```

- [ ] **Step 4: Jalankan migrasi dan test**

Run: `alembic upgrade head && pytest tests/integration/test_proposal_model.py -v`
Expected: PASS

- [ ] **Step 5: Uji migrasi bisa dibalik**

Run: `alembic downgrade -1 && alembic upgrade head`
Expected: keduanya sukses tanpa error. Migrasi yang tidak bisa dibalik adalah jebakan yang baru
terasa saat sudah terlambat.

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add partial unique index for one active proposal per campaign"
```

---

### Task 3: Endpoint submit proposal

**Files:**
- Create: `backend/app/services/proposal.py`, `backend/app/api/v1/proposals.py`
- Test: `backend/tests/integration/test_proposal_submit.py`

**Interfaces:**
- Produces: `submit_proposal(session, umkm, campaign, body, clock) -> Proposal`. Dipakai fase 05
  untuk memicu job scoring.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_proposal_submit.py
def body_proposal(**ubah):
    isi = {
        "business_name": "Warung Kopi Mbak Sri",
        "business_profile": "Warung kopi rumahan di Jakarta Timur, berjalan 3 tahun, "
                            "2 pekerja, omzet rata-rata Rp12 juta per bulan.",
        "requested_amount": 10_000_000,
        "fund_usage_plan": "Rp6 juta mesin kopi, Rp3 juta bahan baku 3 bulan, "
                           "Rp1 juta perbaikan etalase.",
        "business_projection": "Omzet diperkirakan naik ke Rp18 juta per bulan "
                               "dalam 6 bulan setelah mesin baru dipakai.",
        "milestones": [
            {"seq": 1, "title": "Beli mesin", "description": "x" * 20, "amount": 5_000_000},
            {"seq": 2, "title": "Bahan baku", "description": "x" * 20, "amount": 5_000_000},
        ],
    }
    return isi | ubah

async def test_umkm_bisa_submit_proposal(client, umkm, campaign):
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
                            headers=umkm.headers, json=body_proposal())
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "submitted"
    assert data["scoring_status"] in {"pending", "processing", "done"}

async def test_br11_dana_melebihi_target_campaign_ditolak(client, umkm, campaign):
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(requested_amount=campaign.target_amount + 1,
                           milestones=[
                               {"seq": 1, "title": "a", "description": "x" * 20,
                                "amount": campaign.target_amount + 1}]))
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "dana_melebihi_target_campaign"

async def test_br14_jumlah_milestone_tidak_pas_ditolak_dengan_selisih(client, umkm, campaign):
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(milestones=[
            {"seq": 1, "title": "a", "description": "x" * 20, "amount": 5_000_000},
            {"seq": 2, "title": "b", "description": "x" * 20, "amount": 4_000_000},
        ]))
    assert res.status_code == 422
    assert "Rp1.000.000" in res.json()["error"]["message"]

async def test_br12_dana_di_bawah_minimum_ditolak(client, umkm, campaign):
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        json=body_proposal(requested_amount=400_000, milestones=[
            {"seq": 1, "title": "a", "description": "x" * 20, "amount": 200_000},
            {"seq": 2, "title": "b", "description": "x" * 20, "amount": 200_000},
        ]))
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "dana_di_bawah_minimum"

async def test_br13_proposal_kedua_ke_campaign_sama_ditolak_409(client, umkm, campaign):
    await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
                      headers=umkm.headers, json=body_proposal())
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
                            headers=umkm.headers, json=body_proposal())
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "proposal_aktif_sudah_ada"

async def test_br17_campaign_yang_apply_deadline_nya_lewat_menolak(
    client, umkm, campaign_kedaluwarsa
):
    res = await client.post(f"/api/v1/campaigns/{campaign_kedaluwarsa.id}/proposals",
                            headers=umkm.headers, json=body_proposal())
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pengajuan_ditutup"

async def test_br18_tidak_ada_endpoint_ubah_proposal(app):
    rute = {(m, r.path) for r in app.routes
            if getattr(r, "methods", None) for m in r.methods}
    assert ("PATCH", "/api/v1/proposals/{proposal_id}") not in rute
    assert ("PUT", "/api/v1/proposals/{proposal_id}") not in rute
```

Test terakhir menegakkan [BR-18](../prd/07-business-rules.md) secara struktural: bukan dengan
menguji perilaku endpoint, melainkan dengan memastikan endpointnya tidak pernah ada.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_proposal_submit.py -v`
Expected: FAIL dengan `404`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/services/proposal.py
from app.domain.clock import Clock
from app.domain.milestone_plan import MilestoneDraft, validate_milestone_plan
from app.domain.transitions import ProposalStatus, ScoringStatus
from app.errors import ConflictError, UnprocessableError
from app.models.campaign import Campaign, CampaignStatus

async def submit_proposal(session, umkm, campaign: Campaign, body, clock: Clock):
    if campaign.status is CampaignStatus.CLOSED or clock.now() >= campaign.apply_deadline:
        raise ConflictError("pengajuan_ditutup",
                            "Campaign ini sudah tidak menerima proposal baru.")

    if body.requested_amount > campaign.target_amount:
        raise UnprocessableError(
            "dana_melebihi_target_campaign",
            "Dana yang diminta melebihi dana target campaign.",
            detail={"target_amount": campaign.target_amount},
        )

    drafts = [MilestoneDraft(**m.model_dump()) for m in body.milestones]
    try:
        validate_milestone_plan(drafts, body.requested_amount)
    except ValueError as exc:
        raise UnprocessableError("rencana_milestone_tidak_valid", str(exc)) from None

    proposal = Proposal(..., status=ProposalStatus.SUBMITTED,
                        scoring_status=ScoringStatus.PENDING)
    session.add(proposal)
    try:
        await session.flush()
    except IntegrityError:
        # Partial unique index yang menangkapnya, bukan pemeriksaan di Python,
        # sehingga dua request bersamaan pun tetap tertangkap (BR-13).
        raise ConflictError("proposal_aktif_sudah_ada",
                            "Anda sudah punya proposal aktif di campaign ini.") from None
    ...
```

Menangkap `IntegrityError` alih-alih memeriksa dulu dengan `SELECT` disengaja: pemeriksaan lebih
dulu punya celah balapan, constraint database tidak.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_proposal_submit.py -v`
Expected: PASS

- [ ] **Step 5: Perbarui RBAC_MATRIX dan jalankan R5**

Run: `pytest tests/regression -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add proposal submission with milestone plan"
```

---

### Task 4: Aturan akses baca proposal

**Files:**
- Modify: `backend/app/api/v1/proposals.py`
- Test: `backend/tests/integration/test_proposal_akses.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_proposal_akses.py
async def test_proposal_listed_terlihat_publik(client, listed_proposal):
    assert (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).status_code == 200

async def test_proposal_submitted_tidak_terlihat_publik(client, submitted_proposal):
    assert (await client.get(f"/api/v1/proposals/{submitted_proposal.id}")).status_code == 404

async def test_proposal_submitted_terlihat_oleh_pemiliknya(client, umkm, submitted_proposal):
    res = await client.get(f"/api/v1/proposals/{submitted_proposal.id}",
                           headers=umkm.headers)
    assert res.status_code == 200

async def test_proposal_rejected_terlihat_oleh_pemilik_campaign(
    client, investor, rejected_proposal
):
    res = await client.get(f"/api/v1/proposals/{rejected_proposal.id}",
                           headers=investor.headers)
    assert res.status_code == 200

async def test_proposal_submitted_tidak_terlihat_umkm_lain(client, umkm_lain, submitted_proposal):
    res = await client.get(f"/api/v1/proposals/{submitted_proposal.id}",
                           headers=umkm_lain.headers)
    assert res.status_code == 404

async def test_daftar_publik_hanya_memuat_listed_ke_atas(
    client, listed_proposal, submitted_proposal, rejected_proposal
):
    ids = {p["id"] for p in (await client.get("/api/v1/proposals")).json()["items"]}
    assert str(listed_proposal.id) in ids
    assert str(submitted_proposal.id) not in ids
    assert str(rejected_proposal.id) not in ids
```

Perhatikan `404`, bukan `403`, untuk proposal yang tidak boleh dilihat. `403` mengonfirmasi bahwa
proposal itu ada, dan itu sendiri sudah kebocoran informasi.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_proposal_akses.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
PUBLIK = {ProposalStatus.LISTED, ProposalStatus.PARTIALLY_FUNDED,
          ProposalStatus.FUNDED, ProposalStatus.COMPLETED, ProposalStatus.FAILED}

def boleh_melihat(proposal: Proposal, campaign: Campaign, user: User | None) -> bool:
    if proposal.status in PUBLIK:
        return True
    if user is None:
        return False
    return user.id in {proposal.umkm_id, campaign.investor_id}
```

Router memanggilnya, dan melempar `NotFoundError` (bukan `ForbiddenError`) kalau `False`.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add proposal read access rules"
```

## Gerbang keluar fase 04

- [ ] `make test` dan `make test-regression` hijau
- [ ] `alembic downgrade -1 && alembic upgrade head` berhasil
- [ ] Partial unique index terpasang dan terbukti menolak proposal kedua
- [ ] Tidak ada endpoint PATCH atau PUT untuk proposal

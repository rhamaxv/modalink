# Fase 03. Campaign

**Hasil:** investor bisa membuat, mengubah, menutup, dan melihat campaign. Dua deadline
ditegakkan. `score_threshold` terkunci setelah proposal pertama masuk.

**Spec terkait:** [03-feature-investor](../prd/03-feature-investor.md), [BR-64, BR-65, BR-77](../prd/07-business-rules.md)

## Struktur file

```
backend/app/
  models/campaign.py
  schemas/campaign.py
  services/campaign.py
  api/v1/campaigns.py
backend/tests/
  integration/test_campaign.py
  unit/test_campaign_rules.py
```

---

### Task 1: Model campaign dengan dua deadline

**Files:**
- Create: `backend/app/models/campaign.py`, migrasi
- Test: `backend/tests/integration/test_campaign_model.py`

**Interfaces:**
- Produces: `Campaign`, enum `Sector`, enum `CampaignStatus`.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_campaign_model.py
import pytest
from datetime import timedelta
from sqlalchemy.exc import IntegrityError
from app.domain.clock import SystemClock
from app.models.campaign import Campaign, CampaignStatus, Sector

SEKARANG = SystemClock().now()

async def test_br64_funding_deadline_harus_setelah_apply_deadline(db, investor):
    db.add(Campaign(
        investor_id=investor.user.id, title="Modal warung", description="x" * 60,
        sector=Sector.KULINER, target_amount=50_000_000,
        apply_deadline=SEKARANG + timedelta(days=10),
        funding_deadline=SEKARANG + timedelta(days=5),   # lebih awal, harus ditolak
        score_threshold=60, status=CampaignStatus.OPEN,
    ))
    with pytest.raises(IntegrityError):
        await db.flush()

async def test_target_amount_harus_positif(db, investor):
    db.add(Campaign(
        investor_id=investor.user.id, title="x", description="x" * 60,
        sector=Sector.KULINER, target_amount=0,
        apply_deadline=SEKARANG + timedelta(days=5),
        funding_deadline=SEKARANG + timedelta(days=10),
        score_threshold=60, status=CampaignStatus.OPEN,
    ))
    with pytest.raises(IntegrityError):
        await db.flush()
```

Keduanya menguji constraint **database**, bukan validasi Python. Kalau hanya Python yang menjaga,
seed script atau migrasi data bisa menembusnya.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_campaign_model.py -v`
Expected: FAIL dengan `ModuleNotFoundError`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/models/campaign.py
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4
from sqlalchemy import BigInteger, CheckConstraint, Column
from sqlmodel import Field, SQLModel

class Sector(StrEnum):
    KULINER = "kuliner"
    KERAJINAN = "kerajinan"
    PERTANIAN = "pertanian"
    JASA = "jasa"
    RITEL = "ritel"
    TEKNOLOGI = "teknologi"

class CampaignStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"

class Campaign(SQLModel, table=True):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_campaign_target_positif"),
        CheckConstraint("score_threshold BETWEEN 0 AND 100", name="ck_campaign_threshold"),
        CheckConstraint("funding_deadline > apply_deadline", name="ck_campaign_urutan_deadline"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    investor_id: UUID = Field(foreign_key="users.id", index=True)
    title: str
    description: str
    sector: Sector = Field(index=True)
    target_amount: int = Field(sa_column=Column(BigInteger, nullable=False))
    apply_deadline: datetime
    funding_deadline: datetime
    score_threshold: int = 60
    status: CampaignStatus = Field(default=CampaignStatus.OPEN, index=True)
    created_at: datetime
```

`sa_column=Column(BigInteger)` wajib: SQLModel memetakan `int` ke `INTEGER` secara default, dan
`INTEGER` meluap di Rp2,1 miliar ([BR-50](../prd/07-business-rules.md)).

- [ ] **Step 4: Migrasi, lalu jalankan test**

Run: `alembic revision --autogenerate -m "campaigns" && alembic upgrade head && pytest tests/integration/test_campaign_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add campaign model with apply and funding deadlines"
```

---

### Task 2: Endpoint buat dan daftar campaign

**Files:**
- Create: `backend/app/schemas/campaign.py`, `backend/app/services/campaign.py`, `backend/app/api/v1/campaigns.py`
- Test: `backend/tests/integration/test_campaign.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_campaign.py
from datetime import timedelta
from app.domain.clock import SystemClock

SEKARANG = SystemClock().now()

def body_campaign(**ubah):
    isi = {
        "title": "Modal warung kopi Jakarta Timur",
        "description": "Mendanai warung kopi skala rumahan di Jakarta Timur." * 2,
        "sector": "kuliner",
        "target_amount": 50_000_000,
        "apply_deadline": (SEKARANG + timedelta(days=7)).isoformat(),
        "funding_deadline": (SEKARANG + timedelta(days=21)).isoformat(),
        "score_threshold": 60,
    }
    return isi | ubah

async def test_investor_bisa_membuat_campaign(client, investor):
    res = await client.post("/api/v1/campaigns", headers=investor.headers,
                            json=body_campaign())
    assert res.status_code == 201
    assert res.json()["status"] == "open"

async def test_br64_funding_deadline_lebih_awal_ditolak_422(client, investor):
    res = await client.post("/api/v1/campaigns", headers=investor.headers,
                            json=body_campaign(
                                funding_deadline=(SEKARANG + timedelta(days=3)).isoformat()))
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "urutan_deadline_salah"

async def test_apply_deadline_di_masa_lalu_ditolak(client, investor):
    res = await client.post("/api/v1/campaigns", headers=investor.headers,
                            json=body_campaign(
                                apply_deadline=(SEKARANG - timedelta(days=1)).isoformat()))
    assert res.status_code == 422

async def test_br05_daftar_campaign_bisa_diakses_tanpa_token(client, investor):
    await client.post("/api/v1/campaigns", headers=investor.headers, json=body_campaign())
    res = await client.get("/api/v1/campaigns")
    assert res.status_code == 200
    assert len(res.json()["items"]) == 1

async def test_daftar_campaign_urutannya_deterministik(client, investor):
    for i in range(3):
        await client.post("/api/v1/campaigns", headers=investor.headers,
                          json=body_campaign(title=f"Campaign {i}"))
    sekali = (await client.get("/api/v1/campaigns")).json()["items"]
    lagi = (await client.get("/api/v1/campaigns")).json()["items"]
    assert [c["id"] for c in sekali] == [c["id"] for c in lagi]
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_campaign.py -v`
Expected: FAIL dengan `404`

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/services/campaign.py
from app.domain.clock import Clock
from app.errors import UnprocessableError
from app.schemas.campaign import CampaignIn

def validasi_deadline(body: CampaignIn, clock: Clock) -> None:
    sekarang = clock.now()
    if body.apply_deadline <= sekarang:
        raise UnprocessableError(
            "apply_deadline_lampau", "Deadline pengajuan harus di masa depan.")
    if body.funding_deadline <= body.apply_deadline:
        raise UnprocessableError(
            "urutan_deadline_salah",
            "Deadline pendanaan harus setelah deadline pengajuan.",
            detail={"apply_deadline": body.apply_deadline.isoformat()},
        )
```

Router memanggil `validasi_deadline`, lalu menyimpan. Daftar diurut
`ORDER BY created_at DESC, id DESC` supaya deterministik.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_campaign.py -v`
Expected: PASS

- [ ] **Step 5: Tambahkan baris ke RBAC_MATRIX**

Tambahkan di `tests/regression/test_r5_rbac.py` untuk setiap endpoint baru:
`POST /api/v1/campaigns`, `GET /api/v1/campaigns`, `GET /api/v1/campaigns/{id}`,
`PATCH /api/v1/campaigns/{id}`, `POST /api/v1/campaigns/{id}/close`,
`GET /api/v1/campaigns/{id}/proposals`.

Run: `pytest tests/regression/test_r5_rbac.py -v`
Expected: PASS, termasuk `test_r5_setiap_route_punya_baris_di_matriks`

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add campaign create and list endpoints"
```

---

### Task 3: Ubah, tutup, dan kunci threshold

**Files:**
- Modify: `backend/app/api/v1/campaigns.py`, `backend/app/services/campaign.py`
- Test: `backend/tests/integration/test_campaign_update.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_campaign_update.py
async def test_br77_threshold_bisa_diubah_selama_belum_ada_proposal(client, investor, campaign):
    res = await client.patch(f"/api/v1/campaigns/{campaign.id}",
                             headers=investor.headers, json={"score_threshold": 75})
    assert res.status_code == 200
    assert res.json()["score_threshold"] == 75

async def test_br77_threshold_terkunci_setelah_proposal_pertama(
    client, investor, campaign, listed_proposal
):
    res = await client.patch(f"/api/v1/campaigns/{campaign.id}",
                             headers=investor.headers, json={"score_threshold": 20})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "threshold_terkunci"

async def test_judul_tetap_bisa_diubah_setelah_ada_proposal(
    client, investor, campaign, listed_proposal
):
    res = await client.patch(f"/api/v1/campaigns/{campaign.id}",
                             headers=investor.headers, json={"title": "Judul baru"})
    assert res.status_code == 200

async def test_t40_pemilik_bisa_menutup_campaign_manual(client, db, investor, campaign):
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/close",
                            headers=investor.headers)
    assert res.status_code == 200
    await db.refresh(campaign)
    assert campaign.status is CampaignStatus.CLOSED

async def test_t41_campaign_tertutup_sendiri_setelah_apply_deadline_lewat(
    client, db, campaign, majukan
):
    await majukan(hari=8)       # apply_deadline campaign fixture jatuh di hari ke-7
    detail = (await client.get(f"/api/v1/campaigns/{campaign.id}")).json()
    assert detail["status"] == "closed"

async def test_t40_campaign_yang_sudah_closed_menolak_penutupan_ulang(
    client, investor, campaign
):
    await client.post(f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers)
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/close",
                            headers=investor.headers)
    assert res.status_code == 409

async def test_investor_lain_tidak_bisa_mengubah_campaign(client, campaign, investor_lain):
    res = await client.patch(f"/api/v1/campaigns/{campaign.id}",
                             headers=investor_lain.headers, json={"title": "Dibajak"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "bukan_pemilik"

async def test_campaign_closed_menolak_proposal_baru(client, investor, campaign, umkm):
    await client.post(f"/api/v1/campaigns/{campaign.id}/close", headers=investor.headers)
    res = await client.post(f"/api/v1/campaigns/{campaign.id}/proposals",
                            headers=umkm.headers, json={})
    assert res.status_code == 409
```

Test keempat memakai fixture `investor_lain`: peran benar, kepemilikan salah. Ini kasus yang
paling sering lolos dari guard yang hanya memeriksa peran.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_campaign_update.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```python
# backend/app/api/deps.py (tambahan)
from app.errors import ForbiddenError, NotFoundError

async def ambil_campaign_milik_sendiri(
    campaign_id: UUID,
    user: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    if campaign.investor_id != user.id:
        raise ForbiddenError("bukan_pemilik", "Campaign ini bukan milik Anda.")
    return campaign
```

Penguncian threshold di service:

```python
async def ubah_campaign(campaign, body, session) -> Campaign:
    if body.score_threshold is not None and body.score_threshold != campaign.score_threshold:
        ada_proposal = await session.scalar(
            select(func.count()).select_from(Proposal)
            .where(Proposal.campaign_id == campaign.id)
        )
        if ada_proposal:
            # Mengubah ambang setelah penilaian berjalan membuat skor antar proposal
            # tidak lagi sebanding (BR-77).
            raise ConflictError(
                "threshold_terkunci",
                "Ambang skor tidak bisa diubah setelah ada proposal masuk.",
                detail={"jumlah_proposal": ada_proposal},
            )
        campaign.score_threshold = body.score_threshold
    ...
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add campaign update, close and threshold lock"
```

## Gerbang keluar fase 03

- [ ] `make test` dan `make test-regression` hijau
- [ ] R5 memuat baris untuk keenam endpoint campaign, termasuk kasus bukan pemilik
- [ ] Constraint `funding_deadline > apply_deadline` ada di database, bukan hanya di Python

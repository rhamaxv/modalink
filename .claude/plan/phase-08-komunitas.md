# Fase 08. Komunitas

Fase paling kecil. Nilainya bukan pada ukuran fitur, melainkan pada satu batasan yang harus
dijaga: vote **tidak pernah** mengubah status proposal.

**Hasil:** komunitas bisa vote (toggle) dan berkomentar. Daftar proposal untuk investor diurut
skor lalu vote.

**Spec terkait:** [05-feature-komunitas](../prd/05-feature-komunitas.md), [BR-30..BR-35](../prd/07-business-rules.md)

## Struktur file

```
backend/app/
  models/vote.py
  models/comment.py
  services/community.py
  api/v1/community.py
backend/tests/
  integration/test_vote.py
  integration/test_comment.py
  regression/test_r4_failure_paths.py   # ditambah baris, bukan dibuat di sini
```

---

### Task 1: Vote dengan toggle

**Files:**
- Create: `backend/app/models/vote.py`, `backend/app/api/v1/community.py`, migrasi
- Test: `backend/tests/integration/test_vote.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_vote.py
from app.domain.transitions import ProposalStatus as S

async def test_komunitas_bisa_vote(client, community, listed_proposal):
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/vote",
                            headers=community.headers)
    assert res.status_code == 200
    assert res.json() == {"voted": True, "vote_count": 1}

async def test_br32_vote_bersifat_toggle(client, community, listed_proposal):
    url = f"/api/v1/proposals/{listed_proposal.id}/vote"
    await client.post(url, headers=community.headers)
    kedua = await client.post(url, headers=community.headers)
    assert kedua.json() == {"voted": False, "vote_count": 0}

async def test_br32_satu_akun_satu_vote_ditegakkan_database(db, community, listed_proposal):
    from sqlalchemy.exc import IntegrityError
    from app.models.vote import Vote
    db.add(Vote(proposal_id=listed_proposal.id, user_id=community.user.id))
    await db.flush()
    db.add(Vote(proposal_id=listed_proposal.id, user_id=community.user.id))
    with pytest.raises(IntegrityError):
        await db.flush()

async def test_br31_vote_tidak_mengubah_status_proposal(db, client, community,
                                                        listed_proposal):
    sebelum = listed_proposal.status
    for _ in range(20):
        await client.post(f"/api/v1/proposals/{listed_proposal.id}/vote",
                          headers=community.headers)
    await db.refresh(listed_proposal)
    assert listed_proposal.status is sebelum is S.LISTED

async def test_br30_proposal_submitted_tidak_bisa_divote(client, community,
                                                         submitted_proposal):
    res = await client.post(f"/api/v1/proposals/{submitted_proposal.id}/vote",
                            headers=community.headers)
    assert res.status_code in {404, 409}

async def test_investor_dan_umkm_tidak_bisa_vote(client, investor, umkm, listed_proposal):
    for akun in (investor, umkm):
        res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/vote",
                                headers=akun.headers)
        assert res.status_code == 403
```

Test keempat terlihat berlebihan sampai seseorang menambahkan fitur "proposal populer otomatis
dipromosikan". Saat itu terjadi, test ini yang menahannya.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_vote.py -v`
Expected: FAIL dengan `404`

- [ ] **Step 3: Implementasi minimal**

```python
async def toggle_vote(session, user, proposal) -> tuple[bool, int]:
    if proposal.status not in DAPAT_DIVOTE:
        raise ConflictError("proposal_belum_terbuka",
                            "Proposal ini belum terbuka untuk dukungan publik.")

    ada = await session.scalar(select(Vote).where(
        Vote.proposal_id == proposal.id, Vote.user_id == user.id))
    if ada:
        await session.delete(ada)
        voted = False
    else:
        session.add(Vote(proposal_id=proposal.id, user_id=user.id, created_at=clock.now()))
        voted = True
    await session.flush()

    # Status proposal sengaja TIDAK disentuh di sini (BR-31). Vote adalah sinyal
    # bagi investor, bukan mekanisme promosi.
    jumlah = await session.scalar(select(func.count()).select_from(Vote)
                                  .where(Vote.proposal_id == proposal.id))
    return voted, jumlah
```

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_vote.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add community vote toggle that never changes proposal status"
```

---

### Task 2: Komentar

**Files:**
- Create: `backend/app/models/comment.py`, migrasi
- Test: `backend/tests/integration/test_comment.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_comment.py
async def test_komunitas_bisa_berkomentar(client, community, listed_proposal):
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/comments",
                            headers=community.headers,
                            json={"body": "Semoga warungnya makin ramai."})
    assert res.status_code == 201

async def test_br33_komentar_lebih_dari_500_karakter_ditolak(client, community,
                                                             listed_proposal):
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/comments",
                            headers=community.headers, json={"body": "x" * 501})
    assert res.status_code == 422

async def test_br33_komentar_kosong_ditolak(client, community, listed_proposal):
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/comments",
                            headers=community.headers, json={"body": "   "})
    assert res.status_code == 422

async def test_br34_hanya_penulis_yang_bisa_menghapus(client, community, community_lain,
                                                      listed_proposal):
    buat = await client.post(f"/api/v1/proposals/{listed_proposal.id}/comments",
                             headers=community.headers, json={"body": "Semangat."})
    cid = buat.json()["id"]
    assert (await client.delete(f"/api/v1/comments/{cid}",
                                headers=community_lain.headers)).status_code == 403
    assert (await client.delete(f"/api/v1/comments/{cid}",
                                headers=community.headers)).status_code == 204

async def test_komentar_terhapus_tidak_muncul_di_daftar(client, community, listed_proposal):
    buat = await client.post(f"/api/v1/proposals/{listed_proposal.id}/comments",
                             headers=community.headers, json={"body": "Semangat."})
    await client.delete(f"/api/v1/comments/{buat.json()['id']}", headers=community.headers)
    daftar = await client.get(f"/api/v1/proposals/{listed_proposal.id}/comments")
    assert daftar.json()["items"] == []

async def test_br05_komentar_terbaca_publik_tanpa_token(client, community, listed_proposal):
    await client.post(f"/api/v1/proposals/{listed_proposal.id}/comments",
                      headers=community.headers, json={"body": "Semangat."})
    assert (await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/comments")).status_code == 200

async def test_komentar_panjang_dengan_emoji_dihitung_per_karakter_bukan_per_byte(
    client, community, listed_proposal
):
    """500 karakter emoji adalah 2000 byte. Batas dihitung per karakter."""
    res = await client.post(f"/api/v1/proposals/{listed_proposal.id}/comments",
                            headers=community.headers, json={"body": "🙂" * 500})
    assert res.status_code == 201
```

Test terakhir menangkap bug yang mudah terjadi kalau batas dihitung dari `len(body.encode())`.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_comment.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Schema memakai `Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]`.
`CHECK length(body) BETWEEN 1 AND 500` di database sebagai lapis kedua; `length()` di Postgres
menghitung karakter, bukan byte.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_comment.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add proposal comments with a 500 character limit"
```

---

### Task 3: Urutan daftar proposal untuk investor

**Files:**
- Modify: `backend/app/api/v1/campaigns.py`
- Test: `backend/tests/integration/test_urutan_proposal.py`

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_urutan_proposal.py
async def test_diurutkan_skor_lalu_vote_lalu_waktu(client, investor, campaign,
                                                   proposal_dengan):
    rendah = await proposal_dengan(skor=55, vote=9)
    tinggi = await proposal_dengan(skor=80, vote=0)
    sedang_a = await proposal_dengan(skor=70, vote=1)
    sedang_b = await proposal_dengan(skor=70, vote=5)

    items = (await client.get(f"/api/v1/campaigns/{campaign.id}/proposals",
                              headers=investor.headers)).json()["items"]
    urutan = [p["id"] for p in items]
    assert urutan == [str(tinggi.id), str(sedang_b.id), str(sedang_a.id), str(rendah.id)]

async def test_skor_dan_vote_sama_diputus_waktu_submit(client, investor, campaign,
                                                       proposal_dengan):
    duluan = await proposal_dengan(skor=70, vote=2)
    belakangan = await proposal_dengan(skor=70, vote=2)
    items = (await client.get(f"/api/v1/campaigns/{campaign.id}/proposals",
                              headers=investor.headers)).json()["items"]
    assert [p["id"] for p in items] == [str(duluan.id), str(belakangan.id)]

async def test_urutan_stabil_antar_permintaan(client, investor, campaign, banyak_proposal):
    url = f"/api/v1/campaigns/{campaign.id}/proposals"
    sekali = [p["id"] for p in (await client.get(url, headers=investor.headers)).json()["items"]]
    lagi = [p["id"] for p in (await client.get(url, headers=investor.headers)).json()["items"]]
    assert sekali == lagi

async def test_skor_yang_dipakai_adalah_hasil_scoring_terbaru(client, investor, campaign,
                                                              proposal_discore_ulang):
    """Proposal yang pernah dinilai dua kali harus memakai skor terbaru,
    bukan yang pertama."""
    items = (await client.get(f"/api/v1/campaigns/{campaign.id}/proposals",
                              headers=investor.headers)).json()["items"]
    cocok = next(p for p in items if p["id"] == str(proposal_discore_ulang.id))
    assert cocok["total_score"] == proposal_discore_ulang.skor_terbaru
```

Test terakhir penting karena `scoring_results` append-only: query yang naif akan mengambil baris
pertama atau menjumlahkan semuanya.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_urutan_proposal.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

```sql
-- Skor terbaru per proposal lewat DISTINCT ON, bukan subquery per baris.
WITH skor_terbaru AS (
  SELECT DISTINCT ON (proposal_id) proposal_id, total_score
  FROM scoring_results
  ORDER BY proposal_id, created_at DESC
),
jumlah_vote AS (
  SELECT proposal_id, count(*) AS n FROM votes GROUP BY proposal_id
)
SELECT p.*, coalesce(s.total_score, 0) AS total_score, coalesce(v.n, 0) AS vote_count
FROM proposals p
LEFT JOIN skor_terbaru s ON s.proposal_id = p.id
LEFT JOIN jumlah_vote  v ON v.proposal_id = p.id
WHERE p.campaign_id = :campaign_id
ORDER BY total_score DESC, vote_count DESC, p.created_at ASC, p.id ASC;
```

`p.id ASC` di akhir yang membuat urutannya benar-benar deterministik. Tanpa itu, dua proposal
yang identik di seluruh kolom pengurut bisa bertukar posisi antar-request.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_urutan_proposal.py -v`
Expected: PASS

- [ ] **Step 5: Perbarui RBAC_MATRIX, jalankan seluruh regression**

Run: `pytest tests/regression -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git commit -am "feat: add deterministic proposal ordering by score then votes"
```

## Gerbang keluar fase 08

- [ ] `make test` dan `make test-regression` hijau
- [ ] Vote terbukti tidak pernah mengubah status proposal
- [ ] Urutan daftar proposal identik antar dua permintaan berturut-turut
- [ ] Komentar 500 karakter emoji diterima, 501 karakter ditolak

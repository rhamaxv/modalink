# Fase 13. Seed, README, video, dan submission

**Hasil:** demo end-to-end yang stabil, deterministik, dan bisa dijalankan tanpa jaringan.

**Spec terkait:** [01-goals-scope success metrics](../prd/01-goals-scope.md)

---

## Peringatan: endpoint seed tidak ada di produksi

`POST /internal/seed` hanya terdaftar bila `ENV=dev` (BR-63, lihat `app/main.py`), dan
`docker-compose.prod.yml` menyetel `ENV: prod`. Jadi **deployment yang dilihat juri tidak
bisa disemai lewat endpoint itu.** Tanpa jalan lain, juri membuka aplikasi kosong tanpa akun
demo, dan README yang mewajibkan akun demo jadi tidak terpenuhi: itu syarat kelayakan
submission, bukan kenyamanan.

Jangan menyalakan `ENV=dev` di server publik untuk mengakalinya. Itu sekaligus membuka
`POST /internal/clock/tick` ke internet, sehingga siapa pun bisa memajukan jam virtual dan
menggagalkan campaign yang sedang berjalan di depan juri.

Yang harus ada: **modul yang bisa dijalankan sekali di server**, misalnya
`python -m app.seed`, dipanggil pemilik project lewat
`docker compose exec backend python -m app.seed`. Logika semai hidup di satu tempat
(`app/services/seed.py` atau serupa); endpoint `POST /internal/seed` tetap ada untuk test
lokal dan memanggil logika yang sama, bukan menyalinnya.

Modul itu wajib **idempoten**: dijalankan dua kali tidak menghasilkan akun ganda atau
proposal ganda. Pemilik project akan menjalankannya di server tanpa tahu apakah ia sudah
pernah jalan, dan dua set data demo lebih buruk daripada nol.

### Task 1: Data seed yang jujur

**Files:**
- Create: `backend/app/seed/demo.py`, `backend/app/api/v1/internal.py` (endpoint seed)
- Test: `backend/tests/integration/test_seed.py`

Data seed adalah data buatan, dan itu tidak apa-apa selama **disebut apa adanya**. Yang dilarang
adalah data buatan yang menyamar sebagai nyata: testimoni, logo perusahaan, statistik pengguna.
Profil UMKM fiktif untuk demo adalah data contoh, dan halaman demo menyebutnya demikian.

- [ ] **Step 1: Tulis test yang gagal**

```python
# backend/tests/integration/test_seed.py
async def test_seed_menghasilkan_enam_proposal_dengan_kualitas_berbeda(client, db):
    await client.post("/api/v1/internal/seed")
    proposal = (await db.scalars(select(Proposal))).all()
    assert len(proposal) == 6
    status = {p.status for p in proposal}
    assert {S.LISTED, S.PARTIALLY_FUNDED, S.FUNDED, S.REJECTED} <= status

async def test_seed_idempoten(client, db):
    await client.post("/api/v1/internal/seed")
    await client.post("/api/v1/internal/seed")
    assert (await db.scalar(select(func.count()).select_from(Proposal))) == 6

async def test_seed_memakai_mock_engine_sehingga_skornya_dapat_diprediksi(client, db):
    await client.post("/api/v1/internal/seed")
    ditolak = (await db.scalars(select(Proposal)
               .where(Proposal.status == S.REJECTED))).all()
    assert len(ditolak) >= 1   # satu proposal sengaja dibuat memicu red flag kritis

async def test_seed_menandai_dirinya_sebagai_data_contoh(client):
    await client.post("/api/v1/internal/seed")
    daftar = (await client.get("/api/v1/proposals")).json()
    assert daftar["is_demo_data"] is True

async def test_invarian_ledger_bertahan_pada_data_seed(client, db):
    await client.post("/api/v1/internal/seed")
    for p in (await db.scalars(select(Proposal))).all():
        await periksa_invarian(db, p.id, p.requested_amount)
```

Test terakhir menjalankan invarian R2 terhadap data seed. Seed yang melanggar invarian adalah
cara tercepat membuat demo gagal di depan juri.

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `pytest tests/integration/test_seed.py -v`
Expected: FAIL

- [ ] **Step 3: Implementasi minimal**

Enam proposal dengan karakter berbeda, memakai penanda `MockScoringEngine` supaya skornya persis
dan demo tidak pernah berubah antar-pemutaran:

| Proposal | Penanda | Hasil yang diharapkan |
| --- | --- | --- |
| Warung Kopi Mbak Sri | `[[SCORE:82]]` | `listed`, skor tinggi |
| Kerajinan Rotan Pak Dedi | `[[SCORE:71]]` | `partially_funded`, sudah ada 1 pledge |
| Katering Bu Yanti | `[[SCORE:66]]` | `funded`, 2 investor, milestone 1 cair |
| Bengkel Las Mas Tono | `[[SCORE:61]]` | `listed`, pas di atas ambang |
| Toko Kelontong Bu Imah | `[[SCORE:48]]` | `rejected`, di bawah ambang |
| Peternakan Lele Instan | `[[RED_FLAG:critical]]` | `rejected`, proyeksi tidak realistis |

Dua proposal terakhir yang membuat demo bercerita: satu ditolak karena skor, satu karena red flag
kritis meski skornya tinggi.

- [ ] **Step 4: Jalankan test, pastikan lolos**

Run: `pytest tests/integration/test_seed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add idempotent demo seed with six proposals"
```

---

### Task 2: Skenario demo tertulis

**Files:**
- Create: `docs/skenario-demo.md`

- [ ] **Step 1: Tulis skenario**

```markdown
# Skenario Demo, 5 menit

Persiapan: `make demo` lalu `curl -XPOST localhost:8000/api/v1/internal/seed`.
`SCORING_ENGINE=mock`, jadi tidak ada ketergantungan jaringan.

| Menit | Yang ditunjukkan | Kalimat kunci |
| --- | --- | --- |
| 0:00 | Masalahnya: 6 proposal masuk ke satu campaign | "Investor menerima ini tiap minggu dan harus membaca semuanya." |
| 0:45 | Daftar proposal terurut skor AI, red flag terlihat | "Dua sudah tersaring otomatis, dan alasannya terbaca." |
| 1:30 | Buka Peternakan Lele: skor tinggi tapi red flag kritis | "AI tidak menolak karena angkanya kecil. Ia menolak karena proyeksinya tidak masuk akal, dan ia menunjukkan kutipannya." |
| 2:15 | Pledge dari dua akun investor berbeda | "Satu proposal, dua pemodal. Tidak perlu satu orang menanggung semuanya." |
| 3:00 | Proposal jadi funded, milestone 1 disetujui lead investor | "Dana tidak cair sekaligus. Tahap pertama saja." |
| 3:45 | UMKM lapor progres, lead investor menolak, UMKM revisi | "Ini yang tidak ada di platform crowdfunding biasa." |
| 4:15 | Milestone 2 cair, proposal completed, buka jejak ledger | "Setiap rupiah punya barisnya sendiri dan bisa ditelusuri." |
| 4:45 | Jalankan `make test-regression` di terminal | "Dan ini yang menjaganya tetap benar." |

## Pertanyaan yang mungkin datang

| Pertanyaan | Jawaban |
| --- | --- |
| "Uangnya benar-benar berpindah?" | Tidak. Seluruh pergerakan dana adalah pencatatan di `ledger_entries`. Payment gateway ada di roadmap, dan kami menyebutnya terus terang. |
| "Bagaimana kalau AI-nya salah?" | Ambangnya diset investor, bukan platform. Red flag selalu menyertakan kutipan buktinya. Dan kalau pemanggilan AI gagal, proposal tidak pernah ditolak, hanya menunggu dinilai ulang. |
| "Kenapa cuma lead investor yang approve?" | Supaya tidak perlu voting setiap kali satu milestone cair. Lead investor adalah pemilik pledge terbesar, dihitung otomatis. |
| "Datanya asli?" | Tidak, ini data contoh dan ditandai begitu di antarmuka. |
```

- [ ] **Step 2: Jalankan sekali dari awal, catat yang macet**

Jalankan seluruh skenario sambil memegang stopwatch. Yang macet diperbaiki, yang lambat dipotong.

- [ ] **Step 3: Commit**

```bash
git add docs/skenario-demo.md
git commit -m "docs: skenario demo 5 menit beserta pertanyaan yang mungkin datang"
```

---

### Task 3: Delivery Gate dan verifikasi akhir

**Files:**
- Create: `docs/delivery-gate.md`

Ini bukan ringkasan. Ini laporan PASS atau FAIL per aturan, dengan bukti, sesuai yang diminta
modul antislop. Laporan yang memuat satu FAIL tidak boleh dikirim.

- [ ] **Step 1: Jalankan seluruh verifikasi dan catat outputnya**

```bash
make check                       # ruff, mypy, eslint, tsc, seluruh test
make test-regression             # R1, R2, R2b, R3, R4, R5, R6
npx playwright test              # e2e
```

Tempelkan output sungguhan, bukan ringkasannya.

- [ ] **Step 2: Klik seluruh kontrol, catat satu per satu (R-35)**

Bukan "semua berfungsi", melainkan daftar seperti ini:

```
Beranda
  "Jelajahi proposal"   -> /jelajah, 6 kartu tampil, tanpa galat konsol
  "Masuk"               -> /masuk, form fokus ke kolom email
  sakelar tema          -> data-theme berganti, latar body ikut berganti
Jelajah
  kartu proposal        -> /proposal/<id>, panel skor tampil terurai
  filter sektor kuliner -> daftar menyusut jadi 2, URL berisi ?sector=kuliner
Detail proposal
  "Danai proposal ini"  -> form terbuka, sisa dana tampil sebelum diketik
  nominal > sisa        -> tombol nonaktif, peringatan muncul
  ...
```

- [ ] **Step 3: Isi Delivery Gate**

Keempat blok dari modul antislop: Hard Gate (R-02, R-03, R-17, R-18, R-23 sampai R-28, R-32
sampai R-38), Purpose-Gate (R-01, R-04, R-06 sampai R-14, R-19, R-22), Liveliness (dial dan
lever), Craftsmanship dan Quality Locks (C-1 sampai C-5, R-05, R-11, R-15, R-16, R-20, R-21,
R-29, R-30, R-31).

Setiap PASS disertai bukti. Contoh bentuk yang benar:

```
R-26 PASS: setiap tombol punya href atau onClick nyata; tidak ada kontrol mati.
           Bukti: daftar klik di langkah 2, 24 kontrol, semuanya menghasilkan aksi.
R-25 PASS: 13 pasangan warna diukur dengan pemeriksa kontras antislop, terendah 5.11:1.
           Bukti: tabel di DESIGN.md.
R-17 PASS: tidak ada angka tanpa sumber. Diuji otomatis oleh komposisi.test.tsx.
```

- [ ] **Step 4: Perbaiki setiap FAIL, lalu jalankan ulang gerbangnya**

- [ ] **Step 5: Commit**

```bash
git add docs/delivery-gate.md
git commit -m "docs: laporan Delivery Gate antislop dengan bukti per aturan"
```

---

### Task 4: Pemeriksaan akhir sebelum menyebut selesai

- [ ] `make check` hijau, outputnya ditempel di laporan
- [ ] `make test-regression` hijau, keenam kelompok R
- [ ] `make test-live` dijalankan sekali, hasilnya dicatat (boleh gagal karena kuota; kalau
      gagal, sebutkan)
- [ ] Demo dijalankan penuh tanpa jaringan dengan `SCORING_ENGINE=mock`
- [ ] Demo dijalankan penuh **dengan** Gemini sungguhan, sekali, untuk memastikan jalurnya hidup
- [ ] Tidak ada API key di repo: `git log -p | grep -iE "AIza|sk-|api[_-]?key"` tidak menemukan apa pun
- [ ] `.env.example` hanya berisi nama variabel, tanpa nilai
- [ ] Delivery Gate tidak memuat satu pun FAIL
- [ ] `README.md` berisi cara menjalankan dari repo kosong dalam lima perintah atau kurang

## Yang sengaja tidak dikerjakan, dan disebut saat pitching

Diambil dari [01-goals-scope](../prd/01-goals-scope.md), disebut sebagai roadmap, bukan
disembunyikan:

- Payment gateway dan escrow sungguhan
- Verifikasi legal dan KYC
- Impact dashboard pasca-pendanaan
- Notifikasi email
- Moderasi komentar

Menyebut batasan lebih dulu lebih kuat daripada menunggu juri menemukannya.

# Modalink

Platform crowdfunding untuk UMKM: investor membuat campaign pendanaan, UMKM mengajukan
proposal, sebuah AI menilai proposal itu, beberapa investor patungan mendanainya, dan dana
dicatat cair bertahap per milestone.

Dikerjakan untuk **Logicodix 2026**, subtema **Local MSME & Creative Economy**, oleh tim
**Onde Mande Dinamika**.

> Status dokumen ini: ditulis selama Hacking Week, mengikuti kode yang ada pada saat
> penulisan. Beberapa bagian ditandai **[ISI SEBELUM SUBMIT]** karena nilainya belum ada
> (URL deploy, akun demo) atau belum selesai dikerjakan (lihat [Yang belum
> dibangun](#yang-belum-dibangun)). Bagian itu sengaja dikosongkan, bukan diisi nilai
> contoh, supaya tidak ada yang keliru menganggapnya nyata.

## Daftar isi

- [Tim](#tim)
- [Kategori, nama, dan ringkasan produk](#kategori-nama-dan-ringkasan-produk)
- [Masalah dan target pengguna](#masalah-dan-target-pengguna)
- [Fitur utama yang berhasil diimplementasikan](#fitur-utama-yang-berhasil-diimplementasikan)
- [Yang belum dibangun](#yang-belum-dibangun)
- [Teknologi](#teknologi)
- [Arsitektur sistem dan alur data](#arsitektur-sistem-dan-alur-data)
- [Struktur repositori](#struktur-repositori)
- [Instalasi dan menjalankan aplikasi](#instalasi-dan-menjalankan-aplikasi)
- [Variabel lingkungan](#variabel-lingkungan)
- [Akun demonstrasi](#akun-demonstrasi)
- [Dokumentasi penggunaan AI](#dokumentasi-penggunaan-ai)
- [Pengujian](#pengujian)
- [Deploy](#deploy)
- [Atribusi pihak ketiga](#atribusi-pihak-ketiga)

## Tim

**Onde Mande Dinamika**

| # | Nama | Peran di pengembangan |
| --- | --- | --- |
| 1 | Janzen Firdaus Al Zam Zami | **[ISI SEBELUM SUBMIT]** |
| 2 | Rhama Damarwijaya | Ketua tim. **[ISI SEBELUM SUBMIT]** |
| 3 | Moch Hanafi Gus Ageng Manik | **[ISI SEBELUM SUBMIT]** |
| 4 | Naufal Ardallah Budianto | **[ISI SEBELUM SUBMIT]** |

Seluruh commit pada riwayat repositori ini berasal dari satu akun GitHub anggota terdaftar
(`rhamaxv`, Rhama Damarwijaya). Ini sah menurut aturan panitia, yang mensyaratkan asal commit
dari akun anggota terdaftar, bukan pemerataan jumlah commit per anggota. Pembagian kerja
nyata selama Hacking Week (ideasi dan pemetaan masalah, desain UI/UX, penulisan kode,
pengujian, video demo) tidak tercermin satu-satu dari riwayat commit, dan kolom kedua di
atas wajib diisi pemilik project sebelum submission supaya itu terlihat jelas tanpa harus
ditanyakan juri. Cara memverifikasi asal commit:

```bash
git log --format='%an <%ae>' | sort -u
```

## Kategori, nama, dan ringkasan produk

**Kategori: Web.**

**Nama aplikasi: Modalink**, gabungan "modal" dan "link". Produk ini tidak memberi modal;
ia menghubungkan pihak yang punya modal dengan pihak yang membutuhkannya, lalu menjaga
perjalanan dana di antara keduanya tetap bisa ditelusuri.

Modalink menghubungkan UMKM dengan investor melalui satu siklus: UMKM mengajukan proposal ke
sebuah campaign pendanaan, proposal itu disaring dan dinilai oleh AI, beberapa investor bisa
patungan mendanai satu proposal yang lolos, dan dana yang terkumpul dicatat cair bertahap
sesuai milestone yang diajukan UMKM dan disetujui investor.

Produk ini bukan payment gateway. Tidak ada uang sungguhan yang berpindah tangan; setiap
pergerakan dana adalah baris baru di tabel `ledger_entries`, dan ini disebutkan terus
terang, bukan disamarkan sebagai transaksi nyata.

## Masalah dan target pengguna

UMKM kesulitan mendapat modal karena investor sulit melakukan screening manual terhadap
banyak proposal dengan format berbeda-beda, dan setelah dana cair tidak ada mekanisme untuk
memverifikasi penggunaannya. UMKM yang potensial pun sering tidak terlihat karena tidak
punya akses ke jaringan investor, dan proposal mereka dinilai dengan standar yang tidak
pernah dijelaskan.

| Peran | Siapa | Yang dicari |
| --- | --- | --- |
| Investor | Individu atau institusi yang punya dana dan kriteria sektor tertentu | Proposal relevan tanpa harus membaca semuanya, dan kepastian dana dipakai sesuai rencana |
| UMKM | Pemilik usaha yang butuh modal | Akses ke investor, dan penilaian yang adil serta bisa dijelaskan |
| Komunitas | Publik yang peduli pada usaha lokal | Cara memberi dukungan tanpa harus punya uang (lihat catatan di [Yang belum dibangun](#yang-belum-dibangun): peran ini sudah ada sebagai role, tampilan komentar dan vote sudah dirancang di frontend, tapi endpoint backend-nya belum berjalan) |

## Fitur utama yang berhasil diimplementasikan

Daftar di bawah hanya memuat yang benar-benar berjalan ujung ke ujung (endpoint backend ada,
teruji, dan dipakai oleh halaman frontend), diverifikasi langsung dari
`backend/app/api/v1/` dan `frontend/app/`.

**Akun dan peran**

- Registrasi dan login dengan email dan password (hash Argon2), tiga peran pengguna:
  `investor`, `umkm`, `community` (`POST /api/v1/auth/register`, `POST
  /api/v1/auth/login`, `GET /api/v1/auth/me`).
- Autentikasi berbasis JWT yang membawa role, dipakai FastAPI dependency untuk membatasi
  endpoint per peran.
- Tema terang dan gelap, bisa dipilih manual (`ThemeToggle`).

**Investor**

- Membuat campaign pendanaan dengan sektor, dana target, dua deadline terpisah (batas
  pengajuan proposal dan batas pendanaan), dan ambang skor AI
  (`POST /api/v1/campaigns`).
- Melihat daftar campaign publik dan detail satu campaign (`GET /api/v1/campaigns`,
  `GET /api/v1/campaigns/{id}`).
- Mengubah judul, deskripsi, dan ambang skor campaign miliknya sendiri, serta menutup
  campaign secara manual (`PATCH /api/v1/campaigns/{id}`,
  `POST /api/v1/campaigns/{id}/close`).
- Melihat seluruh proposal yang masuk ke campaign miliknya, termasuk yang ditolak AI
  (`GET /api/v1/campaigns/{id}/proposals`).
- Patungan mendanai proposal yang sudah lolos penyaringan AI, dan membatalkan pledge yang
  belum cair (`POST /api/v1/proposals/{id}/pledges`,
  `DELETE /api/v1/pledges/{id}`).

**UMKM**

- Mengajukan proposal ke sebuah campaign, lengkap dengan rencana milestone pencairan dana
  (`POST /api/v1/campaigns/{id}/proposals`). Proposal langsung tersimpan dengan status
  `submitted` dan direspons `201` tanpa menunggu AI; penilaian berjalan di latar belakang.
- Meminta penilaian ulang bila penilaian sebelumnya gagal secara teknis
  (`POST /api/v1/proposals/{id}/rescore`).
- Melihat status dan hasil skor proposalnya sendiri.

**Publik / seluruh peran**

- Menjelajahi daftar proposal yang sudah lolos penyaringan (`GET /api/v1/proposals`) dan
  detail satu proposal, dengan aturan akses: proposal yang belum dinilai atau ditolak hanya
  bisa dilihat oleh pemilik proposal dan pemilik campaign (`GET /api/v1/proposals/{id}`).
- Melihat hasil penilaian AI milik satu proposal: tiga komponen skor, daftar red flag
  dengan kutipan bukti, dan ringkasan brief (`GET /api/v1/proposals/{id}/scoring`).

**Penilaian AI**

- Setiap proposal yang masuk otomatis dinilai oleh AI (Gemini, dengan `MockScoringEngine`
  deterministik sebagai pengganti saat demo atau test tidak perlu jaringan). Rincian penuh
  ada di [Dokumentasi penggunaan AI](#dokumentasi-penggunaan-ai).
- Verdict (`listed` atau `rejected`) dan total skor dihitung oleh kode backend dari
  komponen yang dikembalikan model, bukan diambil langsung dari output model.
- Kegagalan teknis pemanggilan AI (timeout, error jaringan, output tidak valid, API key
  tidak ada) tidak pernah membuat proposal otomatis tertolak; proposal tetap `submitted`
  dengan `scoring_status = failed` dan menunggu rescore manual.

**Pendanaan gotong royong dan uang**

- Beberapa investor bisa menaruh pledge pada satu proposal yang sama. Status pendanaan
  proposal (`listed` / `partially_funded` / `funded`) dihitung ulang otomatis setiap kali
  ada pledge baru atau pembatalan, lewat satu fungsi tunggal
  (`recompute_funding_status`) yang menjadi satu-satunya penulis status itu.
- Pledge yang melebihi sisa dana yang dibutuhkan ditolak dengan HTTP `409`, bukan
  dipotong otomatis; respons menyertakan sisa dana yang masih dibutuhkan.
- Investor dengan total pledge aktif terbesar pada satu proposal ditandai sebagai lead
  investor secara otomatis.
- Setiap pergerakan dana (pledge masuk, refund keluar) dicatat sebagai baris baru di tabel
  `ledger_entries` yang hanya menerima `INSERT`. Saldo tidak pernah disimpan sebagai
  kolom, selalu dihitung ulang dari penjumlahan baris.

## Yang belum dibangun

Bagian ini ada supaya README tidak melebih-lebihkan. Rencana penuh produk ada di
`.claude/prd/` dan `.claude/plan/`; yang berikut ini **didokumentasikan di spesifikasi
tapi belum punya implementasi yang berjalan** pada commit yang disebut di submission:

- **Endpoint API milestone** (`GET /api/v1/proposals/{id}/milestones`,
  `POST /api/v1/milestones/{id}/reports`, `.../approve`, `.../reject`). Aturan bisnisnya
  (jumlah minimal milestone, milestone pertama cair tanpa laporan tapi tetap butuh
  approve, milestone berikutnya butuh laporan dan baru bisa cair setelah milestone
  sebelumnya cair) sudah ditulis sebagai fungsi murni teruji di
  `backend/app/domain/milestone_plan.py` dan `milestone_rules.py`, dan rencana milestone
  sudah tersimpan saat proposal diajukan. Yang belum ada adalah endpoint untuk UMKM
  melaporkan progres dan investor menyetujui atau menolak pencairannya. Halaman frontend
  untuk melaporkan milestone (`frontend/app/umkm/milestone/[id]/lapor/page.tsx`) sudah
  dibangun dan memanggil endpoint ini, jadi saat ini halaman tersebut akan gagal memuat
  data karena endpoint-nya belum ada di backend.
- **Endpoint API komunitas** (vote dan komentar pada proposal). Komponen frontend-nya
  (`CommentForm.tsx`, `CommentList.tsx`) sudah dibangun dan sudah memanggil API, tapi
  belum ada router backend yang melayaninya.
- **Transisi otomatis proposal ke `failed` saat `funding_deadline` lewat, dan refund
  simulasinya.** Logikanya ada di `backend/app/domain/funding.py`
  (`compute_funding_status`), tapi saat ini hanya dievaluasi ulang saat ada pledge baru
  atau pembatalan pledge, bukan setiap kali proposal dibaca. Proposal yang melewati
  `funding_deadline` tanpa ada aktivitas pledge susulan tidak akan otomatis berubah
  menjadi `failed` hanya dengan dilihat.
- **Endpoint internal untuk demo** (`POST /api/v1/internal/clock/tick`,
  `.../clock/reset`, `GET /api/v1/internal/ledger/{id}`,
  `POST /api/v1/internal/seed`). Keempatnya didokumentasikan di
  `.claude/prd/10-api-contract.md` sebagai alat bantu demo untuk juri (memajukan jam
  virtual tanpa menunggu, melihat isi ledger mentah, mengisi data contoh), tapi belum
  diimplementasikan. Ini juga sebab mengapa [akun demonstrasi](#akun-demonstrasi) di
  bawah belum bisa diisi: belum ada data seed yang membuat akun itu ada.
- **Filter dan pengurutan lanjutan** pada daftar campaign dan proposal (`sector`, `page`,
  `sort`, dan endpoint `GET /api/v1/proposals/mine`). Endpoint yang berjalan saat ini
  mengembalikan daftar penuh tanpa parameter tersebut.

## Teknologi

**Backend** (`backend/`)

- [FastAPI](https://fastapi.tiangolo.com/) di atas Python 3.12, satu modular monolith
  (bukan arsitektur microservice atau queue terpisah).
- [SQLModel](https://sqlmodel.tiangolo.com/) + SQLAlchemy async, [asyncpg](https://github.com/MagicStack/asyncpg)
  sebagai driver, [Alembic](https://alembic.sqlalchemy.org/) untuk migrasi skema.
- [PostgreSQL 16](https://www.postgresql.org/) sebagai satu-satunya database.
- [PyJWT](https://pyjwt.readthedocs.io/) untuk token akses, [argon2-cffi](https://github.com/hynek/argon2-cffi)
  untuk hash password.
- [Instructor](https://python.useinstructor.com/) + [google-genai](https://github.com/googleapis/python-genai)
  untuk memanggil Gemini dengan output terstruktur yang divalidasi
  [Pydantic](https://docs.pydantic.dev/).
- Test: [pytest](https://pytest.org/) + `pytest-asyncio`, [httpx](https://www.python-httpx.org/)
  untuk memanggil aplikasi FastAPI langsung tanpa server HTTP sungguhan.
- Lint dan type check: [ruff](https://docs.astral.sh/ruff/), [mypy](https://mypy-lang.org/).

**Frontend** (`frontend/`)

- [Next.js 15](https://nextjs.org/) (App Router) dengan [React 19](https://react.dev/).
- [Tailwind CSS 3](https://tailwindcss.com/) untuk styling.
- Font [Source Sans 3](https://fonts.google.com/specimen/Source+Sans+3) lewat
  `next/font/google` (Google Fonts).
- Test: [Vitest](https://vitest.dev/) + [Testing Library](https://testing-library.com/),
  [Playwright](https://playwright.dev/) untuk end-to-end (berkas ada di `frontend/e2e/`).
- [ESLint](https://eslint.org/) dan `tsc` untuk lint dan type check.

**Layanan pihak ketiga**

- [Google Gemini](https://ai.google.dev/) (`gemini-2.5-flash`) untuk penilaian proposal
  berbasis AI. Lihat [Dokumentasi penggunaan AI](#dokumentasi-penggunaan-ai).

**Infrastruktur deploy** (disiapkan, lihat [Deploy](#deploy))

- [Docker](https://www.docker.com/) + [Docker Compose](https://docs.docker.com/compose/)
  untuk menjalankan Postgres, backend, dan frontend sebagai container terpisah.
- [Caddy 2](https://caddyserver.com/) sebagai reverse proxy, mengurus sertifikat HTTPS
  (Let's Encrypt) secara otomatis.

## Arsitektur sistem dan alur data

Backend dipecah menjadi empat lapisan yang searah: **router (API) → service → domain →
model/database**. Aturan yang ditegakkan secara konsisten di kode: logika uang dan status
tidak pernah ditulis langsung di router, dan lapisan domain adalah fungsi murni, tidak
menyentuh sesi database atau objek request sama sekali, sehingga bisa diuji tanpa database
sungguhan.

```mermaid
flowchart TB
    subgraph CLIENT["Client: browser"]
        FE["Next.js App Router<br/>halaman investor, UMKM, publik"]
    end

    subgraph API["Lapisan API, FastAPI routers (backend/app/api/v1)"]
        R_AUTH["/auth"]
        R_CAMP["/campaigns"]
        R_PROP["/proposals"]
        R_PLEDGE["/pledges"]
    end

    subgraph SVC["Lapisan service, orkestrasi + sesi database (backend/app/services)"]
        S_AUTH["auth.py"]
        S_CAMP["campaign.py"]
        S_PROP["proposal.py"]
        S_PLEDGE["pledge.py"]
        S_STATUS["status.py"]
        S_SCORE["scoring.py"]
        S_LEDGER["ledger.py"]
    end

    subgraph DOM["Lapisan domain, fungsi murni, tanpa sesi DB (backend/app/domain)"]
        D_TRANS["transitions.py<br/>peta status sebagai data"]
        D_FUND["funding.py<br/>compute_funding_status"]
        D_MONEY["money.py<br/>rupiah = integer"]
        D_VERDICT["verdict.py<br/>total + verdict dari skor AI"]
        D_MILE["milestone_plan.py<br/>milestone_rules.py"]
        D_LEAD["lead_investor.py"]
        D_CLOCK["clock.py<br/>satu-satunya sumber waktu"]
    end

    subgraph AIE["Mesin AI, di belakang protocol ScoringEngine (backend/app/ai)"]
        ENGINE["ScoringEngine (protocol)"]
        MOCK["MockScoringEngine<br/>default test & demo, tanpa jaringan"]
        GEMINI["GeminiEngine<br/>Instructor + Gemini 2.5 Flash"]
    end

    EXT_GEMINI(["Gemini API (Google)"])

    subgraph DB["PostgreSQL"]
        T_USER[("users")]
        T_CAMP[("campaigns")]
        T_PROP[("proposals +<br/>proposal_milestones")]
        T_PLEDGE[("pledges")]
        T_SCORE[("scoring_results<br/>append-only")]
        T_LEDGER[("ledger_entries<br/>append-only, INSERT saja")]
    end

    FE -- "fetch JSON, Authorization: Bearer JWT" --> R_AUTH
    FE --> R_CAMP
    FE --> R_PROP
    FE --> R_PLEDGE

    R_AUTH --> S_AUTH
    R_CAMP --> S_CAMP
    R_PROP --> S_PROP
    R_PROP -- "job penilaian di background" --> S_SCORE
    R_PLEDGE --> S_PLEDGE

    S_CAMP --> D_TRANS
    S_CAMP --> D_CLOCK
    S_PROP --> D_MILE
    S_PLEDGE --> D_FUND
    S_PLEDGE --> D_LEAD
    S_PLEDGE --> S_STATUS
    S_PLEDGE --> S_LEDGER
    S_STATUS --> D_TRANS
    S_SCORE --> D_VERDICT
    S_SCORE --> ENGINE
    ENGINE --> MOCK
    ENGINE --> GEMINI
    GEMINI -- "structured output (Pydantic)" --> EXT_GEMINI

    S_AUTH --> T_USER
    S_CAMP --> T_CAMP
    S_PROP --> T_PROP
    S_PLEDGE --> T_PLEDGE
    S_SCORE --> T_SCORE
    S_LEDGER --> T_LEDGER
```

**Alur data pada jalur utama produk:**

1. Investor membuat campaign (sektor, dana target, dua deadline, ambang skor) lewat
   `POST /campaigns`. Tersimpan sebagai baris `campaigns` dengan status `open`.
2. UMKM mengajukan proposal ke campaign itu lewat `POST
   /campaigns/{id}/proposals`, lengkap dengan rencana milestone. Baris `proposals` dan
   `proposal_milestones` tersimpan dengan status `submitted`, dan `201` langsung
   dikembalikan ke klien.
3. Tanpa membuat klien menunggu, job penilaian berjalan di latar belakang
   (`BackgroundTasks`, di balik interface `JobRunner`): memanggil `ScoringEngine`
   (`MockScoringEngine` di test/demo, `GeminiEngine` di produksi), menyimpan hasilnya
   sebagai baris baru di `scoring_results`, dan mengubah status proposal menjadi
   `listed` atau `rejected` lewat peta transisi di `transitions.py`.
4. Investor mana pun boleh menaruh pledge pada proposal yang `listed` lewat `POST
   /proposals/{id}/pledges`. Setiap pledge mengunci baris proposal
   (`SELECT ... FOR UPDATE`), mencatat entri `pledge_in` di `ledger_entries`, menghitung
   ulang lead investor, lalu memanggil `recompute_funding_status` untuk menulis status
   `partially_funded` atau `funded`. Pembatalan pledge mencatat entri `refund_out` dan
   mengulang perhitungan yang sama.
5. Siapa pun yang berhak boleh membaca hasil skor (`GET
   /proposals/{id}/scoring`): tiga komponen skor, red flag dengan kutipan bukti, dan
   brief ringkas, langsung dari baris `scoring_results` terbaru.

Status funding punya satu penulis (`recompute_funding_status`), peta transisi status
ditulis sebagai data di satu modul (bukan `if` yang tersebar di banyak service), dan
seluruh pergerakan dana adalah baris baru, tidak pernah `UPDATE`. Ketiganya ditegakkan
oleh test regresi, bukan hanya konvensi penulisan kode (lihat [Pengujian](#pengujian)).

## Struktur repositori

Repositori ini memuat backend dan frontend dalam satu repo, dipisah lewat nama folder di
direktori utama:

```
logicodix/
├── backend/    # FastAPI + PostgreSQL, lihat "Teknologi" dan "Arsitektur" di atas
├── frontend/   # Next.js, konsumen REST API backend
├── .claude/    # dokumen sumber kebenaran proyek: PRD, plan, keputusan arsitektur, skill
├── docker-compose.yml       # Postgres untuk dev dan test lokal
├── docker-compose.prod.yml  # backend + frontend + Postgres + Caddy untuk deploy
├── Caddyfile
└── Makefile    # seluruh perintah yang didokumentasikan di bawah
```

## Instalasi dan menjalankan aplikasi

### Lewat Docker Compose (jalur yang didokumentasikan proyek ini)

Prasyarat: Docker dan Docker Compose.

```bash
cp .env.example .env
# isi .env, lihat tabel "Variabel lingkungan" di bawah

make up        # menyalakan Postgres (db + db-test) lewat Docker Compose,
               # lalu menjalankan backend (uvicorn --reload) langsung di host
make migrate   # alembic upgrade head
```

`make up` menyalakan dua container Postgres (`db` untuk data pengembangan, `db-test`
untuk test, supaya menjalankan test tidak pernah menghapus data dev) dan menjalankan
backend dengan `uvicorn --reload` memakai virtualenv di host (`backend/.venv`), bukan di
dalam container. Siapkan virtualenv itu dulu bila belum ada:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Setelah backend dan database jalan, di terminal lain:

```bash
cd frontend
npm install
npm run dev     # http://localhost:3000, backend di http://localhost:8000
```

Frontend memanggil API lewat `process.env.NEXT_PUBLIC_API_URL`, dengan fallback ke path
relatif `/api/v1` bila variabel itu tidak diset. Untuk pengembangan lokal dengan frontend
dan backend di port berbeda, set:

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

di `frontend/.env.local` (belum ada di `.env.example` saat ini; lihat catatan di
[Variabel lingkungan](#variabel-lingkungan) soal `NEXT_PUBLIC_API_BASE` yang sudah
didaftarkan di sana tapi belum dibaca kode mana pun).

### Mode demo tanpa jaringan

```bash
make demo   # setara SCORING_ENGINE=mock make up: seluruh penilaian proposal
            # memakai MockScoringEngine, tidak memanggil Gemini sama sekali
```

### Perintah lain

```bash
make test             # unit + integration + regression (butuh db-test hidup)
make test-unit         # hanya lapisan domain dan unit murni
make test-regression  # hanya enam kelompok invarian; wajib hijau sebelum klaim selesai
make test-live         # memanggil Gemini sungguhan, butuh GEMINI_API_KEY, di-skip CI
make test-fe           # test frontend (vitest), butuh frontend/node_modules
make check             # ruff + mypy + eslint + tsc + seluruh test di atas
```

## Variabel lingkungan

Sesuai `.env.example` di direktori utama:

| Variabel | Dipakai untuk |
| --- | --- |
| `ENV` | `dev` atau `prod`. Menentukan apakah router internal (belum ada, lihat [Yang belum dibangun](#yang-belum-dibangun)) akan didaftarkan. |
| `DATABASE_URL` | String koneksi Postgres untuk backend, format `postgresql+asyncpg://user:pass@host:port/db`. |
| `JWT_SECRET` | Kunci penandatanganan token akses. Wajib diisi, tidak ada default. |
| `JWT_TTL_HOURS` | Umur token akses dalam jam. |
| `SCORING_ENGINE` | `mock` (default, tanpa jaringan) atau `gemini` (memanggil Gemini sungguhan). |
| `GEMINI_API_KEY` | Kunci API Google Gemini. Hanya dibaca saat `SCORING_ENGINE=gemini`. |
| `GEMINI_MODEL` | Nama model Gemini, default `gemini-2.5-flash`. |
| `GEMINI_TIMEOUT_S` | Batas waktu tunggu per pemanggilan Gemini, dalam detik. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Kredensial database Postgres untuk container `db` (data pengembangan/produksi). |
| `POSTGRES_TEST_DB` | Nama database pada container `db-test`, terpisah dari data dev. |
| `DOMAIN` | Nama domain publik, dipakai `docker-compose.prod.yml` dan `Caddyfile` untuk sertifikat HTTPS otomatis. |
| `NEXT_PUBLIC_API_BASE` | Didaftarkan di `.env.example` dan diteruskan ke image frontend saat build produksi, **tapi kode frontend saat ini membaca `NEXT_PUBLIC_API_URL`, bukan nama ini**. Selama keduanya belum disamakan, variabel ini tidak berefek; frontend produksi berjalan karena fallback path relatif `/api/v1` kebetulan benar ketika Caddy menaruh frontend dan backend di balik satu domain yang sama. |

Tidak ada API key atau kredensial yang di-hardcode di kode sumber. `.env` ada di
`.gitignore`; nilai asli hanya pernah ada di `.env` lokal dan di environment variable
pada server deploy.

## Akun demonstrasi

**[ISI SEBELUM SUBMIT: belum ada akun demo pada commit yang ditulis dokumen ini.]**

Produk ini memakai autentikasi (lihat [Variabel lingkungan](#variabel-lingkungan) dan
[Fitur](#fitur-utama-yang-berhasil-diimplementasikan)), jadi juri butuh akun untuk mencoba
peran investor dan peran UMKM. Akun itu belum dibuat, bukan belum didokumentasikan: data
seed yang membuatnya belum berjalan (lihat endpoint `POST /api/v1/internal/seed` di
[Yang belum dibangun](#yang-belum-dibangun)), jadi tidak ada kredensial sungguhan yang bisa
dituliskan di sini tanpa mengarang. README ini sengaja tidak mengisi baris
email/password dengan nilai contoh, karena kredensial palsu di repositori publik lebih
buruk daripada kolom kosong.

Sebelum submission, pemilik project wajib mengisi tabel ini dengan akun yang sungguh ada
di database produksi:

| Peran | Email | Password | Catatan |
| --- | --- | --- | --- |
| Investor | **[ISI]** | **[ISI]** | |
| UMKM | **[ISI]** | **[ISI]** | |

Cara membuatnya secara manual, sampai endpoint seed dibangun:

```bash
curl -X POST https://<domain>/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"investor-demo@example.com","password":"<password>","name":"Investor Demo","role":"investor"}'

curl -X POST https://<domain>/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"umkm-demo@example.com","password":"<password>","name":"UMKM Demo","role":"umkm"}'
```

Lalu login lewat `/masuk` di frontend, atau lewat `POST /api/v1/auth/login`, dan isi
tabel di atas dengan kredensial yang sungguh dipakai.

## Dokumentasi penggunaan AI

**Layanan dan model:** [Google Gemini](https://ai.google.dev/), model `gemini-2.5-flash`
secara default (bisa diganti lewat `GEMINI_MODEL`), dipanggil lewat
[Instructor](https://python.useinstructor.com/) supaya responsnya datang sebagai objek
Python yang sudah divalidasi Pydantic, bukan teks bebas yang diparsing manual.

**Bagian produk yang memanfaatkannya:** penilaian otomatis setiap proposal yang masuk
(`backend/app/ai/`, dipicu dari `POST /campaigns/{id}/proposals`, hasilnya dibaca lewat
`GET /proposals/{id}/scoring`). Tidak ada fitur lain di produk ini yang memanggil AI.

**Kontrak output.** Model tidak diminta mengembalikan "skor total" atau "lolos/tidak".
Yang diminta hanya tiga komponen dan daftar temuan, divalidasi lewat skema Pydantic di
`backend/app/ai/models.py`:

```python
class ProposalScore(BaseModel):
    fit_score: int = Field(ge=0, le=40)           # kecocokan dengan kriteria campaign
    data_quality_score: int = Field(ge=0, le=30)  # kelengkapan dan konsistensi isian
    impact_score: int = Field(ge=0, le=30)        # potensi dampak dana yang diminta
    red_flags: list[RedFlag] = Field(max_length=8)
    brief: Brief   # strengths, risks, recommendation
```

Tiap `RedFlag` punya `code`, `severity` (`info` / `warning` / `critical`), `message`, dan
`evidence` yaitu kutipan yang wajib berupa teks persis dari isi proposal.

**Keputusan dihitung oleh kode, bukan oleh model.** Model sama sekali tidak diminta
mengembalikan total skor atau verdict. Keduanya dihitung di `backend/app/domain/verdict.py`:

```python
total = fit_score + data_quality_score + impact_score
if any(f.severity == "critical" for f in red_flags):
    verdict = "rejected"       # red flag kritis menolak tanpa memandang total
elif total < campaign.score_threshold:
    verdict = "rejected"
else:
    verdict = "listed"
```

Bila model mengembalikan field tambahan seperti `total`, Pydantic membuangnya tanpa
dibaca. Alasannya: angka total yang dikarang langsung oleh model tidak bisa diaudit dan
tidak stabil antar pemanggilan untuk input yang sama; model menilai komponen, kode yang
memutuskan.

**Penjagaan terhadap kutipan karangan.** Sebelum hasil penilaian dipakai, setiap
`evidence` pada red flag diperiksa ulang: bila kutipannya tidak benar-benar muncul sebagai
substring di isi proposal, red flag itu dibuang (`buang_evidence_halusinasi` di
`backend/app/ai/gemini_engine.py`). Ini bisa membuat red flag kritis ikut terbuang dan
verdict berubah dari `rejected` menjadi `listed`; itu konsekuensi yang disengaja, karena
menampilkan kutipan karangan ke UMKM sebagai alasan penolakan dianggap lebih merusak
daripada melewatkan satu red flag.

**Mode kegagalan.** Error jaringan, timeout, output yang gagal lolos validasi setelah
percobaan ulang oleh Instructor, atau `GEMINI_API_KEY` yang tidak diset, semuanya
menghasilkan `scoring_status = failed` sementara status proposal tetap `submitted`.
**Tidak ada mode kegagalan teknis yang membuat proposal otomatis `rejected`**, kegagalan
infrastruktur dianggap kerusakan produk, bukan keputusan bisnis atas usaha seseorang.
UMKM atau pemilik campaign kemudian bisa memicu `POST /proposals/{id}/rescore`.

**Default tanpa jaringan.** `SCORING_ENGINE=mock` (default) memakai
`MockScoringEngine`: deterministik, dihitung dari panjang dan kelengkapan isian proposal
dibanding dana target campaign, tanpa memanggil Gemini sama sekali. Ini dipakai oleh
seluruh unit test dan integration test di repositori ini; tidak ada test yang memanggil
Gemini sungguhan kecuali satu berkas yang ditandai `@pytest.mark.live`
(`backend/tests/contract/test_gemini_scoring.py`), yang di-skip secara default dan hanya
dijalankan manual lewat `make test-live`.

**Prompt.** Disimpan sebagai berkas teks terpisah, bukan string di dalam kode Python:
`backend/app/ai/prompts/score_proposal.md`. Isinya menjelaskan peran model (menilai,
bukan memutuskan), kriteria campaign, isi proposal lengkap dengan nama field, rubrik
penilaian per komponen, dan instruksi bahwa `evidence` harus kutipan persis. Prompt
sengaja tidak memuat ambang skor campaign, supaya penilaian model tidak condong
menyesuaikan diri ke ambang itu.

## Pengujian

Dijalankan ulang saat menulis dokumen ini (9 November 2026), bukan diambil dari dokumen
rencana:

```bash
$ cd backend && PYTHONPATH=. pytest tests/unit tests/integration tests/regression -q
434 passed, 1 skipped in 17.29s
```

Rincian per kelompok:

| Kelompok | Jumlah test | Isi |
| --- | --- | --- |
| `tests/unit` | 173 passed, 1 skipped | Lapisan domain murni dan unit lain tanpa database |
| `tests/integration` | 108 passed | Jalur endpoint utama, lewat Postgres sungguhan |
| `tests/regression` | 153 passed | Enam kelompok invarian (R1 transisi status, R2 dan R2b ledger/funding, R5 RBAC, R6 kegagalan AI) |

Satu test yang di-skip bukan terkait Gemini; test itu memeriksa bahwa `clock.py` adalah
satu-satunya pemanggil jam sistem (`tests/unit/test_domain_murni.py`). `R3` dan `R4` yang
disebut di dokumen rencana sebagai kelompok regresi tambahan belum punya berkasnya; lima
kelompok di atas (R1, R2, R2b, R5, R6) adalah yang berjalan hari ini.

```bash
$ cd frontend && npm run test
Test Files  18 passed (18)
     Tests  103 passed (103)
```

Lint dan type check keduanya bersih pada commit yang sama:

```bash
$ cd backend && ruff check . && mypy app
All checks passed!
Success: no issues found in 54 source files

$ cd frontend && npx tsc --noEmit && npm run lint
✔ No ESLint warnings or errors
```

`make test-regression` adalah gerbang wajib sebelum klaim pekerjaan selesai di proyek ini;
hasil di atas adalah hasil sungguhan dari gerbang itu, dijalankan lewat Postgres 16 di
container Docker terisolasi, bukan SQLite, karena dialect keduanya berbeda untuk partial
unique index dan `CHECK` constraint yang dipakai proyek ini.

## Deploy

**[ISI SEBELUM SUBMIT: URL aplikasi yang sudah di-deploy dan bisa diakses juri lewat
browser. Belum ada pada saat dokumen ini ditulis.]**

Aturan panitia mewajibkan aplikasi web sudah di-deploy dan bisa diakses juri tanpa
pembayaran atau akses khusus. Konfigurasi untuk itu sudah ada di repositori
(`docker-compose.prod.yml`, `Caddyfile`, `backend/Dockerfile`, `frontend/Dockerfile`):
satu VPS menjalankan Postgres, backend, dan frontend sebagai container terpisah, dengan
Caddy sebagai reverse proxy yang mengurus sertifikat HTTPS otomatis lewat Let's Encrypt.
Proses deploy itu sendiri belum dijalankan pada saat dokumen ini ditulis.

| | |
| --- | --- |
| URL aplikasi | **[ISI]** |
| Status | Belum di-deploy |

## Atribusi pihak ketiga

Tidak ada template aplikasi, aset visual (gambar, ikon, dataset), atau kode pihak lain
yang disalin ke dalam repositori ini. Seluruh gambar/ikon: **tidak ada**, antarmuka
dibangun tanpa aset gambar, hanya tipografi, warna, dan tata letak (lihat `DESIGN.md`).

Framework, library, dan layanan pihak ketiga yang dipakai (lisensi open-source masing-masing,
tidak dimodifikasi):

- Backend: FastAPI, SQLModel, SQLAlchemy, asyncpg, Alembic, Pydantic, pydantic-settings,
  PyJWT, argon2-cffi, Instructor, google-genai, pytest, pytest-asyncio, httpx, ruff, mypy.
- Frontend: Next.js, React, Tailwind CSS, Vitest, Testing Library, Playwright, ESLint,
  TypeScript.
- Font: Source Sans 3 (Google Fonts, Open Font License), dimuat lewat `next/font/google`.
- Infrastruktur: Docker, Docker Compose, PostgreSQL, Caddy.
- Layanan AI: Google Gemini (`gemini-2.5-flash`) lewat API resmi Google.

Daftar versi minimum setiap dependency ada di `backend/pyproject.toml` dan
`frontend/package.json`.

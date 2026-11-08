# Rencana Implementasi Modalink

> **Untuk pekerja agentik:** SUB-SKILL WAJIB. Pakai `superpowers:subagent-driven-development`
> (disarankan) atau `superpowers:executing-plans` untuk mengerjakan rencana ini task demi task.
> Langkah ditulis dengan checkbox (`- [ ]`) supaya progresnya bisa dilacak.

**Goal:** Platform crowdfunding UMKM yang berjalan end-to-end, dari campaign dibuat sampai seluruh
milestone cair, dengan AI scoring Gemini dan pencairan bertahap yang akuntabel.

**Arsitektur:** Modular monolith FastAPI dengan lapisan `domain/` murni (tanpa DB, tanpa HTTP) yang
memegang seluruh aturan uang dan status, dibungkus `services/` untuk orkestrasi database, dan
`api/v1/` untuk HTTP serta RBAC. Frontend Next.js App Router memanggil REST. Job AI berjalan di
belakang interface `JobRunner` yang untuk sekarang berisi `InlineRunner` ([D-01](../docs/decisions.md)).

**Tech Stack:** Python 3.12, FastAPI, SQLModel, Alembic, PostgreSQL 16, Instructor, Google Gemini
`gemini-2.5-flash`, TypeScript, Next.js 15, Tailwind CSS, pytest, httpx, Vitest, Playwright,
Docker Compose.

**Spec:** [`../prd/README.md`](../prd/README.md). Rencana ini berargumen dari spec itu, jadi
keduanya dibaca bersamaan. Keputusan arsitektur yang sudah dikunci ada di
[`../docs/decisions.md`](../docs/decisions.md). Arah visual ada di [`../../DESIGN.md`](../../DESIGN.md).

---

## Global Constraints

Berlaku untuk **setiap** task di seluruh fase. Tidak diulang di tiap task.

| Batasan | Nilai persis |
| --- | --- |
| Runtime backend | Python 3.12, FastAPI, SQLModel, Alembic |
| Runtime frontend | Node 20, Next.js 15 App Router, TypeScript dengan `strict: true` |
| Database | PostgreSQL 16. Test berjalan di Postgres, tidak pernah SQLite ([D-10](../docs/decisions.md)) |
| Uang | `BIGINT` rupiah utuh. Tidak ada `float`, tidak ada `Decimal`, tidak ada sen ([D-02](../docs/decisions.md), [BR-50](../prd/07-business-rules.md)) |
| Waktu | `datetime.now()` dilarang di luar `backend/app/domain/clock.py` ([BR-60](../prd/07-business-rules.md)) |
| Ledger | `ledger_entries` hanya menerima INSERT. Tidak ada UPDATE, tidak ada DELETE ([BR-51](../prd/07-business-rules.md)) |
| Status funding | Hanya `recompute_funding_status()` yang boleh menulis `listed`, `partially_funded`, `funded` ([D-05](../docs/decisions.md)) |
| Transisi status | Semua lewat `domain/transitions.py`. Kombinasi tak sah mengembalikan `409` ([D-04](../docs/decisions.md)) |
| Skor AI | Total dijumlahkan di Python dari tiga komponen. Field `total` dari model dibuang ([BR-70](../prd/07-business-rules.md)) |
| Test dan jaringan | Tidak ada test yang memanggil Gemini kecuali bertanda `@pytest.mark.live`, di-skip default ([D-07](../docs/decisions.md)) |
| Bentuk error | `{"error": {"code", "message", "detail"}}` di semua endpoint ([10-api-contract](../prd/10-api-contract.md)) |
| Urutan daftar | Deterministik. Seri diputus `created_at` lalu `id` |
| Bahasa antarmuka | Indonesia. Istilah teknis dipakai apa adanya. Tidak ada tanda pisah em di teks antarmuka |
| Aksesibilitas | Kontras WCAG AA, seluruh UI bisa dioperasikan keyboard, indikator fokus terlihat |
| antislop | Mode DURING. Setiap penyerahan UI ditutup Delivery Gate berupa laporan PASS/FAIL dengan bukti ([D-15](../docs/decisions.md)) |

## Review Focus

Lima kelas input dan mode kegagalan yang **tersirat** di spec tapi tidak otomatis tercakup oleh
test fitur. Urutan dari yang paling mungkin menggigit pengguna sungguhan. Setiap baris sudah
dipasangkan ke task yang memiliki kodenya.

| # | Kondisi | Yang diharapkan orang waras | Dipasang di |
| --- | --- | --- | --- |
| RF-1 | Dua investor pledge nyaris bersamaan pada sisa dana yang sama | Salah satunya ditolak `409`. Total tidak pernah melampaui `requested_amount`. Butuh penguncian baris proposal | Fase 06, Task 4 |
| RF-2 | `amount` dikirim sebagai `"1e9"`, `1000000.5`, atau melebihi jangkauan `BIGINT` | `422` dengan pesan yang jelas. Tidak ada pembulatan diam-diam, tidak ada crash | Fase 06, Task 1 |
| RF-3 | Gemini mengembalikan `evidence` yang tidak ada di isi proposal (kutipan halusinasi) | Red flag itu dibuang atau ditandai, tidak pernah ditampilkan ke UMKM sebagai bukti palsu | Fase 05, Task 3 |
| RF-4 | Lead investor membatalkan pledge terbesarnya tepat saat proposal mencapai target | Status turun kembali ke `partially_funded` dan lead investor berpindah. Tidak pernah ada `funded` dengan total kurang dari target | Fase 06, Task 5 |
| RF-5 | Approve milestone terakhir dikirim dua kali nyaris bersamaan | Hanya satu `disbursement_out` dan satu transisi ke `completed` | Fase 07, Task 4 |

RF-1, RF-4, dan RF-5 semuanya berakar pada hal yang sama: operasi uang membaca lalu menulis tanpa
mengunci. Solusinya seragam, `SELECT ... FOR UPDATE` pada baris proposal, dan dipasang sekali di
fase 06 lalu dipakai ulang di fase 07.

---

## Tenggat dan prioritas

**Code freeze 14 November 2026, 23.59 WIB.** Aturan lengkapnya di
[aturan-lomba.md](../docs/aturan-lomba.md), dan wajib dibaca sebelum commit pertama.

Scope yang disepakati: **jalan penuh, kedalaman test dipangkas ke yang esensial.**

| Tetap penuh | Dipangkas |
| --- | --- |
| Keenam kelompok regression R1 sampai R6 | Integration test per-endpoint, cukup jalur kritis |
| Seluruh unit test lapisan `domain/` | Test varian yang hanya mengulang pola yang sama |
| Satu skenario Playwright end-to-end | Test komponen frontend di luar yang punya logika |
| Contract test Gemini | Pengulangan kasus yang sudah tertutup regression |

Alasannya bukan kemalasan: regression suite dan lapisan domain yang menyasar 25% bobot Software
Engineering, sementara integration test ke-tujuh untuk endpoint yang sama tidak menambah apa pun,
baik di mata juri maupun di mata pemeliharaan.

**Yang tidak boleh dipangkas sama sekali**, karena menentukan submission diterima atau tidak:
deploy yang bisa diakses juri, README dengan isi yang dipatok panitia, video demo 3 sampai 5
menit, dan surat orisinalitas bermaterai.

## Urutan fase

Fase dikerjakan berurutan. **Fase berikutnya tidak dimulai sebelum regression suite fase
sebelumnya hijau** ([01-goals-scope](../prd/01-goals-scope.md)).

| Fase | Isi | Hasil yang bisa diuji |
| --- | --- | --- |
| [00](phase-00-fondasi.md) | Scaffold repo, Docker Compose, config, Makefile, CI | `make up` menyalakan Postgres dan backend, `GET /health` hijau |
| [01](phase-01-domain-murni.md) | `money.py`, `clock.py`, `transitions.py` | Matriks transisi lengkap (R1) hijau tanpa database sama sekali |
| [02](phase-02-auth-rbac.md) | Users, register, login, JWT, role guard | Matriks RBAC (R5) hijau |
| [03](phase-03-campaign.md) | CRUD campaign, dua deadline | Investor bisa membuat dan menutup campaign |
| [04](phase-04-proposal.md) | Submit proposal beserta milestone, validasi | UMKM bisa submit, validasi BR-10 sampai BR-18 ditegakkan |
| [05](phase-05-ai-scoring.md) | `ScoringEngine`, mock, Gemini, `JobRunner` | Proposal masuk langsung mendapat skor dan brief (R6 hijau) |
| [06](phase-06-ledger-cofunding.md) | Ledger, pledge, lead investor, status funding | Co-funding berjalan, invarian uang (R2, R2b) hijau |
| [07](phase-07-milestone.md) | Laporan progres, approve, reject, pencairan | Flow `funded` sampai `completed` berjalan (R3 hijau) |
| [08](phase-08-komunitas.md) | Vote dan komentar | Komunitas bisa vote dan berkomentar |
| [09](phase-09-deadline-refund.md) | Deadline lazy, refund simulasi, jam virtual | Jalur gagal berjalan (R4 hijau) |
| [10](phase-10-frontend-fondasi.md) | Next.js, token `DESIGN.md`, api client, auth, tema | Login jalan, tema terang dan gelap keduanya benar |
| [11](phase-11-frontend-alur.md) | Halaman campaign, proposal, explore, funding, milestone | Seluruh flow bisa dijalankan lewat browser |
| [12](phase-12-deploy.md) | Dockerfile produksi, compose, Caddy, deploy ke VPS | Aplikasi terbuka dari browser dengan HTTPS |
| [13](phase-13-submission.md) | Seed, README lomba, video demo, surat orisinalitas | Seluruh berkas submission siap dikirim |

Dokumen pendamping:

- [testing-strategy.md](testing-strategy.md) — empat lapis test, kapan memakai yang mana
- [regression-checklist.md](regression-checklist.md) — R1 sampai R6, gerbang wajib sebelum klaim selesai

## Definisi selesai, berlaku untuk setiap task

Sebuah task belum selesai sampai **semuanya** benar:

1. Test yang ditulis lebih dulu memang pernah merah karena alasan yang benar.
2. Test itu sekarang hijau.
3. Seluruh regression suite masih hijau: `make test-regression`.
4. `make check` lolos (ruff, mypy, eslint, tsc, seluruh test).
5. Kalau task menyentuh UI, Delivery Gate antislop dijalankan dan laporannya disertakan.
6. Commit dibuat dengan format yang dipatok panitia: `feat: reject pledge that exceeds the
   remaining amount`. Satu kalimat, bahasa Inggris, tanpa scope, tanpa baris `Co-Authored-By`,
   dan tanpa awalan `test`. Lihat [aturan-lomba.md](../docs/aturan-lomba.md).

Klaim "sudah selesai" tanpa output perintah di atas adalah klaim tanpa bukti.

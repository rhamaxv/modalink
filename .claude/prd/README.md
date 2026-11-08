# PRD Modalink

Spesifikasi produk, dipecah per topik supaya tiap file muat dibaca sekali duduk dan bisa diubah
tanpa menyentuh yang lain.

Dokumen ini adalah **spec**, bukan rencana kerja. Urutan pengerjaan ada di `../plan/README.md`.

## Daftar isi

| File | Isi | Dibaca saat |
| --- | --- | --- |
| [00-overview.md](00-overview.md) | Masalah, solusi, target pengguna, nilai unik | Onboarding, menulis pitch |
| [01-goals-scope.md](01-goals-scope.md) | Tujuan produk, non-goals, success metrics | Memutuskan sesuatu masuk scope atau tidak |
| [02-personas-user-stories.md](02-personas-user-stories.md) | Tiga peran dan user story per peran | Menulis acceptance criteria |
| [03-feature-investor.md](03-feature-investor.md) | Modul investor | Mengerjakan campaign, pledge, approve |
| [04-feature-umkm.md](04-feature-umkm.md) | Modul UMKM | Mengerjakan submit proposal, laporan milestone |
| [05-feature-komunitas.md](05-feature-komunitas.md) | Modul komunitas | Mengerjakan vote dan komentar |
| [06-feature-ai.md](06-feature-ai.md) | Modul AI dari sisi produk | Memahami apa yang dilihat pengguna dari AI |
| [07-business-rules.md](07-business-rules.md) | Semua aturan bisnis, satu per satu bernomor | Menulis validasi dan test |
| [08-state-machines.md](08-state-machines.md) | Matriks transisi lengkap | Menyentuh status apa pun |
| [09-data-model.md](09-data-model.md) | Entitas, kolom, constraint database | Menulis model dan migrasi |
| [10-api-contract.md](10-api-contract.md) | Endpoint, request, response, kode error | Menulis router atau api client |
| [11-ai-scoring-spec.md](11-ai-scoring-spec.md) | Rubrik skor, schema output, prompt, fallback | Menyentuh scoring |
| [12-non-functional.md](12-non-functional.md) | Keamanan, performa, aksesibilitas, bahasa | Review sebelum rilis |

## Cara membaca nomor aturan

Aturan bisnis diberi nomor `BR-xx` dan dirujuk langsung dari nama test. Kalau sebuah aturan
berubah, cari nomornya di `backend/tests/` dan perbarui testnya di baris yang sama.

Transisi status diberi nomor `T-xx`. Setiap `T-xx` wajib punya satu kasus di regression test R1,
baik untuk jalur yang diizinkan maupun yang ditolak.

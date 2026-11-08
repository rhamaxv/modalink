# 12. Kebutuhan Non-Fungsional

## Keamanan

| Hal | Aturan |
| --- | --- |
| Password | argon2, tidak pernah dikembalikan API, tidak pernah masuk log |
| JWT | HS256, masa berlaku 24 jam, berisi `sub` dan `role` |
| Role | Diverifikasi ulang terhadap database tiap request, bukan dipercaya dari token ([BR-04](07-business-rules.md)) |
| Rahasia | Hanya dari environment variable. Tidak ada API key di repo, termasuk di file contoh |
| Input | Divalidasi Pydantic di batas HTTP. Query database selalu lewat SQLModel, tidak ada string SQL yang dirakit |
| Kepemilikan | Setiap endpoint yang menyentuh sumber daya memeriksa kepemilikan, bukan hanya peran |

Poin terakhir sering terlewat: peran `investor` yang benar bukan berarti investor **itu** boleh
menyentuh pledge investor lain. Regression test R5 menguji keduanya.

## Performa

Target untuk demo, bukan untuk produksi:

| Operasi | Target |
| --- | --- |
| Endpoint baca biasa | di bawah 200 ms pada data seed |
| `POST /proposals` | di bawah 300 ms, karena scoring berjalan di background |
| Daftar proposal terurut skor | di bawah 400 ms untuk 100 proposal |
| Scoring Gemini | di bawah 15 detik, timeout di 20 detik |

Yang perlu dijaga agar target itu bertahan: skor terbaru per proposal diambil lewat index
`(proposal_id, created_at DESC)`, dan jumlah vote serta total pledge dihitung lewat agregat
dengan `GROUP BY`, bukan dengan query per baris di dalam loop.

## Aksesibilitas

Mengikuti `DESIGN.md` dan modul `antislop:antislop-human`. Yang tidak bisa ditawar:

- Kontras teks memenuhi WCAG AA. Tabel kontras yang sudah diukur ada di `DESIGN.md`.
- Seluruh antarmuka bisa dioperasikan dengan keyboard: `Tab` berurutan sesuai urutan visual,
  `Enter` dan `Space` mengaktifkan tombol, `Escape` menutup dialog.
- Setiap elemen yang menerima fokus punya indikator fokus yang terlihat jelas.
- Form punya `label` yang terhubung, dan pesan error terhubung lewat `aria-describedby`.
- Status tidak pernah disampaikan oleh warna saja. Selalu ada teks pendampingnya.

Poin terakhir penting untuk produk ini: `funded` dan `failed` tidak boleh dibedakan hanya oleh
hijau dan merah.

## Responsif

- Tidak ada scroll horizontal di lebar berapa pun.
- Target sentuh minimal 44 px.
- Tabel padat (daftar proposal, riwayat ledger) berubah menjadi kartu di bawah 640 px, bukan
  dibiarkan melebar dan terpotong.

## Observability

Cukup untuk menjelaskan kegagalan saat demo, tidak lebih:

- Log terstruktur JSON, satu baris per request, memuat metode, path, status, durasi, dan `user_id`.
- Setiap pemanggilan Gemini dicatat: model, durasi, jumlah token, dan hasil validasi. Isi proposal
  **tidak** ikut dicatat.
- `GET /health` memeriksa koneksi database.
- Setiap entri ledger sudah menjadi jejak audit tersendiri, jadi tidak perlu tabel audit terpisah.

## Bahasa

Antarmuka berbahasa Indonesia. Istilah teknis yang sudah lazim dipakai apa adanya: campaign,
pledge, milestone, dashboard. Jangan diterjemahkan paksa.

Pesan error ditujukan ke pengguna, bukan ke programmer. "Pledge melebihi sisa dana yang
dibutuhkan, sisa Rp3.000.000" dan bukan "ValidationError on field amount".

Tidak ada tanda pisah em (`—`) di teks antarmuka maupun di pesan error.

## Yang sengaja tidak diurus

| Hal | Alasan |
| --- | --- |
| Rate limiting | Tidak ada trafik publik saat demo |
| Caching | Data berubah terus, dan dataset kecil |
| Internationalization | Satu bahasa, dan menambah lapisan i18n menambah biaya tanpa pembeli |
| Soft delete menyeluruh | Hanya komentar yang punya soft delete; sisanya tidak pernah dihapus |
| Backup dan disaster recovery | Lingkungan demo |

Daftar ini ada supaya "kenapa tidak ada caching" terjawab sekali, bukan setiap kali ditanya.

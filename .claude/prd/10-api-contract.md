# 10. Kontrak API

Semua endpoint di bawah prefix `/api/v1`. Autentikasi dengan `Authorization: Bearer <jwt>`.

## Bentuk error yang seragam

Setiap error mengembalikan bentuk yang sama, sehingga frontend hanya perlu satu penangan:

```json
{
  "error": {
    "code": "pledge_melebihi_sisa",
    "message": "Pledge melebihi sisa dana yang dibutuhkan.",
    "detail": { "remaining_amount": 3000000 }
  }
}
```

| Kode HTTP | Dipakai untuk |
| --- | --- |
| `400` | Payload tidak valid secara bentuk |
| `401` | Token tidak ada atau kedaluwarsa |
| `403` | Peran tidak berhak, atau bukan pemilik sumber daya |
| `404` | Sumber daya tidak ada, atau tidak boleh diketahui keberadaannya |
| `409` | Transisi status tidak sah, atau aturan bisnis dilanggar |
| `422` | Payload valid bentuknya tapi gagal validasi domain |

`409` dipakai untuk semua pelanggaran state machine ([08-state-machines.md](08-state-machines.md)).
`detail` menyertakan `current_status` supaya frontend bisa menjelaskan ke pengguna.

## Auth

| Endpoint | Peran | Efek |
| --- | --- | --- |
| `POST /auth/register` | publik | Membuat akun. Body: `email`, `password`, `name`, `role`. |
| `POST /auth/login` | publik | Mengembalikan `access_token` berisi `sub` dan `role`. |
| `GET /auth/me` | terautentikasi | Profil singkat pengguna saat ini. |

## Campaign

| Endpoint | Peran | Efek |
| --- | --- | --- |
| `POST /campaigns` | investor | Campaign baru berstatus `open`. Body wajib memuat `apply_deadline` dan `funding_deadline`; `funding_deadline` yang tidak lebih lambat dari `apply_deadline` ditolak `422` ([BR-64](07-business-rules.md)). |
| `GET /campaigns` | publik | Daftar campaign `open`. Query: `sector`, `page`. |
| `GET /campaigns/{id}` | publik | Detail campaign, termasuk jumlah proposal masuk. |
| `PATCH /campaigns/{id}` | pemilik | Hanya `title`, `description`, dan `score_threshold`. `score_threshold` ditolak `409` bila sudah ada proposal masuk ([BR-77](07-business-rules.md)). |
| `POST /campaigns/{id}/close` | pemilik | Status menjadi `closed`. |
| `GET /campaigns/{id}/proposals` | pemilik | Semua proposal termasuk `rejected`, terurut skor lalu vote lalu waktu submit. |

## Proposal

| Endpoint | Peran | Efek |
| --- | --- | --- |
| `POST /campaigns/{id}/proposals` | umkm | Membuat proposal `submitted` beserta milestone-nya, lalu memicu job scoring. Mengembalikan `201` segera, tanpa menunggu AI. |
| `GET /proposals` | publik | Hanya `listed` ke atas. Query: `sector`, `campaign_id`, `sort`. |
| `GET /proposals/{id}` | kondisional | Publik bila `listed` ke atas. Bila `submitted` atau `rejected`, hanya pemilik proposal dan pemilik campaign. |
| `GET /proposals/mine` | umkm | Proposal milik pengguna saat ini beserta statusnya. |
| `POST /proposals/{id}/rescore` | pemilik proposal, pemilik campaign | Hanya bila `scoring_status = failed`, selain itu `409`. |
| `GET /proposals/{id}/scoring` | pemilik proposal, investor | Hasil scoring terbaru lengkap dengan komponen, red flag, dan brief. `403` untuk peran komunitas ([BR-35](07-business-rules.md)). |

## Pledge

| Endpoint | Peran | Efek |
| --- | --- | --- |
| `POST /proposals/{id}/pledges` | investor | Body: `amount`. Mencatat `pledge_in`, menghitung ulang lead investor dan status funding. `409` bila melebihi sisa, dengan `remaining_amount` di `detail`. |
| `DELETE /pledges/{id}` | pemilik pledge | Menandai `cancelled`, mencatat `refund_out`, menghitung ulang. `409` bila proposal sudah `funded`. |
| `GET /proposals/{id}/pledges` | investor, pemilik proposal | Daftar pledge aktif beserta nominal dan penanda lead investor. |

## Milestone

| Endpoint | Peran | Efek |
| --- | --- | --- |
| `GET /proposals/{id}/milestones` | publik bila proposal publik | Daftar milestone beserta status dan laporan terakhir. |
| `POST /milestones/{id}/reports` | pemilik proposal | Membuat laporan baru, milestone menjadi `reported`. `409` untuk `seq = 1` atau bila `seq - 1` belum cair. |
| `POST /milestones/{id}/approve` | lead investor | Mencatat `disbursement_out`, milestone `disbursed`. Bila itu milestone terakhir, proposal menjadi `completed`. |
| `POST /milestones/{id}/reject` | lead investor | Body: `note` minimal 10 karakter. Laporan menjadi `rejected`, milestone kembali `pending`. |

## Komunitas

| Endpoint | Peran | Efek |
| --- | --- | --- |
| `POST /proposals/{id}/vote` | community | Toggle. Mengembalikan `voted` dan `vote_count` terbaru. |
| `GET /proposals/{id}/comments` | publik | Daftar komentar, terbaru di atas. |
| `POST /proposals/{id}/comments` | community | Body: `body`, maksimal 500 karakter. |
| `DELETE /comments/{id}` | penulis komentar | Soft delete. |

## Internal

Hanya aktif bila `ENV=dev`. Di `ENV=prod`, seluruh router ini tidak didaftarkan sama sekali,
sehingga mengembalikan `404` ([BR-63](07-business-rules.md)).

| Endpoint | Efek |
| --- | --- |
| `POST /internal/clock/tick` | Body: `advance_days`. Memajukan `virtual_now` untuk mendemokan deadline. |
| `POST /internal/clock/reset` | Mengembalikan ke jam asli. |
| `GET /internal/ledger/{proposal_id}` | Seluruh entri ledger proposal beserta saldo hasil penjumlahan. |
| `POST /internal/seed` | Mengisi data demo: 3 investor, 4 UMKM, 2 campaign, 6 proposal dengan kualitas berbeda. |

## Aturan yang mengikat seluruh API

1. Endpoint yang mengubah uang atau status **wajib** berjalan dalam satu transaksi database
   bersama entri ledger-nya. Tidak boleh ada keadaan di mana milestone `disbursed` tapi entri
   ledger-nya gagal tertulis.
2. Endpoint daftar selalu mengembalikan urutan yang deterministik. Pengurutan yang berakhir seri
   diputus oleh `created_at` lalu `id`.
3. Tidak ada endpoint yang mengembalikan `password_hash`, token orang lain, atau identitas
   investor sebelum proposal `funded`.
4. Setiap endpoint punya satu baris di matriks RBAC yang diuji oleh regression test **R5**:
   endpoint kali peran, menghasilkan `200` atau `403`. Endpoint baru tanpa baris baru di matriks
   itu akan membuat R5 merah.

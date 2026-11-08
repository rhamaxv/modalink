# 01. Tujuan, Scope, dan Metrik

## Tujuan produk

1. **Memangkas waktu screening investor** lewat AI scoring dan ringkasan otomatis, sehingga
   investor membaca proposal secara mendalam hanya untuk kandidat yang sudah tersaring.
2. **Membuka akses pendanaan ke lebih banyak UMKM** lewat model co-funding, sehingga proposal
   tidak harus menemukan satu investor yang sanggup menanggung seluruhnya.
3. **Membangun kepercayaan** lewat pencairan bertahap dan sinyal dukungan komunitas, sehingga
   keputusan investor berpijak pada lebih dari satu sumber.

## Non-goals

Di luar scope, dan disebut sebagai roadmap saat pitching, bukan disembunyikan:

| Tidak dibangun | Diganti dengan |
| --- | --- |
| Payment gateway atau escrow sungguhan | Pencatatan angka di tabel `ledger_entries` |
| Verifikasi legal dan KYC penuh | Field profil usaha yang diisi sendiri oleh UMKM |
| Refund otomatis ke rekening bank | Status `failed` dan entri `refund_out` di ledger |
| Impact dashboard pasca-pendanaan | Disebut sebagai rencana lanjutan |
| Notifikasi email atau push | Status terlihat saat pengguna membuka halaman |
| Pencarian dan filter lanjutan | Daftar terurut skor AI, dengan filter sektor sederhana |

## Success metrics

Ini metrik untuk demo hackathon, bukan metrik bisnis. Keduanya berbeda dan jangan dicampur.

| Metrik | Ambang lulus | Cara diukur |
| --- | --- | --- |
| Flow end-to-end berjalan | campaign dibuat, proposal masuk, skor AI tampil, co-funding tercapai, milestone cair, proposal `completed` | Regression test R3 hijau, lalu dijalankan manual sekali |
| AI scoring masuk akal | 3 skenario uji (proposal bagus, biasa, red flag) menghasilkan urutan skor yang benar | Contract test `test_live_scoring_ordering` |
| Perbedaan dari marketplace biasa terlihat | Satu layar memuat skor terurai, progress funding multi-investor, dan riwayat milestone | Review manual terhadap halaman detail proposal |
| Demo tidak bergantung jaringan | Seluruh flow bisa dijalankan dengan `MockScoringEngine` | `SCORING_ENGINE=mock make demo` berhasil |

## Batas waktu

Prioritas: **secepatnya, tanpa menurunkan kualitas**. Operasionalnya:

- Fase dikerjakan berurutan, dan fase berikutnya tidak dimulai sebelum regression suite fase
  sebelumnya hijau.
- Fitur yang tidak ada di tabel non-goals tetapi juga tidak ada di `plan/` adalah penambahan
  scope. Tanyakan dulu, jangan kerjakan diam-diam.
- Kalau sebuah fase meleset dari perkiraan, yang dipotong adalah cakupan fitur, bukan test.

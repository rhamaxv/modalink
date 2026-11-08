---
name: nextjs-app-conventions
description: Konvensi frontend Logicodix. Gunakan sebelum menulis atau mengubah komponen, halaman, atau gaya apa pun. Memuat urutan membaca arah design, pembagian server dan client component, aturan uang dan status di UI, aksesibilitas, dan gerbang antislop sebelum penyerahan.
---

# Frontend Logicodix

## Baca dulu, dalam urutan ini

1. `DESIGN.md` di akar repo. Arah visualnya ditentukan pemilik project, bukan ditebak.
2. Skill `antislop:antislop` (inti), lalu `antislop:antislop-ui`.
3. Untuk form dan navigasi: `antislop:antislop-human`.
4. Untuk layout yang harus mengalir: `antislop:antislop-layoutmobile`.
5. Untuk teks antarmuka: `antislop:antislop-copywriting`.

Mode yang dipilih pemilik project adalah **DURING**: aturan diterapkan sambil mengerjakan, bukan
diaudit setelah jadi.

## Dial yang berlaku, dan konsekuensinya

**ENERGY 2 / RHYTHM 3 / MOTION 2.**

RHYTHM 3 berarti **tidak boleh ada dua section berurutan dengan pola komposisi yang sama**. Ini
diuji, bukan dijanjikan: setiap `<section>` memasang `data-pola="<nama>"`, dan
`tests/komposisi.test.tsx` menolak dua pola identik berurutan.

Pola yang tersedia: `naratif-kiri`, `dua-kolom-asimetris`, `lebar-penuh-kutipan`,
`daftar-bernomor`, `tabel-padat`.

MOTION 2 berarti scroll-reveal terukur di halaman publik dan transisi state di dashboard. Tidak
ada parallax, tidak ada bounce, tidak ada loop tanpa henti.

## Aksen kuning

`--accent` adalah satu-satunya aksen, dan ia muncul hanya di momen yang berarti: tombol aksi utama
satu per layar, bilah progres funding, penanda milestone yang sedang berjalan.

**Teks di atas `--accent` selalu `--ink`, tidak pernah putih.** Kontras putih di atas `#FFC94A`
hanya 1.53:1.

Kalau aksen muncul lebih dari tiga kali di satu layar, dia bukan aksen lagi.

Panel skor AI **tidak** memakai aksen: ia informasi, bukan aksi. Aksen disimpan untuk tombol
pledge di sebelahnya.

## Server dan client component

| Jenis | Dipakai untuk |
| --- | --- |
| Server component (default) | daftar padat data, halaman detail, apa pun yang hanya membaca |
| Client component (`"use client"`) | form, sakelar tema, apa pun yang punya state atau event |

`"use client"` ditulis di komponen terkecil yang membutuhkannya, bukan di halaman. Menaruhnya di
halaman menarik seluruh pohon ke klien.

## Uang dan status di UI

- Format rupiah hanya lewat `lib/money.ts`. Tidak ada `toLocaleString` ad-hoc di komponen.
- Setiap angka rupiah memakai `font-variant-numeric: tabular-nums` (kelas `.tabular`), supaya
  kolom nominal sejajar per digit.
- Persentase progres memakai `Math.floor`, bukan `Math.round`. Bilah yang menunjukkan 100% pada
  proposal yang belum `funded` adalah kebohongan kecil yang merusak kepercayaan.
- Label status hanya lewat `lib/status.ts`. Satu tempat, satu terjemahan.
- **Status tidak pernah disampaikan lewat warna saja.** `funded` dan `failed` tidak boleh
  dibedakan hanya oleh hijau dan merah; selalu ada teks pendampingnya.

## Tiga keadaan adalah bagian desain

Setiap layar yang menampilkan data wajib punya ketiganya, dan ketiganya dibuat di fase fondasi,
bukan belakangan:

| Keadaan | Harus menyebut |
| --- | --- |
| Kosong | sebabnya dan satu aksi yang mengisinya |
| Memuat | apa yang sedang dimuat, tanpa memindahkan layout saat data datang |
| Galat | penyebabnya dan satu tombol coba lagi, dengan `role="alert"` |

"Tidak ada data" bukan keadaan kosong, itu label hampa.

## Aksesibilitas yang tidak bisa ditawar

- Setiap kolom form memakai komponen `Kolom`, yang menggabungkan `<label htmlFor>`,
  `aria-describedby`, dan `aria-invalid`. Satu komponen, dipakai di mana-mana, supaya aksesibilitas
  form tidak bergantung pada ingatan.
- Bilah progres memakai `role="progressbar"` dengan `aria-valuenow` dan `aria-valuetext`
  berisi nominal, bukan hanya `<div>` yang lebarnya diatur.
- Perubahan yang diumumkan tanpa merebut fokus memakai `aria-live="polite"`.
- Kontrol memakai elemen aslinya: `<button>`, bukan `<div onClick>`.
- Indikator fokus tidak pernah dihapus tanpa diganti yang lebih baik.
- Target sentuh minimal 44px.

## Angka dan isi yang tidak nyata

Produk ini penuh angka rupiah, dan kartu statistik berisi angka yang belum tersambung ke data
adalah pelanggaran yang paling mudah terjadi.

Aturannya: **angka muncul hanya kalau datanya nyata.** Belum tersambung berarti tidak ditampilkan.

Berlaku juga untuk: testimoni, bilah logo "dipercaya oleh", jumlah pengguna, dan delta tren
("naik 12% minggu ini") yang tidak punya deret data di belakangnya.

Kolom form kosong memakai placeholder jujur (`email@contoh.id`, `Nama usaha Anda`), bukan data
palsu yang terlihat asli (`Budi Santoso`, `budi@gmail.com`).

## Bahasa antarmuka

Indonesia. Istilah teknis yang sudah lazim dipakai apa adanya: campaign, pledge, milestone,
dashboard. Jangan diterjemahkan paksa jadi "kampanye penggalangan" atau "tonggak pencapaian".

Pesan error ditujukan ke pengguna, bukan ke programmer. Tidak ada tanda pisah em di teks antarmuka.

## Gerbang sebelum menyerahkan pekerjaan UI

Jalankan Delivery Gate dari skill `antislop:antislop` dan sertakan laporannya: PASS atau FAIL per
aturan, **dengan bukti**. Laporan yang memuat satu FAIL tidak boleh dikirim.

Yang paling sering jadi FAIL di project ini:

- [ ] R-03 scroll horizontal di 320px
- [ ] R-17 angka yang belum tersambung ke data
- [ ] R-25 pasangan warna baru yang belum diukur kontrasnya
- [ ] R-26 tombol yang belum punya perilaku
- [ ] R-27 keadaan kosong yang hanya bertuliskan "Tidak ada data"
- [ ] R-32 kontrol yang dibuat dari `<div>` sehingga tidak bisa di-Tab
- [ ] R-34 mode gelap yang belum diperiksa satu per satu
- [ ] R-35 klaim "semua berfungsi" tanpa daftar klik satu per satu

R-35 menuntut daftar, bukan ringkasan. Bentuknya:

```
Beranda
  "Jelajahi proposal"  -> /jelajah, 6 kartu tampil, tanpa galat konsol
  sakelar tema         -> data-theme berganti, latar body ikut berganti
```

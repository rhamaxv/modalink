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

**ENERGY 4 / RHYTHM 3 / MOTION 2.** ENERGY naik dari 2 pada 10 November 2026: arah
sebelumnya tidak melanggar aturan apa pun, ia hanya **datar dan tanpa rasa**, yang
antislop sendiri namai *Sterile Default*. Perbaikannya menaikkan dial, bukan menambah
larangan.

RHYTHM 3 berarti **tidak boleh ada dua section berurutan dengan pola komposisi yang sama**.
Ini diuji dua lapis di `tests/composition.test.tsx`: lapis pertama menolak dua
`data-pola` identik berurutan, lapis kedua memeriksa **DOM yang sungguh dirender**, karena
audit desain pernah menemukan section berlabel `dua-kolom-asimetris` yang kenyataannya satu
kolom. Label yang berbeda belum berarti komposisi yang berbeda.

MOTION 2 berarti scroll-reveal terukur di halaman publik dan transisi state di dashboard.
Tidak ada parallax, tidak ada bounce, tidak ada loop tanpa henti.

## Dua aksen, dengan tugas berbeda

`--accent` **lime `#DDFD6C`** adalah tindakan dan uang: satu tombol aksi utama per layar,
bilah progres funding, penanda tahap milestone yang sedang berjalan.

`--accent-2` **periwinkle `#AAB2FF`** adalah penanda, bukan tindakan: label kategori,
sorotan angka pendukung. **Ia tidak pernah menjadi latar tombol.**

Tiga aturan yang diuji dan tidak bisa ditawar:

1. **Teks di atas kedua aksen selalu `--on-accent`**, tidak pernah putih dan tidak pernah
   `--ink`. Putih di atas lime mengukur **1,14:1**, di atas periwinkle **2,00:1**, keduanya
   lebih buruk daripada putih-pada-kuning 1,53:1 yang arah lama sudah larang. `--ink`
   berbalik ikut tema, aksen tidak, dan pelanggaran ini pernah hidup di setiap tombol
   selama berjam-jam karena pemeriksanya menggeledah kata "white" alih-alih mengukur warna.
2. **Aksen tidak pernah menjadi teks di tema terang.** Lime sebagai teks di latar terang
   mengukur **1,09:1**. Pakai sebagai latar dengan `--on-accent`, atau sebagai teks hanya
   di permukaan gelap.
3. **Tepat satu aksi berlatar aksen per halaman, dan ia di layar pertama.** Dijatah per
   halaman, bukan per section: halaman depan sempat membelanjakan satu-satunya aksennya di
   CTA paling bawah, sehingga layar pertama tidak punya warna sama sekali.

Pakai `Button` dan `ButtonLink` dari `components/ui`, jangan menyusun gaya tombol sendiri.
Halaman yang menyusunnya sendiri berakhir dengan setiap CTA berupa tautan teks transparan.

Panel skor AI **tidak** memakai aksen: ia informasi, bukan aksi.

## Garis punya dua token, dan memilih yang salah tidak akan terlihat

`--line` mengukur 1,46:1 dan **hanya sah sebagai pemisah dekoratif atau tepi kartu**.
Batas kontrol yang bisa diklik atau difokus memakai `--line-strong` (3,94:1). Satu tombol
pernah lolos review dengan border 1,27:1 karena keduanya dulu satu token.

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

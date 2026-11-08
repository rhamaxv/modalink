# DESIGN.md: Arah visual Logicodix

Arah di bawah ini ditentukan oleh pemilik project. Dokumen ini hanya merapikannya menjadi token
dan aturan yang bisa dipakai saat membangun. Nilai hex adalah titik awal yang boleh digeser;
karakter, palet, tipografi, dan dial di bawah **bukan** titik awal, melainkan keputusan.

`antislop` adalah filter di atas arah ini, bukan sumber arah. Kalau keduanya bertabrakan,
sebut tabrakannya ke pemilik project, jangan diam-diam memilih salah satu.

## Design Read

> Membacanya sebagai: platform pendanaan UMKM untuk dua audiens sekaligus (investor yang menimbang
> angka, pemilik usaha yang mengisi formulir panjang), dalam bahasa visual **editorial & naratif**,
> dial **ENERGY 2 / RHYTHM 3 / MOTION 2**.

## Karakter: editorial & naratif

Tiap proposal diperlakukan seperti artikel, bukan seperti baris tabel. Foto dan cerita usaha
mendapat ruang; angka tidak dijejalkan ke dalam grid rapat.

Kenapa: produk ini menjual *dampak*, dan dampak dibaca sebagai cerita, bukan sebagai metrik.

Karakter editorial biasanya dibawa oleh serif. Di sini tidak. Hierarki datang dari **ukuran dan
ruang**, bukan dari bentuk huruf:

- Judul halaman besar sekali (clamp 2.5rem sampai 4rem), bukan 1.5rem yang ditebalkan.
- Lebar baris teks naratif dibatasi 62 sampai 68 karakter. Form dan tabel boleh lebih lebar.
- Jarak antar blok lega: skala spasi 4, 8, 16, 24, 40, 64, 96. Bukan 16 di mana-mana.

Kenapa satu sans humanis dan bukan serif: teks Indonesia di formulir panjang lebih mudah dibaca
dengan sans humanis, dan editorial yang dibangun dari sans adalah jalur yang lebih jarang dipakai,
jadi lebih sulit terbaca generik.

## Dial

| Dial | Nilai | Artinya di sini |
| --- | --- | --- |
| ENERGY | 2 | Landing page punya karakter kuat. Dashboard tenang dan fokus kerja. |
| RHYTHM | 3 | **Tidak boleh ada dua section berpola sama.** Lihat aturan di bawah. |
| MOTION | 2 | Scroll-reveal terukur di halaman publik, transisi state di dashboard. Tidak ada parallax, tidak ada bounce. |

RHYTHM 3 adalah aturan, bukan saran. Kalau dua section berurutan sama-sama "judul di tengah +
grid kartu seragam", salah satunya harus diubah. Variasi yang tersedia: lebar penuh vs terbatas,
rata kiri vs tengah, satu kolom vs dua kolom asimetris, dengan rule horizontal vs tanpa.

## Palet

Dua warna inti (netral tidak dihitung) plus satu aksen. Total sesuai batas R-29.

| Token | Terang | Gelap | Peran |
| --- | --- | --- | --- |
| `--ink` | `#1A1917` | `#F2EEE6` | Teks utama, garis tegas |
| `--paper` | `#FBF9F4` | `#141310` | Latar halaman |
| `--surface` | `#F3EFE6` | `#201E19` | Kartu, panel, baris tabel bergaris |
| `--muted` | `#5C574E` | `#A8A196` | Teks sekunder, label, satuan |
| `--line` | `#DCD5C7` | `#36332B` | Border, pemisah |
| `--accent` | `#FFC94A` | `#FFC94A` | **Aksen tunggal** |
| `--ok` | `#2F6B3A` | `#7FCB8C` | Status positif (funded, cair) |
| `--warn` | `#A3561F` | `#E8A765` | Perlu tindakan (laporan menunggu review) |
| `--danger` | `#A32C1F` | `#F08C7E` | Rejected, failed |

### Aturan kuning yang tidak bisa dilanggar

Kuning adalah satu-satunya warna yang **tidak bisa** menjadi latar teks putih. Rasio kontras
putih di atas `#FFC94A` hanya 1.53:1, jauh di bawah ambang 4.5:1.

- Teks di atas `--accent` **selalu** `--ink`. Tidak pernah putih.
- `--accent` muncul hanya di momen yang berarti: tombol aksi utama satu per layar, bar progres
  funding, penanda tahap milestone yang sedang berjalan. Tidak di ikon, tidak di border kartu,
  tidak di badge biasa.
- Kalau aksen muncul lebih dari tiga kali di satu layar, dia bukan aksen lagi. Kurangi.

Kenapa dipakai hemat: aksen yang jarang muncul membuat tiap kemunculannya berarti, dan itu yang
mengarahkan mata ke keputusan yang sedang diminta dari pengguna.

## Tipografi

Satu keluarga sans humanis untuk semua. Kandidat: Source Sans 3, Public Sans, atau IBM Plex Sans.
Pilih satu, jangan campur.

Kenapa humanis: bentuk hurufnya lebih terbuka dan lebih mudah dibaca di formulir panjang
berbahasa Indonesia dibanding grotesk geometris.

| Peran | Ukuran | Berat |
| --- | --- | --- |
| Judul halaman | `clamp(2.5rem, 5vw, 4rem)` | 600 |
| Judul section | 1.75rem | 600 |
| Judul kartu | 1.125rem | 600 |
| Teks | 1rem, line-height 1.6 | 400 |
| Label, satuan, caption | 0.8125rem | 500 |

**Angka rupiah wajib `font-variant-numeric: tabular-nums`.** Tanpa itu, kolom nominal di tabel
tidak sejajar per digit dan angka jadi sulit dibandingkan sekilas.

## Motif identitas

Nominal rupiah adalah tokoh utama tiap kartu proposal: ditulis besar (1.75rem ke atas), tabular,
rata kiri, dengan label kecil di atasnya, bukan diselipkan sebagai teks biasa di dalam paragraf.

Kenapa: ini produk tentang uang yang berpindah. Angkanya yang harus dibaca lebih dulu, dan
pengulangan perlakuan ini di seluruh aplikasi yang membuatnya terasa satu produk.

(Motif ini adalah rumusan dari pilihan "editorial & naratif". Kalau tidak cocok, ganti.)

## Radius dan elevasi

- Radius: `4px` untuk input dan badge, `8px` untuk kartu, `12px` untuk panel besar. Variasi ini
  disengaja sebagai penanda hierarki. Tidak ada yang berbentuk pil.
- Bayangan dipakai hanya untuk elemen yang benar-benar melayang di atas halaman: dropdown, modal,
  toast. Kartu dibatasi oleh `--line`, bukan oleh bayangan.

## Yang harus ada di setiap layar data

Bukan bonus, melainkan bagian dari desain:

- **Empty state** dengan satu aksi yang jelas ("Belum ada proposal masuk. Bagikan link campaign.")
- **Loading state** yang tidak memindahkan layout saat data datang.
- **Error state** dengan penyebab dan satu tombol coba lagi.

## Tema terang dan gelap

Produk ini tidak punya alasan kuat untuk mengunci satu tema, jadi toggle terang/gelap **dibangun**,
bukan ditunda. Kedua mode harus diperiksa: kontras, warna status, dan layout. Mode yang rusak
adalah cacat, bukan fitur yang belum selesai.

## Bahasa

Antarmuka berbahasa Indonesia. Istilah teknis yang sudah lazim dipakai apa adanya (campaign,
pledge, milestone, dashboard). Jangan diterjemahkan paksa menjadi "kampanye penggalangan" atau
"tonggak pencapaian".

Tidak ada tanda pisah em (`—`) di teks antarmuka. Pakai koma, titik, titik dua, atau kurung.

## Kontras yang sudah diukur

Diukur dengan pemeriksa kontras antislop, bukan ditaksir. Ambang WCAG AA: 4.5:1 teks normal,
3:1 teks besar.

| Teks | Latar | Rasio | Verdict |
| --- | --- | --- | --- |
| `--ink` `#1A1917` | `--paper` `#FBF9F4` | 16.7:1 | lolos |
| `--muted` `#5C574E` | `--paper` `#FBF9F4` | 6.82:1 | lolos |
| `--muted` `#5C574E` | `--surface` `#F3EFE6` | 6.25:1 | lolos |
| `--ink` `#1A1917` | `--accent` `#FFC94A` | 11.47:1 | lolos |
| putih `#FFFFFF` | `--accent` `#FFC94A` | 1.53:1 | **gagal, dilarang** |
| `--ok` `#2F6B3A` | `--paper` `#FBF9F4` | 6.08:1 | lolos |
| `--warn` `#A3561F` | `--paper` `#FBF9F4` | 5.11:1 | lolos |
| `--danger` `#A32C1F` | `--paper` `#FBF9F4` | 6.79:1 | lolos |
| `--ink` gelap `#F2EEE6` | `--paper` gelap `#141310` | 16.05:1 | lolos |
| `--muted` gelap `#A8A196` | `--paper` gelap `#141310` | 7.26:1 | lolos |
| `--ok` gelap `#7FCB8C` | `--paper` gelap `#141310` | 9.58:1 | lolos |
| `--warn` gelap `#E8A765` | `--paper` gelap `#141310` | 8.98:1 | lolos |
| `--danger` gelap `#F08C7E` | `--paper` gelap `#141310` | 7.75:1 | lolos |

Kalau ada nilai hex yang digeser, ukur ulang pasangannya sebelum dipakai.

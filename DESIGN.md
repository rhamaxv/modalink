# DESIGN.md: Arah visual Modalink

Arah ini ditentukan pemilik project pada 10 November 2026, menggantikan arah sebelumnya
secara penuh. Dokumen lama bercorak **editorial & naratif** di atas kertas hangat dengan
satu aksen kuning. Ia tidak gagal karena melanggar aturan; ia gagal karena **datar dan
tanpa rasa**, yang modul antislop sendiri namai *Sterile Default*: hasil menyaring terlalu
kuat tanpa arah yang cukup kuat. Perbaikannya bukan menambah larangan, melainkan menaikkan
dial kehidupannya.

Referensi yang ditunjuk pemilik project: [the5ers.com](https://the5ers.com). Nilai di bawah
diukur langsung dari situs itu, bukan ditaksir.

`antislop` adalah filter di atas arah ini, bukan sumber arah. Kalau keduanya bertabrakan,
sebut tabrakannya ke pemilik project, jangan diam-diam memilih salah satu.

## Satu hal yang harus dipecahkan sendiri

Referensinya memuat **341 gambar dan 89 SVG** dalam satu halaman. Sebagian besar rasanya
datang dari fotografi manusia nyata. Modalink punya **nol** gambar, dan mengarangnya
dilarang aturan lomba sekaligus R-18 dan R-36.

Jadi menyalin sistem visualnya tanpa menjawab "apa yang mengisi ruang tempat foto mereka"
hanya menghasilkan situs **gelap yang tetap datar**.

Jawabannya **uang**. Nominal rupiah tabular adalah elemen grafis produk ini, bukan sekadar
data. Di atas latar hampir hitam, angka setinggi 80px dengan bobot display melakukan
pekerjaan yang di situs itu dilakukan foto. Dokumen lama sudah menyebut nominal sebagai
tokoh utama tapi menetapkan batas minimum 1,75rem, yaitu 28px, dan 28px itulah yang
membuatnya hilang. Batas itu dinaikkan.

## Dial

| Dial | Nilai | Artinya di sini |
| --- | --- | --- |
| ENERGY | **4** | Naik dari 2. Tipografi tegas, kontras tinggi, komposisi asimetris. Dashboard tetap lebih tenang daripada halaman publik, tapi tidak lagi pucat. |
| RHYTHM | 3 | **Tidak boleh ada dua section berurutan berpola sama.** Tetap seperti sebelumnya. |
| MOTION | 2 | Scroll-reveal terukur di halaman publik, transisi state di dashboard. Tidak ada parallax, tidak ada bounce. |

## Palet

Dua warna inti netral plus **dua aksen**. Jumlah ini sengaja melewati batas satu-aksen di
arah sebelumnya, dan itu keputusan sadar: dua aksen dengan peran berbeda adalah yang
membedakan referensi ini dari latar gelap biasa.

| Token | Gelap (utama) | Terang | Peran |
| --- | --- | --- | --- |
| `--paper` | `#100F0F` | `#FBF9F4` | Latar halaman |
| `--panel` | `#1A1918` | `#F3EFE6` | Kartu dan panel |
| `--panel-raised` | `#242322` | `#EAE4D8` | Panel di atas panel |
| `--ink` | `#FFFFFF` | `#100F0F` | Teks utama |
| `--muted` | `#A3A09B` | `#5C574E` | Teks sekunder, label, satuan |
| `--line` | `#32302E` | `#DCD5C7` | Pemisah dekoratif, tepi kartu |
| `--line-strong` | `#767166` | `#8A8275` | **Batas kontrol interaktif** |
| `--accent` | `#DDFD6C` | `#DDFD6C` | Aksi utama, bilah funding, tahap aktif |
| `--accent-2` | `#AAB2FF` | `#AAB2FF` | Penanda sekunder: label kategori, sorotan data |
| `--on-accent` | `#100F0F` | `#100F0F` | **Teks di atas kedua aksen. Tidak pernah berbalik.** |
| `--ok` | `#7FCB8C` | `#2F6B3A` | Status positif |
| `--warn` | `#E8A765` | `#A3561F` | Perlu tindakan |
| `--danger` | `#F08C7E` | `#A32C1F` | Gagal, ditolak |

### Aturan aksen yang tidak bisa dilanggar

Teks di atas `--accent` maupun `--accent-2` **selalu** `--on-accent`. Tidak pernah putih,
dan tidak pernah `--ink`.

Alasannya bukan selera, dan bukan pula warisan dari palet lama: putih di atas lime
mengukur **1,14:1** dan di atas periwinkle **2,00:1**. Keduanya **lebih buruk** daripada
putih-pada-kuning 1,53:1 yang arah sebelumnya sudah melarang.

`--on-accent` sengaja **tidak punya pasangan di blok tema terang**. `--ink` berbalik saat
tema berganti, aksen tidak, jadi teks di atas aksen tidak boleh mengikuti token yang
berbalik. Pelanggaran aturan ini pernah dikirim ke produksi dan hidup di setiap tombol
selama berjam-jam karena pemeriksaannya menggeledah kata "white" alih-alih mengukur
warnanya. Pagar `frontend/tests/accent-contrast.test.ts` sekarang mengukur, dan ia harus
tetap mengukur.

### Aksen tidak pernah menjadi teks di tema terang

Empat baris gagal di tabel kontras bukan kasus sudut, melainkan akibat langsung
dari aksen yang tidak ikut berbalik saat tema berganti. Di latar gelap keduanya
terbaca sebagai teks; di latar terang lime mengukur **1,09:1**, yang artinya
praktis tidak terlihat.

Versi pertama dokumen ini hanya mengukur aksen terhadap latar gelap lalu menulis
"lolos" tanpa menyebut syaratnya, dan satu agen sempat memakai `text-accent-2`
sebagai label di tema terang atas dasar baris itu. Kesalahannya milik dokumen,
bukan agen.

Aturannya karena itu: **aksen dipakai sebagai latar dengan `--on-accent` di
atasnya, atau sebagai teks hanya di permukaan gelap.** Label berwarna aksen di
tema terang ditulis sebagai chip `bg-accent-2 text-on-accent`, bukan sebagai
teks berwarna, karena kombinasi itu sudah terukur aman di kedua tema.

### Pembagian kerja dua aksen

Satu aksen menjadi dua bukan berarti dua kali lebih banyak kuning. Keduanya punya tugas
berbeda dan tidak boleh tertukar:

- `--accent` **lime** adalah tindakan dan uang. Tombol aksi utama satu per layar, bilah
  progres funding, penanda tahap milestone yang sedang berjalan.
- `--accent-2` **periwinkle** adalah penanda, bukan tindakan. Label kategori di atas judul
  section, sorotan angka pendukung, penekanan di dalam kalimat. Ia tidak pernah menjadi
  latar tombol.

Anggaran per layar: **tiga kemunculan `--accent`**, dan periwinkle secukupnya karena ia
tidak bersaing memperebutkan klik. Kalau lime muncul lebih dari tiga kali, ia bukan aksen
lagi.

## Tipografi

**Dua keluarga, bukan satu.** Ini perubahan dari arah sebelumnya, dan ia yang paling
menentukan rasanya.

| Peran | Keluarga | Bobot |
| --- | --- | --- |
| Judul halaman dan judul section | **Cabinet Grotesk** | 700, 800 untuk nominal besar |
| Teks, label, kontrol, angka | **General Sans** | 400, 500, 600, 700 |

Keduanya dari Fontshare, lisensi ITF Free Font License, **di-host sendiri** di
`frontend/app/fonts/` lewat `next/font/local`. Bukan lewat CDN: deployment lomba wajib
tetap bisa diakses juri, dan satu dependency jaringan pihak ketiga adalah satu cara lagi
ia bisa mati.

| Peran | Ukuran | Bobot | Leading |
| --- | --- | --- | --- |
| Judul halaman | `clamp(2.75rem, 6vw, 4.5rem)` | 700 | **1,10** |
| Judul section | `clamp(2rem, 4vw, 2.75rem)` | 700 | **1,10** |
| Nominal utama | `clamp(3rem, 7vw, 5rem)` | 800 | 1,00 |
| Nominal pendukung | 1,75rem | 700 | 1,10 |
| Judul kartu | 1,25rem | 600 | 1,30 |
| Teks | 1rem | 400 | 1,60 |
| Label, satuan, caption | 0,8125rem | 500 | 1,40 |

**Leading 1,10 pada judul adalah separuh dari efeknya.** Judul lama berukuran 64px dengan
leading 1,25 terasa lebih lemah daripada judul referensi yang hanya 50px dengan leading
1,10. Ukuran saja tidak cukup; yang membuat judul terasa padat adalah barisnya rapat dan
bobotnya berat.

**Judul section sebesar judul halaman.** Di referensi keduanya 50px. Judul section lama
28px, dan itu sebabnya setiap section terasa seperti catatan kaki. Angka di tabel atas
sudah mencerminkan ini.

**Angka rupiah wajib `font-variant-numeric: tabular-nums`.** Tanpa itu kolom nominal tidak
sejajar per digit dan angka sulit dibandingkan sekilas.

## Komposisi

- **Asimetris, bukan terpusat.** Judul dan teks di kiri dengan lebar terbatas, konten
  pendukung di kanan yang boleh menembus tepi layar. Judul terpusat dipakai sesekali
  sebagai variasi, bukan sebagai default.
- **Section bergantian gelap dan panel.** `--paper` lalu `--panel` lalu `--paper`,
  sehingga batas antar-section terbaca tanpa garis.
- **RHYTHM 3 tetap berlaku.** Variasi yang tersedia: lebar penuh lawan terbatas, rata kiri
  lawan tengah, satu kolom lawan dua kolom asimetris, kartu lawan daftar bernomor.
- Lebar baris teks naratif 62 sampai 68 karakter lewat `--measure`. Form dan tabel boleh
  lebih lebar.
- Skala spasi 4, 8, 16, 24, 40, 64, 96. Bukan 16 di mana-mana.

## Radius dan elevasi

| Token | Nilai | Dipakai untuk |
| --- | --- | --- |
| `--radius-sm` | 8px | Input, lencana |
| `--radius-card` | 16px | Kartu |
| `--radius-panel` | 24px | Panel besar |
| `--radius-feature` | 35px | Blok sorotan, satu atau dua per halaman |
| `--radius-pill` | 9999px | **Tombol** |

Bentuk pil **diizinkan di tombol**, dan ini pembalikan sadar dari arah sebelumnya yang
melarangnya sepenuhnya. Alasannya: pil di referensi dipakai konsisten pada tombol saja,
bukan pada setiap elemen, sehingga ia menjadi bahasa tombol dan bukan dekorasi. Larangan
R-11 menyasar pil **di mana-mana**; pil hanya di tombol tetap merupakan keputusan hierarki.

Kartu tetap dibatasi `--line`, bukan bayangan. Bayangan hanya untuk elemen yang benar-benar
melayang: dropdown, modal, toast.

## Kontras yang sudah diukur

Diukur dengan pemeriksa antislop dan dihitung ulang mandiri, bukan ditaksir. Ambang WCAG
AA: 4,5:1 teks normal, 3:1 teks besar dan batas kontrol.

| Teks | Latar | Rasio | Verdict |
| --- | --- | --- | --- |
| `--ink` putih | `--paper` `#100F0F` | 19,14:1 | lolos |
| `--muted` `#A3A09B` | `--paper` | 7,34:1 | lolos |
| `--muted` | `--panel` `#1A1918` | 6,74:1 | lolos |
| `--on-accent` | `--accent` lime | **16,72:1** | lolos |
| putih | `--accent` lime | **1,14:1** | **gagal, dilarang** |
| `--on-accent` | `--accent-2` periwinkle | **9,59:1** | lolos |
| putih | `--accent-2` | **2,00:1** | **gagal, dilarang** |
| `--accent` sebagai teks | `--paper` gelap | 16,72:1 | lolos |
| `--accent-2` sebagai teks | `--paper` gelap | 9,59:1 | lolos |
| `--accent` sebagai teks | `--paper` **terang** | **1,09:1** | **gagal, dilarang** |
| `--accent` sebagai teks | `--panel` **terang** | **1,00:1** | **gagal, dilarang** |
| `--accent-2` sebagai teks | `--paper` **terang** | **1,90:1** | **gagal, dilarang** |
| `--accent-2` sebagai teks | `--panel` **terang** | **1,74:1** | **gagal, dilarang** |
| `--ok` `#7FCB8C` | `--paper` | 9,86:1 | lolos |
| `--warn` `#E8A765` | `--paper` | 9,25:1 | lolos |
| `--danger` `#F08C7E` | `--paper` | 7,98:1 | lolos |
| `--line-strong` `#767166` | `--paper` | 3,94:1 | lolos ambang 3:1 |
| `--line-strong` | `--panel` | 3,62:1 | lolos ambang 3:1 |
| `--line` `#32302E` | `--paper` | 1,46:1 | **hanya untuk pemisah dekoratif** |

`--line` sengaja di bawah 3:1 dan karena itu **tidak boleh dipakai pada batas kontrol yang
bisa diklik atau difokus**. Batas interaktif memakai `--line-strong`. Pemisahan ini ada
karena satu tombol pernah lolos review dengan border 1,27:1.

## Yang harus ada di setiap layar data

Bukan bonus, melainkan bagian dari desain:

- **Empty state** dengan penyebab dan satu aksi yang jelas.
- **Loading state** yang tidak memindahkan layout saat data datang, termasuk tidak
  memindahkan judul halaman.
- **Error state** dengan penyebab dan satu tombol coba lagi.

## Tema

**Gelap adalah default dan keadaan yang dirancang.** Tema terang tetap dibangun dan tetap
harus bekerja penuh, karena ia sudah ada, teruji, dan menguntungkan sebagian pembaca.
Mode yang rusak adalah cacat, bukan fitur yang belum selesai.

Yang tidak boleh ikut berbalik saat tema berganti: `--accent`, `--accent-2`, dan
`--on-accent`.

## Bahasa

Antarmuka berbahasa Indonesia. Istilah teknis yang sudah lazim dipakai apa adanya
(campaign, pledge, milestone, dashboard). Jangan diterjemahkan paksa.

Tidak ada tanda pisah em (`—`) di teks antarmuka. Pakai koma, titik, titik dua, atau kurung.

## Yang tetap dilarang meski arahnya berubah

Arah baru menaikkan energi, bukan membuka pintu untuk slop. Semua ini tetap berlaku:

- Gradien sebagai perlakuan warna default, glassmorphism di lebih dari satu atau dua
  elemen, bayangan di setiap komponen, grid atau titik di latar.
- Ikon sparkle, petir, robot, atau orb AI.
- Badge kapsul di atas H1, titik status dekoratif, emoji di teks antarmuka.
- **Angka statistik, testimoni, avatar, dan baris logo yang dikarang.** Produk ini tidak
  punya satu pun, dan mengarangnya melanggar aturan lomba.
- H1 berisi nama merek. Nama produk sudah ada di header.

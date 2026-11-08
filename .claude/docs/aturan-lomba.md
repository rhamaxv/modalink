# Aturan Logicodix 2026 yang mengikat pengerjaan

Disarikan dari `GUIDEBOOK-LOGICODIX-FINAL.pdf` (30 halaman) dan klarifikasi panitia di grup
WhatsApp, 7 sampai 8 November 2026. **Baca ini sebelum commit pertama.**

Pelanggaran di sini bukan soal nilai turun, melainkan **diskualifikasi** atau submission tidak
dilanjutkan ke penilaian.

---

## Waktu

| Tahap | Waktu |
| --- | --- |
| Hacking kick-off | 7 November 2026 |
| **Code freeze dan batas submission** | **14 November 2026, 23.59 WIB** |
| Pengumuman finalis | 21 November 2026 |
| Grand Final | 29 November 2026 |

Versi yang dinilai adalah **commit hash final** yang dicantumkan di form submission, dan commit
itu wajib dibuat tidak lebih lambat dari code freeze. Aplikasi yang di-deploy dan video demo
wajib berasal dari commit final tersebut.

Setelah code freeze, deployment tidak boleh diubah kecuali memulihkan ketersediaan layanan tanpa
mengubah kode, fitur, atau data.

Submission hanya bisa dikirim **satu kali** dan bersifat final.

## Riwayat commit

| Aturan | Konsekuensi melanggar |
| --- | --- |
| Commit wajib berkala selama Hacking Week, mencerminkan perubahan nyata | Manipulasi riwayat pengembangan = diskualifikasi |
| **Dilarang bulk upload**: mengunggah seluruh proyek dalam satu commit di akhir | sama |
| **Dilarang force push, rebase, squash, menghapus commit, memanipulasi tanggal** setelah push | sama |
| Seluruh commit wajib dari akun GitHub anggota terdaftar | Melibatkan pihak luar = diskualifikasi |
| Repositori dibuat setelah kick-off, commit pertama setelah kick-off selesai | Proyek dibangun sebelum Hacking Week = diskualifikasi |

### Format pesan commit

Diwajibkan panitia, dan persis format yang dipilih pemilik project:

```
feat: add user authentication
feat: integrate Gemini API for auto-summary
fix: resolve login validation bug
docs: update project installation guide
```

Awalan yang disebut panitia: **`feat`, `fix`, `docs`, `style`, `refactor`, `chore`**.

Pesan seperti `update`, `test`, atau `final` **ditolak** karena tidak menjelaskan perubahan.

Aturan turunan untuk project ini:

- Satu kalimat, bahasa Inggris, tanpa scope dalam kurung.
- **Tidak ada awalan `test:`.** Test dan implementasinya masuk satu commit `feat:`, yang memang
  bentuk yang benar untuk TDD.
- **Tidak ada baris `Co-Authored-By`.** Seluruh commit harus terbaca sebagai karya anggota tim.
  Larangan ini mutlak dan tanpa pengecualian: tidak untuk AI, dan tidak untuk sesama anggota.
  Aturan yang tidak punya pengecualian tidak bisa disalahgunakan. Larangan ini mengikat agen dan
  subagent; anggota tim yang benar-benar pair programming boleh menambahkan trailernya sendiri
  secara manual, dan itu keputusan mereka. Co-author yang direkayasa masuk kategori manipulasi
  bukti pengembangan, yang hukumannya diskualifikasi.

## Orisinalitas

- Seluruh kode dan komponen utama wajib dikembangkan **selama** Hacking Week.
- Ide, riset, wireframe, dan desain UI/UX boleh disiapkan sebelumnya. **Penulisan kode tidak boleh.**
  Dokumen `.claude/prd/`, `.claude/plan/`, dan `DESIGN.md` masuk kategori riset dan desain, dan
  ditulis 7 sampai 9 November, jadi tetap di dalam Hacking Week.
- Dilarang repositori lama, fork proyek pihak lain, atau memindahkan proyek lama ke repo baru.
- Dilarang template aplikasi lengkap yang hanya diubah identitas atau tampilannya.
- Diperbolehkan: framework, library, package, komponen UI, starter template resmi, API publik,
  model pre-trained, pustaka open-source, dan **AI coding assistant**.
- Tim bertanggung jawab penuh atas seluruh kode, termasuk kode hasil AI, dan wajib mampu
  menjelaskan setiap implementasi teknisnya.

## Kredensial

- **Dilarang hardcode** API key, token, atau password database di repositori.
- Kredensial wajib di `.env`, dan `.env` wajib masuk `.gitignore`.
- Wajib menyediakan **`.env.example`** berisi nama variabel tanpa nilai asli.
- Kebocoran kredensial menjadi tanggung jawab tim.

## Repositori dan README

- Repositori wajib **Public** sejak submission sampai penilaian selesai. Tidak boleh dihapus,
  dipindahkan, atau diprivat.
- Backend dan frontend boleh dalam satu repo, asal **nama foldernya dipisahkan dengan jelas** dan
  dijelaskan di README (klarifikasi panitia, 8 November).
- Branch per fitur diperbolehkan, tetapi **produk final wajib di-merge ke branch utama**
  (klarifikasi panitia, 8 November).
- Repositori yang kosong, tidak memuat kode sumber utama, atau **tidak memiliki README.md**
  dinyatakan tidak memenuhi persyaratan.

### Isi README.md yang diwajibkan

Berada di direktori utama, memuat seluruh poin berikut:

- [ ] Nama tim dan daftar anggota
- [ ] Kategori (Web atau Mobile), nama aplikasi, deskripsi solusi, masalah yang diangkat, target pengguna
- [ ] Daftar fitur utama yang **berhasil** diimplementasikan
- [ ] Teknologi: framework, library, database, API, layanan pihak ketiga
- [ ] **Diagram arsitektur sistem dan alur data**
- [ ] Panduan instalasi, konfigurasi, dan menjalankan aplikasi, termasuk daftar variabel lingkungan
- [ ] **Akun demonstrasi**, karena aplikasi ini memakai autentikasi
- [ ] **Dokumentasi penggunaan AI**: layanan atau model yang dipakai dan bagian produk yang memanfaatkannya
- [ ] Atribusi seluruh template, aset, dataset, dan kode pihak ketiga

Dua poin bertanda tebal paling sering terlewat, dan keduanya menyasar rubrik secara langsung.

## Deploy dan akses juri

- **Web: aplikasi wajib sudah di-deploy dan dapat diakses melalui browser.**
- Akun demonstrasi wajib disediakan.
- Juri tidak boleh diwajibkan membayar, berlangganan, atau punya akses khusus.
- Tim wajib memastikan layanan pendukung, **termasuk kuota API**, tetap aktif selama penilaian.
- Untuk Grand Final: aplikasi wajib bisa dijalankan **localhost** di laptop tim.

## Video demo

- YouTube, status Unlisted atau Public, tidak dihapus sampai pengumuman hasil akhir.
- Durasi **minimal 3 menit 00 detik, maksimal 5 menit 00 detik**. Di luar itu dinyatakan tidak
  memenuhi persyaratan.
- Merekam aplikasi yang **benar-benar berjalan** dari commit final, lewat browser.
- Wajib menampilkan berurutan: tampilan awal dan identitas aplikasi; alur fitur utama dari input,
  proses, hingga output; pembuktian fungsi utama yang diklaim; **proses dan hasil integrasi AI
  secara langsung**.
- Rekaman harus utuh dan berkesinambungan. Penyuntingan hanya boleh memotong waktu tunggu atau
  menambah narasi, teks, dan musik.
- **Dilarang** memakai slide, desain UI/UX, prototype Figma, mockup, animasi, atau simulasi
  sebagai pengganti demonstrasi.

## Berkas submission

| Komponen | Ketentuan |
| --- | --- |
| Repositori GitHub | Tautan publik |
| Video demo | Tautan YouTube, 3 sampai 5 menit |
| Surat Pernyataan Orisinalitas Karya | PDF, format resmi panitia, **bermaterai Rp10.000 atau e-meterai**, ditandatangani Ketua Tim |

Dikumpulkan lewat portal resmi, paling lambat 14 November 2026 pukul 23.59 WIB. Pengiriman lewat
WhatsApp atau email panitia tidak sah.

## Rubrik penilaian

| Kriteria | Bobot | Yang dinilai |
| --- | --- | --- |
| Problem-Solution Fit | 25% | Ketajaman identifikasi masalah dan kesesuaian solusi |
| Technology Innovation | 25% | Kreativitas dan efektivitas teknologi. **Pemanfaatan AI menjadi nilai tambah** |
| Software Engineering | 25% | **Fungsionalitas MVP, kualitas kode, arsitektur sistem, dan dokumentasi** |
| UI/UX | 15% | Kualitas desain antarmuka, kemudahan penggunaan, alur pengguna |
| Digital Ethics & Security | 10% | Etika pengembangan, perlindungan privasi dan data, keamanan dasar, **transparansi penggunaan AI dan atribusi pihak ketiga** |

Bobot ini yang menentukan prioritas saat waktu menipis. Arsitektur berlapis, regression suite,
dan dokumentasi menyasar 25% Software Engineering secara langsung. Transparansi AI dan atribusi
di README menyasar 10% Digital Ethics, dan biayanya hanya beberapa paragraf.

## Subtema yang dipakai

**Local MSME & Creative Economy**: membangun platform atau alat bantu digital yang membantu UMKM
lokal dalam digitalisasi operasional, memperluas akses pasar, atau mengoptimalkan manajemen bisnis.

## Bentuk pelanggaran yang berujung diskualifikasi

- Menyerahkan proyek yang sudah selesai atau sebagian besar dibangun sebelum Hacking Week
- Menggunakan karya atau kode pihak lain tanpa pengembangan substantif dan atribusi
- Melibatkan pihak di luar tim dalam pengembangan bagian utama aplikasi
- **Memanipulasi riwayat commit atau bukti pengembangan**
- Menggunakan rekaman demo palsu, simulasi hasil, atau manipulasi visual
- Mengubah kode atau deployment setelah code freeze untuk memengaruhi penilaian
- Memberikan informasi, dokumen, atau tautan yang tidak benar atau tidak dapat diverifikasi

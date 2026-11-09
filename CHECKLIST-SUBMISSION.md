# Checklist submission Logicodix 2026

Disusun 9 November 2026 dari hasil audit repositori terhadap
[`.claude/docs/aturan-lomba.md`](.claude/docs/aturan-lomba.md).

**Batas submission: 14 November 2026, 23.59 WIB.** Sisa waktu 5 hari. Submission hanya bisa
dikirim satu kali dan bersifat final.

Setiap item di bawah punya tiga bagian: **apa yang dikerjakan**, **siapa yang bisa
mengerjakannya**, dan **cara memverifikasinya selesai**. Item tanpa cara verifikasi tidak
dimasukkan ke daftar ini.

Arti penanda pelaku:

| Penanda | Arti |
| --- | --- |
| **Pemilik** | Hanya Rhama Damarwijaya yang bisa. Butuh akses server, akun GitHub, materai, atau tanda tangan |
| **Tim** | Siapa pun anggota tim, tidak butuh akses khusus |
| **Kode** | Siapa pun yang menulis kode di repo ini, termasuk agen |

---

## Bagian 1. Blokir kelayakan: submission tidak dinilai kalau item ini kosong

Urutannya adalah urutan kerja. Item 1.1 memblokir 1.2, dan 1.2 memblokir 1.5.

### 1.1 Deploy aplikasi ke server yang bisa dibuka juri dari browser

Aturan: "Web: aplikasi wajib sudah di-deploy dan dapat diakses melalui browser." Mockup,
video, atau localhost tidak sah sebagai pengganti.

**Pelaku:** Pemilik. Butuh VPS, domain, dan `GEMINI_API_KEY` sungguhan.

Yang sudah ada di repo: `docker-compose.prod.yml`, `Caddyfile`, `backend/Dockerfile`,
`frontend/Dockerfile`. Image sudah pernah dibangun dan dijalankan lokal. Yang belum ada:
servernya.

Yang masih harus dikerjakan:

1. Sewa VPS, arahkan domain ke IP-nya (A record), tunggu propagasi DNS.
2. Pasang Docker dan Docker Compose di VPS.
3. `git clone` repo ke VPS, buat `.env` di sana dari `.env.example`.
4. Isi `DOMAIN`, `POSTGRES_*`, `DATABASE_URL`, `JWT_SECRET`, `SCORING_ENGINE=gemini`,
   `GEMINI_API_KEY`. `docker-compose.prod.yml` memakai bentuk `${VAR:?}` sehingga compose
   menolak jalan kalau ada yang kosong, jadi variabel yang terlewat akan muncul sebagai
   pesan error saat start, bukan sebagai kerusakan diam-diam nanti.
5. `docker compose -f docker-compose.prod.yml up -d --build`.
6. `docker compose -f docker-compose.prod.yml exec backend alembic upgrade head`.

**Jangan** menyetel `ENV=dev` di server. Router internal (`POST /api/v1/internal/clock/tick`)
hanya terdaftar saat `ENV=dev`, dan membukanya ke internet berarti siapa pun bisa memajukan
jam virtual aplikasi saat juri sedang memakainya.

**Verifikasi:** dari jaringan lain (data seluler, bukan wifi rumah, bukan mesin sendiri),
buka `https://<domain>/` dan `https://<domain>/api/v1/health`. Keduanya harus menjawab tanpa
peringatan sertifikat. Kalau `/api/v1/health` menjawab tapi halaman depan tidak, masalahnya
di container frontend, bukan di Caddy.

### 1.2 Buat akun demonstrasi yang sungguh ada di database produksi

Aturan: README wajib memuat akun demonstrasi, dan "juri tidak boleh diwajibkan membayar,
berlangganan, atau punya akses khusus". Aplikasi ini memakai autentikasi, jadi tanpa akun
juri tidak bisa melihat apa pun selain halaman publik.

**Pelaku:** Pemilik. Harus dijalankan terhadap database produksi.

Tidak ada modul seed di repo ini. `backend/app/seed.py` tidak ada, dan
`POST /api/v1/internal/seed` juga tidak ada di `backend/app/api/v1/internal.py`; router itu
hanya punya `clock/tick` dan `ledger/{proposal_id}`. Commit `085a9e8` berjudul
`fix: seed demo data with a command that works in production` hanya menambah peringatan di
`.claude/plan/phase-13-submission.md`, tidak menambah perintahnya. Jadi saat ini ada dua
jalan:

**Jalan A, manual lewat API.** Tidak butuh kode baru. Registrasi dua akun lewat endpoint
yang sudah berjalan, lalu isi data demo dari UI seperti pengguna biasa: login sebagai
investor, buat campaign, login sebagai UMKM, ajukan proposal, lalu pledge.

```bash
curl -X POST https://<domain>/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"<email>","password":"<password>","name":"<nama>","role":"investor"}'
```

**Jalan B, modul seed.** Butuh kode baru: satu modul yang bisa dijalankan lewat
`docker compose exec backend python -m app.seed`, idempoten, dan memakai logika yang sama
dengan endpoint seed untuk test lokal. Rancangannya sudah ditulis di
`.claude/plan/phase-13-submission.md` lengkap dengan enam proposal contoh dan status yang
diharapkan. Lebih bagus untuk demo karena datanya bercerita, tapi ini pekerjaan **Kode**,
bukan Pemilik, dan harus selesai sebelum 1.1 dijalankan ulang.

Pilih satu. Jalan A cukup untuk memenuhi syarat kelayakan.

**Verifikasi:** dari browser yang belum pernah login (mode incognito), buka
`https://<domain>/masuk`, login dengan kredensial yang akan ditulis di README, dan pastikan
masing-masing peran sampai ke halamannya: investor ke daftar campaign, UMKM ke beranda
proposalnya. Ulangi dengan kredensial yang disalin dari README, bukan dari catatan lain,
supaya salah ketik ikut tertangkap.

### 1.3 Ubah visibility repositori menjadi Public

Aturan: repositori wajib Public sejak submission sampai penilaian selesai, dan tidak boleh
dihapus, dipindahkan, atau diprivat. Repo `rhamaxv/modalink` saat ini **Private**
(diverifikasi 9 November 2026 lewat `gh repo view`).

**Pelaku:** Pemilik.

```bash
gh repo edit rhamaxv/modalink --visibility public
```

Kerjakan ini **setelah** item 2.1 (sinkronisasi README) selesai, karena riwayat commit ikut
terbuka dan tidak bisa diubah setelahnya.

**Verifikasi:** buka `https://github.com/rhamaxv/modalink` dari browser yang tidak login ke
GitHub. Halaman harus terbuka, bukan 404.

### 1.4 Nyalakan Secret scanning dan Push protection

Bukan syarat kelayakan secara langsung, tapi letaknya di sini karena hanya tersedia setelah
repo Public dan akan terlewat kalau dikerjakan belakangan. Percobaan menyalakannya pada
9 November 2026 ditolak dengan `422 Secret scanning is not available for this repository`
karena repo masih private.

**Pelaku:** Pemilik. Settings, Code security.

**Verifikasi:** di halaman Settings, Code security, keduanya tertulis Enabled.

### 1.5 Isi tujuh penanda `[ISI SEBELUM SUBMIT]` di README

README memuat 7 penanda `[ISI SEBELUM SUBMIT]` dan 5 sel `[ISI]`. Satu di antaranya
(baris 11) adalah catatan penjelas, bukan kolom. Enam sisanya adalah kolom yang harus diisi:

| Letak | Isi | Pelaku | Status audit |
| --- | --- | --- | --- |
| Baris 40 sampai 43, tabel Tim | Peran masing-masing dari 4 anggota | Tim | **Bukan nilai yang tidak diketahui.** Tim tahu siapa mengerjakan apa. Ini tertunda, bukan mustahil |
| Baris 462 dan 478 sampai 479, Akun demonstrasi | Email dan password 2 akun | Pemilik | Tergantung item 1.2 |
| Baris 618 dan 630, Deploy | URL aplikasi | Pemilik | Tergantung item 1.1 |

Kolom peran paling penting dari ketiganya untuk alasan yang tidak kelihatan: seluruh 185
commit berasal dari satu akun (`rhamaxv`). Itu sah menurut aturan, yang mematok asal commit
dan bukan sebarannya, tapi empat nama di README dengan satu akun di riwayat adalah hal
pertama yang akan ditanyakan juri. Menjelaskan pembagian kerja lebih dulu lebih kuat
daripada menjawab saat ditanya. Alasan lengkapnya ada di `.claude/docs/tim.md`.

**Jangan mengisi kolom mana pun dengan nilai contoh.** README saat ini sengaja kosong, bukan
diisi tebakan, dan nilai palsu di repositori publik lebih buruk daripada kolom kosong.

**Verifikasi:** `grep -c 'ISI SEBELUM SUBMIT\|\[ISI\]' README.md` harus mengembalikan `0`.

### 1.6 Buat commit final sebelum code freeze, lalu berhenti

Aturan: versi yang dinilai adalah commit hash yang dicantumkan di form submission, dan
commit itu wajib dibuat tidak lebih lambat dari 14 November 2026 pukul 23.59 WIB. Aplikasi
yang di-deploy dan video demo wajib berasal dari commit final itu.

**Pelaku:** Tim, lalu Pemilik untuk pencatatan.

Urutannya mengikat: commit final dulu, lalu deploy ulang dari commit itu, lalu rekam video
dari deployment itu. Kalau ada perbaikan setelah video direkam, videonya harus direkam ulang.

**Verifikasi:**

```bash
git rev-parse HEAD                 # catat hash ini, ini yang masuk form
git log -1 --date=iso-strict --pretty='%H %ad'   # tanggalnya harus sebelum batas
git log origin/main..main --oneline               # harus kosong: semua sudah di-push
```

### 1.7 Rekam video demo YouTube, 3 sampai 5 menit

Aturan: minimal 3 menit 00 detik, maksimal 5 menit 00 detik. Di luar rentang itu dinyatakan
tidak memenuhi persyaratan, bukan dikurangi nilainya. Status Unlisted atau Public, tidak
dihapus sampai pengumuman hasil akhir.

**Pelaku:** Tim. Butuh item 1.1 dan 1.2 sudah selesai.

Yang wajib tampil berurutan: tampilan awal dan identitas aplikasi; alur fitur utama dari
input sampai output; pembuktian fungsi utama yang diklaim; proses dan hasil integrasi AI
secara langsung. Dilarang memakai slide, mockup, prototype Figma, atau simulasi sebagai
pengganti demonstrasi.

Bagian integrasi AI yang paling kuat untuk ditampilkan: ajukan satu proposal, tunjukkan ia
dibalas `201` dengan status `submitted` sebelum AI selesai, lalu buka halaman skornya dan
tunjukkan tiga komponen skor serta red flag beserta kutipan buktinya. Itu memperlihatkan
proses, bukan hanya hasil.

**Verifikasi:** durasi di halaman YouTube terbaca antara 3.00 dan 5.00. Buka tautannya dari
jendela incognito untuk memastikan Unlisted, bukan Private.

### 1.8 Surat Pernyataan Orisinalitas Karya, bermaterai, ditandatangani

Aturan: PDF, format resmi panitia, bermaterai Rp10.000 atau e-meterai, ditandatangani Ketua
Tim.

**Pelaku:** Pemilik. Hanya Rhama Damarwijaya yang bisa menandatanganinya.

Draf isinya ada di [`.claude/docs/submission/surat-orisinalitas.md`](.claude/docs/submission/surat-orisinalitas.md).
Baca catatan di kepala berkas itu lebih dulu: **kalau panitia menyediakan template resmi,
template panitia yang dipakai**, dan draf itu hanya rujukan isi. Draf itu juga memuat satu
keputusan yang harus diambil Ketua Tim soal pengungkapan pemakaian AI, dan keputusan itu
tidak boleh dilewati karena surat bermaterai adalah dokumen pernyataan.

**Verifikasi:** PDF terbuka, materai Rp10.000 atau e-meterai terlihat, tanda tangan ada di
atas atau di sebelah materai, nama dan tanggal terisi, dan tidak ada kolom `[...]` yang
masih berupa penanda.

### 1.9 Pastikan kuota API tetap aktif selama penilaian

Aturan: tim wajib memastikan layanan pendukung, termasuk kuota API, tetap aktif selama
penilaian. Penilaian berlangsung sampai Grand Final 29 November 2026.

**Pelaku:** Pemilik.

Catatan teknis yang meringankan: kegagalan Gemini tidak pernah membuat proposal otomatis
`rejected`. Proposal tetap `submitted` dengan `scoring_status = failed`. Jadi kuota habis
tidak merusak data, tapi juri akan melihat skor yang gagal dan itu menyasar langsung 25%
Technology Innovation.

**Verifikasi:** dari deployment produksi, ajukan satu proposal uji dan pastikan
`GET /api/v1/proposals/{id}/scoring` mengembalikan skor, bukan `scoring_status = failed`.
Ulangi sehari sebelum Grand Final.

### 1.10 Kirim lewat portal resmi, satu kali

Aturan: dikumpulkan lewat portal resmi, paling lambat 14 November 2026 pukul 23.59 WIB.
Pengiriman lewat WhatsApp atau email panitia tidak sah. Submission hanya bisa dikirim satu
kali.

**Pelaku:** Pemilik.

Isi form: tautan repositori publik, tautan YouTube, PDF surat bermaterai, dan commit hash
final. Periksa seluruh tautan dari jendela incognito sebelum menekan submit, karena aturan
menyebut "memberikan informasi, dokumen, atau tautan yang tidak benar atau tidak dapat
diverifikasi" sebagai bentuk pelanggaran yang berujung diskualifikasi.

**Verifikasi:** halaman konfirmasi portal, atau email konfirmasi, disimpan sebagai tangkapan
layar.

---

## Bagian 2. Memengaruhi nilai, bukan kelayakan

### 2.1 Sinkronkan README dengan kode pada commit final

README ditulis pada commit `bfa49ee` (9 November, 16.12 WIB). Dua puluh commit setelahnya
menambah fitur yang README masih sebut belum ada. Ini menyasar 25% Software Engineering
(dokumentasi) dan, lebih buruk, membuat juri meremehkan produk dari dokumennya sendiri.

**Pelaku:** Kode.

Yang sudah usang, diverifikasi terhadap isi repo hari ini:

| Letak | Klaim README | Keadaan sebenarnya |
| --- | --- | --- |
| Yang belum dibangun, butir 1 | Endpoint API milestone belum ada | `backend/app/api/v1/milestones.py` ada, beserta approve, reject, dan laporan progres |
| Yang belum dibangun, butir 2 | Endpoint API komunitas belum ada | `backend/app/api/v1/community.py` ada, vote dan komentar |
| Yang belum dibangun, butir 3 | Transisi otomatis ke `failed` belum ada | `backend/app/services/expiry.py` ada, evaluasi deadline dan refund simulasi |
| Yang belum dibangun, butir 4 | Keempat endpoint internal belum ada | `clock/tick` dan `ledger/{id}` sudah ada. `clock/reset` dan `seed` memang belum |
| Variabel lingkungan, baris terakhir | `.env.example` mendaftarkan `NEXT_PUBLIC_API_BASE` | `.env.example` mendaftarkan `NEXT_PUBLIC_API_URL`. Nama lama sudah tidak ada |
| Pengujian | `434 passed`, frontend `18 files, 103 tests` | Angka dari sebelum 20 commit terakhir. Frontend kini punya 21 berkas test |
| Struktur repositori | Akar diagram bernama `logicodix/` | Nama repositori `modalink` |

Daftar fitur utama juga perlu dibaca ulang: beberapa yang kini berjalan ujung ke ujung belum
tercantum di sana.

**Verifikasi:** untuk setiap butir di bagian "Yang belum dibangun", cari berkasnya. Kalau
berkasnya ada dan punya test, butir itu pindah ke daftar fitur. Angka test diambil dari
keluaran `make test` dan `cd frontend && npm run test` yang sungguh dijalankan pada commit
final, bukan disalin dari versi README ini.

### 2.2 Tambahkan pengungkapan pemakaian AI coding assistant di README

Aturan membolehkan AI coding assistant secara eksplisit, dan mewajibkan tim bertanggung
jawab penuh atas seluruh kode termasuk hasil AI. Rubrik memberi 10% untuk Digital Ethics &
Security yang menilai "transparansi penggunaan AI".

Bagian "Dokumentasi penggunaan AI" di README saat ini hanya membahas Gemini sebagai fitur
produk. Pemakaian AI sebagai alat bantu penulisan kode tidak disebut, padahal `.claude/`
ikut di-commit (43 berkas: PRD, plan, konvensi, skill) dan `CLAUDE.md` ada di akar, sehingga
juri yang membuka repo akan melihatnya sendiri. Menyebutkannya lebih dulu adalah transparansi
yang dinilai; membiarkannya tersimpul sendiri adalah nilai yang ditinggalkan di meja.

**Pelaku:** Kode untuk menulis, Pemilik untuk menyetujui kalimatnya.

**Verifikasi:** README memuat subbagian yang menyebut alat bantu yang dipakai dan batas
tanggung jawab tim atas kode hasilnya. Kalimatnya harus konsisten dengan Surat Pernyataan
Orisinalitas; keduanya dibaca orang yang sama.

### 2.3 Isi About repositori: deskripsi, topics, dan Website

Satu kalimat deskripsi dan baris Website adalah hal pertama yang terbaca juri sebelum mereka
mengklik apa pun. Deskripsi sudah terisi. Topics kosong (`null`) dan Website kosong
(diverifikasi 9 November lewat `gh repo view`).

**Pelaku:** Pemilik.

Topics yang direncanakan di `.claude/docs/panduan-repo.md`: `hackathon`, `umkm`,
`crowdfunding`, `fastapi`, `nextjs`, `postgresql`, `gemini-api`. Website diisi URL deploy
dari item 1.1.

**Verifikasi:** `gh repo view rhamaxv/modalink --json repositoryTopics,homepageUrl` tidak
mengembalikan `null` atau string kosong.

### 2.4 Jaga keberkalaan commit sampai code freeze

Aturan menilai keberkalaan commit selama Hacking Week dan melarang bulk upload. Riwayat saat
ini **tidak melanggar larangan bulk upload**: ada 185 commit, masing-masing berisi perubahan
nyata, bukan satu commit raksasa. Tapi seluruh 185 commit itu bertanggal **9 November 2026**,
tidak ada satu pun pada 7 atau 8 November, dan pushnya terkumpul pada hari yang sama.

Ini tidak bisa diperbaiki ke belakang, dan **tidak boleh** dicoba diperbaiki: mengubah
tanggal commit adalah manipulasi bukti pengembangan, yang hukumannya diskualifikasi. Yang
bisa dilakukan adalah ke depan: pekerjaan yang tersisa (item 2.1, 2.2, dan modul seed kalau
Jalan B dipilih) di-commit dan di-push pada hari ia dikerjakan, 10 sampai 14 November,
sehingga riwayat lima hari terakhir memperlihatkan ritme.

**Pelaku:** Kode.

**Verifikasi:**

```bash
git log --pretty='%ad' --date=short | sort | uniq -c
```

Keluarannya harus memuat lebih dari satu tanggal.

### 2.5 Siapkan aplikasi bisa dijalankan localhost untuk Grand Final

Aturan: untuk Grand Final, aplikasi wajib bisa dijalankan localhost di laptop tim. Ini
berlaku 29 November, bukan 14 November, tapi disiapkan sebelum code freeze karena kodenya
tidak boleh berubah setelahnya.

**Pelaku:** Tim.

**Verifikasi:** pada laptop yang akan dipakai presentasi, dari clone bersih repositori pada
commit final, jalankan `make up` dan `make migrate` sesuai README lalu buka
`http://localhost:3000`. Catat langkah apa pun yang README belum sebut, dan tambahkan ke
README sebelum commit final.

---

## Bagian 3. Sudah selesai dan sudah diverifikasi

Diperiksa pada 9 November 2026 terhadap keadaan repositori, bukan terhadap klaim dokumen.
Perintah verifikasinya dicantumkan supaya bisa diulang pada commit final.

| Aturan | Keadaan | Cara memeriksa ulang |
| --- | --- | --- |
| Awalan pesan commit hanya `feat`, `fix`, `docs`, `style`, `refactor`, `chore` | 185 dari 185 commit patuh. Tidak ada `test:`. Sebaran: 91 feat, 40 fix, 21 docs, 16 chore, 12 refactor, 5 style | `git log --pretty=%s \| grep -vcE '^(feat\|fix\|docs\|style\|refactor\|chore): '` harus `0` |
| Tidak ada `Co-Authored-By` atau atribusi AI di commit mana pun | Nol kecocokan di seluruh subject, body, dan trailer. Satu-satunya kecocokan kata "co-author" adalah subject commit `f7d3399`, yaitu dokumentasi larangannya sendiri | `git log --pretty='%H%n%B%n%(trailers)' \| grep -ciE 'co-author\|claude\|anthropic\|copilot\|generated with'` harus `1` |
| Seluruh commit dari akun anggota terdaftar | Satu penulis: `rhamaxv <rhamaxv@gmail.com>`, author dan committer sama | `git log --pretty='%an <%ae> / %cn <%ce>' \| sort -u` |
| Tidak ada manipulasi tanggal | Author date dan committer date identik pada seluruh 185 commit | `git log --pretty='%h %ad %cd' --date=iso-strict \| awk '{if ($2!=$3) print}'` harus kosong |
| Tidak ada force push, rebase, atau squash | 13 merge commit dari branch worktree, nol squash. Allow squash dan allow rebase sudah dimatikan di setelan GitHub | `git reflog \| grep -i 'rebase\|amend'` dan setelan di Settings, General, Pull Requests |
| Repositori dibuat setelah kick-off | Dibuat 9 November 2026 01.26 WIB, kick-off 7 November. Commit pertama 9 November 01.04 WIB | `gh repo view rhamaxv/modalink --json createdAt` |
| Produk final ada di branch utama | `main` dan `origin/main` sama persis, nol commit belum di-push | `git log origin/main..main --oneline` harus kosong |
| `.env` masuk `.gitignore` dan tidak pernah ter-commit | `.env` dan `.env.*` di `.gitignore` dengan pengecualian `!.env.example`. Nol kemunculan `.env` di seluruh riwayat | `git log --all --full-history --name-only -- .env` harus kosong |
| `.env.example` berisi nama tanpa nilai | 14 variabel, seluruhnya berakhir pada `=` tanpa nilai | `grep -cE '^[A-Z_]+=' .env.example` dan `grep -c '=$' .env.example` harus sama |
| Tidak ada kunci API di riwayat | Nol kecocokan pola `AIza`, `sk-`, `ghp_`, `AKIA`, `BEGIN PRIVATE KEY`, JWT di seluruh 48.153 baris diff riwayat | perintah di `.claude/docs/panduan-repo.md`, bagian Setelan yang mencegah pelanggaran |
| Kredensial tidak masuk image Docker | `.dockerignore` ada di akar, `backend/`, dan `frontend/`, ketiganya menutup `.env` | `cat backend/.dockerignore frontend/.dockerignore \| grep -c '^\.env'` |
| README memuat diagram arsitektur | Diagram Mermaid empat lapisan (router, service, domain, model) di bagian Arsitektur sistem dan alur data | buka README di GitHub setelah repo Public dan pastikan diagram ter-render, bukan tampil sebagai blok kode |
| README memuat dokumentasi penggunaan AI produk | Gemini `gemini-2.5-flash` lewat Instructor, kontrak output, pembagian tugas model dan kode, penjagaan kutipan halusinasi, mode kegagalan | lihat juga item 2.2 soal AI coding assistant yang belum disebut |
| README memuat atribusi pihak ketiga | Daftar framework, library, font, infrastruktur, dan layanan AI, dengan pernyataan tidak ada template atau aset pihak lain yang disalin | |
| README memuat nama tim, kategori, fitur, teknologi, panduan instalasi, dan daftar variabel lingkungan | Seluruhnya ada | lihat item 2.1 soal isinya yang perlu disinkronkan |
| Backend dan frontend dipisah jelas dan dijelaskan di README | `backend/` dan `frontend/` di akar, dijelaskan di bagian Struktur repositori | |
| Tidak ada kredensial di-hardcode di kode saat ini | `backend/app/config.py` tidak punya default untuk `DATABASE_URL` maupun `JWT_SECRET`. CI memakai `${{ secrets.* \|\| 'ci-only-placeholder' }}` | |

---

## Bagian 4. Cacat permanen: didokumentasikan, bukan diperbaiki

Riwayat commit tidak boleh ditulis ulang. Larangan force push, rebase, squash, dan
penghapusan commit bersifat mutlak dan hukumannya diskualifikasi. Jadi hal berikut tetap
ada, dan cara menanganinya adalah jujur tentangnya, bukan merapikannya.

### 4.1 Commit `085a9e8`: pesan menjanjikan perintah yang tidak ada di dalamnya

`fix: seed demo data with a command that works in production` hanya mengubah satu berkas,
`.claude/plan/phase-13-submission.md`, dan isinya adalah peringatan bahwa perintah seed
belum ada. Tidak ada modul seed yang ditambahkan. Ini commit paling akhir di `main`, jadi
siapa pun yang membuka riwayat melihatnya lebih dulu.

Konsekuensi nyatanya bukan soal estetika riwayat: akun demonstrasi adalah syarat kelayakan,
dan commit ini membuatnya terbaca sudah selesai padahal belum. Item 1.2 di atas yang
menutupnya.

**Yang harus dilakukan:** commit berikutnya yang benar-benar menambah modul seed diberi
pesan yang menyebut apa yang ia tambahkan, misalnya
`feat: add idempotent demo seed module runnable in production`. Kalau Jalan A yang dipilih
dan modul seed tidak dibuat, tidak ada yang perlu dikerjakan di sini selain menyadari bahwa
riwayat memuat janji yang tidak ditebus.

### 4.2 Lima commit `feat:` dan `fix:` yang hanya mengubah dokumen rencana

| Commit | Pesan | Yang sebenarnya diubah |
| --- | --- | --- |
| `0399026` | `feat: add the four contract endpoints no task owned and a coverage guard` | hanya `.claude/plan/phase-07-milestone.md` |
| `ba48602` | `feat: add a guard comparing the API contract against registered routes` | hanya `.claude/plan/phase-07-milestone.md` |
| `81c73e9` | `feat: guard the invariant that no failed proposal holds an active pledge` | hanya dua berkas `.claude/plan/` |
| `249bcb2` | `fix: reconcile failed proposals that still hold active pledges` | hanya `.claude/plan/` dan `.claude/prd/` |
| `8af19bc` | `feat: add a task centralizing the domain to column enum bridge` | hanya `.claude/plan/phase-07-milestone.md` |

Kelimanya menulis rencana, bukan kode. Kodenya memang ada, ditulis di commit lain setelahnya
(`c7e876d`, `ef176be`, `c24bc77`), jadi tidak ada klaim fitur yang kosong. Yang salah hanya
awalannya: seharusnya `docs:`. Beberapa commit lain punya masalah serupa tapi lebih ringan
karena pesannya menyebut kata "plan" (`82e13ce`, `065a083`, `7d7a456`, `b06e511`).

Awalan `feat` dan `fix` keduanya ada di daftar yang dibolehkan panitia, dan tidak ada pesan
yang berbunyi `update`, `test`, atau `final`. Jadi ini bukan pelanggaran aturan, hanya
riwayat yang kurang akurat.

**Yang harus dilakukan:** mulai sekarang, commit yang hanya mengubah `.claude/` diberi
awalan `docs:`.

### 4.3 Password database pengembangan dan default JWT secret pernah ada di riwayat

| Nilai | Letak | Commit masuk | Commit keluar |
| --- | --- | --- | --- |
| `POSTGRES_PASSWORD: logicodix` | `docker-compose.yml`, workflow CI, contoh di `.claude/plan/phase-00-fondasi.md` | `2681c64`, `b9631dd` | `9afc5b4`, `ae0851e` |
| `database_url: postgresql+asyncpg://logicodix:logicodix@localhost:5433/logicodix_test` | default di `backend/app/config.py` | `b9631dd` | `9afc5b4` |
| `jwt_secret: "ganti-di-produksi"` | default di `backend/app/config.py` | `b9631dd` | `9afc5b4` |

Pohon kerja saat ini bersih: `config.py` tidak punya default untuk keduanya, dan compose
memakai `${VAR:?}`. Tapi riwayat git ikut publik saat repo dijadikan Public, jadi nilai di
atas akan bisa dibaca siapa pun.

Yang meringankan: ketiganya nilai pengembangan lokal, bukan kredensial produksi, dan tidak
ada satu pun kunci API sungguhan yang pernah masuk. Yang tetap harus dijaga:

**Yang harus dilakukan:** pastikan `POSTGRES_PASSWORD` dan `JWT_SECRET` di server produksi
**bukan** `logicodix` dan **bukan** `ganti-di-produksi`. Ini bukan saran kebersihan, ini
satu-satunya hal yang membuat kebocoran riwayat itu tidak berarti apa-apa.

**Verifikasi:** di VPS, `grep -E '^(POSTGRES_PASSWORD|JWT_SECRET)=' .env` dan pastikan
nilainya acak dan panjang, bukan salah satu dari tiga nilai di atas.

---

## Bagian 5. Yang tidak boleh dilakukan, apa pun alasannya

Diulang di sini karena empat dari lima item pertama di Bagian 1 akan menggoda seseorang
untuk melakukan salah satunya.

| Tindakan | Akibat |
| --- | --- |
| `git push --force`, `git rebase`, squash merge, `git commit --amend` setelah push | Diskualifikasi |
| Menghapus commit atau mengubah tanggal commit | Diskualifikasi |
| Menambahkan `Co-Authored-By` anggota yang tidak mengerjakan commit itu | Manipulasi bukti pengembangan, diskualifikasi |
| Meminta anggota lain membuat commit kosong supaya riwayat terlihat merata | sama |
| Mengubah kode atau deployment setelah code freeze | Diskualifikasi. Pengecualiannya hanya memulihkan ketersediaan layanan tanpa mengubah kode, fitur, atau data |
| Menghapus atau mem-private repo sebelum pengumuman hasil | Submission tidak sah |
| Menyetel `ENV=dev` di server publik | Bukan pelanggaran aturan, tapi membuka `clock/tick` ke internet dan bisa merusak demo saat juri sedang memakainya |
| Mengisi kolom README atau surat orisinalitas dengan nilai contoh yang terlihat nyata | Aturan menyebut informasi atau tautan yang tidak dapat diverifikasi sebagai bentuk pelanggaran |

Kalau ada commit yang salah, perbaiki dengan commit baru. Riwayat yang jujur dan berantakan
jauh lebih aman daripada riwayat rapi yang ditulis ulang.

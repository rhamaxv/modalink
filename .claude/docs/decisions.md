# Keputusan Arsitektur

Dikunci pada 2026-11-07 bersama pemilik project. Setiap baris di sini sudah ditimbang dan
disetujui. Kalau sebuah keputusan terasa salah saat implementasi, ubah dokumen ini dulu dan
bicarakan, jangan diam-diam menyimpang di kode.

---

## D-01. Modular monolith, bukan queue terpisah

FastAPI satu service, dipecah per domain. Job AI dijalankan lewat `BackgroundTasks` di belakang
interface `JobRunner`.

**Kenapa:** satu proses untuk dijalankan, test cepat, dan tidak ada worker yang bisa mati saat demo.

**Ditolak:** ARQ/Celery + Redis. Menambah dua proses dan satu titik gagal demi retry yang belum
dibutuhkan. Kalau nanti perlu, yang berganti cuma satu adapter `JobRunner`, bukan lapisan domain.

**Konsekuensi:** tidak ada retry otomatis saat Gemini gagal. Ditangani dengan kolom
`scoring_status` dan endpoint rescore manual.

---

## D-02. Uang sebagai `BIGINT` rupiah utuh

Tidak ada desimal, tidak ada sen, tidak ada `float`.

**Kenapa:** rupiah tidak dipakai dalam sen. Aritmetika pledge terhadap target jadi eksak, dan
progress bar tidak pernah berhenti di 99,99% karena pembulatan.

**Konsekuensi:** semua konversi tampilan ada di satu tempat (`domain/money.py` di backend,
`lib/money.ts` di frontend). Dilarang memformat rupiah secara ad-hoc di komponen.

---

## D-03. Ledger append-only untuk semua pergerakan dana

`ledger_entries` hanya menerima INSERT. Tidak ada UPDATE, tidak ada DELETE. Saldo dihitung dari
penjumlahan, bukan disimpan di kolom.

**Kenapa:** ini yang membuat invarian uang bisa ditegakkan oleh test. Tanpa ledger, bug "dana
cair dua kali" tidak punya tempat untuk ketangkap.

**Invarian yang ditegakkan regression test R2:**
- jumlah `pledge_in` dikurangi `refund_out` dan `disbursement_out` sama dengan saldo escrow
- total `disbursement_out` tidak pernah melebihi dana terkumpul
- tidak ada entri dengan nominal nol atau negatif
- `idempotency_key` unik, sehingga pemicu ganda tidak menghasilkan dua baris

---

## D-04. State machine terpusat di satu modul

Semua transisi status melewati `domain/transitions.py`. Peta transisi ditulis eksplisit sebagai
data, bukan tersebar sebagai `if` di banyak service.

**Kenapa:** status yang tersebar adalah sumber regresi nomor satu di sistem seperti ini.

**Konsekuensi:** regression test R1 menguji **seluruh matriks** status kali event, yang legal
maupun yang harus ditolak. Menambah satu status berarti menambah satu baris di matriks test,
dan test akan merah sampai itu dilakukan. Itu disengaja.

---

## D-05. `partially_funded` adalah status di database

Dipilih pemilik project di atas alternatif "dihitung saat dibaca".

**Kenapa dipilih:** status terbaca langsung saat melihat tabel, tanpa perlu menjalankan query
agregat.

**Risiko yang diterima:** status bisa melenceng dari jumlah pledge sebenarnya.

**Cara risiko itu ditutup:** hanya satu fungsi, `recompute_funding_status()`, yang boleh menulis
`listed`, `partially_funded`, dan `funded`. Setiap service yang mengubah pledge wajib memanggilnya.
Regression test **R2b** menegakkan `status == f(jumlah pledge aktif)` di setiap titik pemeriksaan,
jadi kode yang menulis status sembarangan akan membuat test merah.

---

## D-06. Deadline dievaluasi lazy, bukan oleh scheduler

Transisi ke `failed` dihitung saat proposal atau campaign dibaca. Ada endpoint
`POST /api/v1/internal/clock/tick` untuk memajukan jam virtual, aktif hanya di mode dev.

**Kenapa:** demo jadi deterministik (juri bisa melihat refund simulasi tanpa menunggu), dan test
tidak perlu `sleep` atau mem-patch jam sistem.

**Konsekuensi:** `domain/clock.py` adalah satu-satunya sumber waktu. Memanggil
`datetime.now()` langsung di service atau router dilarang.

---

## D-07. Gemini di belakang interface, mock untuk semua test

`ScoringEngine` adalah protocol. `GeminiEngine` memakai Instructor dengan `gemini-2.5-flash`.
`MockScoringEngine` deterministik dipakai di seluruh unit dan integration test.

**Kenapa:** test yang memanggil API sungguhan itu lambat, mahal, flaky, dan gagal saat offline.

**Konsekuensi:** kontrak dengan Gemini diuji terpisah sebagai contract test bertanda
`@pytest.mark.live`, di-skip secara default, dijalankan manual dengan `make test-live`.

---

## D-08. Total skor dihitung di Python, bukan diambil dari model

Model menilai tiga komponen (`fit_score`, `data_quality_score`, `impact_score`) dan menandai
red flag. Total, perbandingan dengan threshold, dan verdict dikerjakan oleh kode.

**Kenapa:** angka total yang dikarang model tidak bisa diaudit dan tidak stabil antar pemanggilan.
Model menilai, kode memutuskan.

**Konsekuensi:** kalau model mengembalikan field `total`, field itu dibuang tanpa dibaca.

---

## D-09. Kegagalan teknis tidak pernah berarti penolakan

Error jaringan, timeout, atau schema yang meleset menghasilkan `scoring_status = failed`
sementara status proposal tetap `submitted`.

**Kenapa:** menolak usaha orang karena API sedang down adalah kerusakan produk, bukan keputusan bisnis.

**Ditegakkan oleh regression test R6.**

---

## D-10. Test berjalan di Postgres, bukan SQLite

**Kenapa:** dialectnya berbeda di partial unique index, `CHECK`, `ON CONFLICT`, dan tipe numerik.
Test yang lolos di SQLite tapi jebol di Postgres memberi rasa aman palsu.

**Konsekuensi:** `make test` butuh Postgres hidup. `docker-compose.yml` menyediakan service
`db-test` terpisah dari `db` supaya data dev tidak terhapus oleh test.

---

## D-11. Pledge melebihi sisa dana ditolak dengan 409

Bukan dipotong otomatis ke sisa, bukan diizinkan over-funding.

**Kenapa:** tidak pernah ada kelebihan dana yang harus dikembalikan, dan investor tidak pernah
menerima jumlah yang berbeda dari yang dia ketik. Responsnya menyertakan sisa yang masih bisa didanai.

---

## D-12. Siapa pun yang berperan investor boleh ikut mendanai

Pembuat campaign adalah kurator: dia menentukan sektor, dana target, deadline, dan threshold skor.
Begitu proposal `listed`, investor mana pun boleh patungan.

**Kenapa:** co-funding gotong royong adalah salah satu dari tiga nilai unik produk ini. Membatasi
pledge ke pembuat campaign akan menghapusnya.

---

## D-13. Milestone pertama cair tanpa laporan, tetap butuh approve

Milestone `seq = 1` bisa langsung diajukan begitu proposal `funded`, tanpa laporan progres, tapi
tetap menunggu klik approve dari lead investor.

**Kenapa:** sesuai pola "50% di awal" di PRD, dan tetap menyisakan momen "investor menyetujui
pencairan" yang bisa ditunjukkan saat demo. Milestone `seq > 1` wajib disertai laporan, dan
`seq N` baru bisa dilaporkan setelah `seq N-1` cair.

---

## D-14. Auth JWT di FastAPI

Email dan password, hash dengan argon2, access token JWT berisi role.

**Kenapa:** tanpa dependency eksternal, dan role guard jadi FastAPI dependency biasa yang bisa
diuji langsung. Regression test R5 menguji matriks endpoint kali role secara penuh.

---

## D-15. antislop dipakai dalam mode DURING, dengan arah dari pemilik

Keenam modul antislop terpasang. Arah visual ditentukan pemilik project dan tertulis di `DESIGN.md`.

**Kenapa mode DURING:** mencegah slop muncul sejak awal lebih murah daripada mengaudit dan
mengerjakan ulang.

**Konsekuensi:** setiap penyerahan UI ditutup dengan Delivery Gate berupa laporan PASS/FAIL per
aturan, dengan bukti, bukan klaim.

---

## D-16. Campaign punya dua deadline, bukan satu

`apply_deadline` membatasi pengajuan proposal. `funding_deadline` membatasi terkumpulnya dana, dan
wajib setelah `apply_deadline`.

**Kenapa:** doc awal hanya punya satu deadline dan memakainya untuk dua hal sekaligus. Akibatnya
proposal yang masuk di hari terakhir punya jendela pendanaan nol detik dan langsung `failed`. Itu
efek samping, bukan aturan yang dimaksudkan.

**Ditolak:** jendela per proposal (`listed` + N hari). Lebih adil bagi yang mengajukan belakangan,
tapi membuat setiap proposal punya deadline berbeda sehingga sulit dibaca sekilas di daftar.

**Konsekuensi:** campaign `closed` berhenti menerima proposal baru, tetapi pendanaan proposal yang
sudah masuk tetap berjalan sampai `funding_deadline` ([BR-65](../prd/07-business-rules.md)).

---

## D-17. Aturan lomba adalah batasan keras, di atas preferensi teknis

Guidebook Logicodix 2026 disarikan ke [aturan-lomba.md](aturan-lomba.md) dan mengikat seluruh
pengerjaan.

**Kenapa:** pelanggarannya tidak menurunkan nilai, melainkan membatalkan submission atau
mendiskualifikasi tim. Tidak ada keputusan teknis yang sepadan dengan risiko itu.

**Konsekuensi yang mengubah rencana awal:**

- Format commit dipatok panitia. Awalan `test:` dibuang; test masuk commit `feat:` yang sama
  dengan implementasinya.
- Riwayat commit tidak boleh diubah setelah push. Tidak ada rebase, squash, atau amend.
- Deploy yang bisa diakses juri menjadi deliverable wajib, bukan tambahan.
- README wajib memuat diagram arsitektur, akun demonstrasi, dan dokumentasi penggunaan AI.

---

## D-18. Deploy ke VPS sendiri dengan Docker Compose dan Caddy

Dipilih pemilik project di atas Vercel plus Railway.

**Kenapa dipilih:** kontrol penuh, satu lingkungan yang sama persis dengan pengembangan lokal,
dan tidak bergantung pada free tier penyedia yang bisa tidur sendiri saat juri membuka aplikasi.

**Risiko yang diterima:** butuh domain, HTTPS, dan waktu setup yang tidak kecil di tengah tenggat
yang mepet.

**Cara risiko itu ditekan:** Caddy mengurus sertifikat Let's Encrypt secara otomatis sehingga
tidak ada konfigurasi sertifikat manual, dan `restart: unless-stopped` pada seluruh service
membuat stack hidup kembali sendiri setelah VPS reboot.

---

## D-19. Kedalaman test dipangkas, regression suite tidak

Dengan tenggat 14 November, integration test per-endpoint dikurangi ke jalur kritis. Keenam
kelompok regression R1 sampai R6 dan seluruh unit test lapisan `domain/` tetap penuh.

**Kenapa:** rubrik memberi 25% untuk Software Engineering yang menilai kualitas kode, arsitektur,
dan dokumentasi. Regression suite dan lapisan domain murni adalah yang menunjukkan ketiganya.
Integration test ke-tujuh untuk endpoint yang sama tidak menambah apa pun, baik di mata juri
maupun di mata pemeliharaan.

**Yang tidak dipangkas sama sekali:** deploy, README sesuai spesifikasi panitia, video demo, dan
surat orisinalitas. Keempatnya menentukan submission diterima atau tidak.

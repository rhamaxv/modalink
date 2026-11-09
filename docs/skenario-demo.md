# Skenario Demo, 5 menit

> **Catatan lokasi berkas:** brief Fase 13 meminta berkas ini di `docs/skenario-demo.md`
> (akar repo). Agen yang menulis berkas ini dibatasi hanya menyentuh `backend/` untuk
> menghindari konflik dengan agen lain yang berjalan paralel di worktree yang sama, jadi
> berkas ini sementara ada di `backend/docs/skenario-demo.md`. Pindahkan ke `docs/` di akar
> repo saat menggabungkan hasil kerja beberapa agen.

Setiap langkah di bawah **sudah dijalankan sungguhan** lewat HTTP (curl) terhadap server
`uvicorn` yang berjalan di atas basis data ini, bukan ditulis dari rencana. Yang **belum**
dijalankan adalah klik sungguhan di browser: frontend tidak dijalankan saat menulis skenario
ini (di luar cakupan tugas, dan `frontend/node_modules` belum terpasang di lingkungan
penulisan). Bagian "Yang belum sempat dicoba" di akhir berkas ini menyebutnya eksplisit.

## Persiapan

```
make up
docker compose exec backend python -m app.seed
```

Atau untuk mencoba secara lokal tanpa Docker (`ENV=dev` di `.env`):

```
cd backend && .venv/bin/uvicorn app.main:app
curl -X POST localhost:8000/api/v1/internal/seed
```

`SCORING_ENGINE=mock` secara default, jadi seluruh skenario di bawah tidak butuh jaringan
maupun kuota Gemini. Password seluruh akun demo: **`Demo#Modalink2026`** (sama untuk
ketujuhnya, lihat `app/seed/demo.py` untuk daftar emailnya).

## Jalannya skenario

| Menit | Yang ditunjukkan | Kalimat kunci |
| --- | --- | --- |
| 0:00 | `POST /internal/seed` sekali di awal. Buka daftar proposal publik (`GET /proposals`): 4 proposal tampil (dua `listed`, satu `partially_funded`, satu `funded`). | "Ini daftar yang dilihat investor. Dua proposal lain sudah tersaring otomatis sebelum sampai ke sini." |
| 0:30 | Masuk sebagai `investor2@demo.example.com` (pembuat campaign kedua) dan buka daftar proposal campaign itu: dua proposal yang tersaring kini terlihat, keduanya `rejected`, dengan skor 90 dan 48. | "Yang satu ditolak karena skornya rendah. Yang satu lagi skornya 90 dari 100, tapi tetap ditolak." |
| 1:00 | Buka `GET /proposals/{id}/scoring` milik "Peternakan Lele Instan": `red_flags` berisi level `critical`, `brief.risks` menyebut ini engine tiruan. | "AI tidak menolak karena angkanya kecil. Ia menolak karena ada red flag kritis pada proyeksinya, dan alasannya tercatat di baris ini." |
| 1:30 | Masuk sebagai `investor1@demo.example.com` (belum pernah pledge di seed). `POST /proposals/{id}/pledges` ke "Kerajinan Rotan Pak Dedi" (`partially_funded`, sisa Rp12.000.000 dari seed). | "Satu proposal bisa menerima pledge dari investor mana pun, tidak harus investor yang membuat campaign-nya." |
| 2:00 | Buka proposal "Katering Bu Yanti" (`funded`, dua investor patungan: Rp18.000.000 dan Rp12.000.000). Lihat milestone pertama sudah `disbursed`, milestone 2 dan 3 masih `pending`. | "Dua investor menutup dana ini bersama-sama. Dana cair tahap demi tahap, bukan sekaligus." |
| 2:30 | Sebagai `umkm3@demo.example.com`, `POST /milestones/{id}/reports` untuk milestone kedua. Sebagai `investor2@demo.example.com` (lead investor, pledge terbesar), `POST /milestones/{id}/reject` dengan alasan "belum semua belanja tercatat". | "Lead investor bisa menolak laporan yang belum lengkap, bukan menyetujui begitu saja." |
| 3:15 | UMKM mengirim laporan revisi dengan data lebih lengkap. Lead investor `POST /milestones/{id}/approve`: milestone kedua jadi `disbursed`. | "Ini yang tidak ada di platform crowdfunding biasa: UMKM harus merevisi dulu sebelum dana cair." |
| 4:00 | Ulangi lapor-dan-approve untuk milestone ketiga (tanpa revisi). Proposal berubah status jadi `completed` begitu seluruh milestone cair. | "Tahap terakhir cair, dan sistem sendiri yang menandai proposal ini selesai." |
| 4:30 | `GET /internal/ledger/{proposal_id}` untuk "Katering Bu Yanti": lima baris (dua `pledge_in`, tiga `disbursement_out`), saldo akhir nol. | "Setiap rupiah punya barisnya sendiri dan bisa ditelusuri. Tidak ada kolom saldo yang diam-diam diubah." |
| 4:50 | Jalankan `make test-regression` di terminal. | "Dan ini yang menjaganya tetap benar setiap kali ada perubahan kode." |

## Pertanyaan yang mungkin datang

| Pertanyaan | Jawaban |
| --- | --- |
| "Uangnya benar-benar berpindah?" | Tidak. Seluruh pergerakan dana adalah pencatatan di `ledger_entries`, tidak ada payment gateway. Itu memang disebut terus terang sebagai roadmap, bukan disembunyikan (lihat `.claude/plan/phase-13-submission.md`). |
| "Bagaimana kalau AI-nya salah?" | Ambang skor (`score_threshold`) diset investor lewat campaign, bukan platform. Red flag selalu menyertakan `evidence`, dan kalau pemanggilan AI sungguhan gagal (timeout, kuota), proposal tidak pernah ditolak begitu saja: `scoring_status` jadi `failed`, status proposal tetap `submitted`, menunggu dinilai ulang (`POST /proposals/{id}/rescore`). |
| "Kenapa cuma lead investor yang approve milestone?" | Supaya tidak perlu voting setiap kali satu tahap dana mau cair. Lead investor dihitung otomatis dari jumlah pledge terbesar (`recompute_funding_status`), bukan ditunjuk manual. |
| "Datanya asli?" | Tidak. Setiap `business_profile` hasil seed membawa kalimat "Profil usaha ini adalah data contoh untuk demonstrasi Logicodix 2026, bukan usaha sungguhan." secara eksplisit (lihat `app/seed/demo.py`). |
| "Kenapa `evidence` red flag-nya cuma tulisan `[[RED_FLAG:critical]]`, bukan kutipan kalimat?" | Karena demo berjalan dengan `MockScoringEngine` (deterministik, tanpa jaringan): penandanya memang literal seperti itu, disengaja supaya skornya tidak pernah berubah antar-pemutaran. Dengan Gemini sungguhan (`SCORING_ENGINE=gemini`), `evidence` berisi kutipan asli dari isi proposal, bukan penanda ini. Lihat "Yang belum sempat dicoba" di bawah. |

## Yang belum sempat dicoba

- **Klik sungguhan di browser/frontend.** Seluruh langkah di atas diverifikasi lewat HTTP
  (curl) terhadap API, bukan lewat UI Next.js. Presenter sebaiknya menjalankan sekali penuh
  di browser sebelum rekaman untuk memastikan tampilan (panel skor, badge status, progress
  bar funding) benar-benar menampilkan field yang sama dengan yang diverifikasi di sini.
- **Jalur dengan Gemini sungguhan (`SCORING_ENGINE=gemini`).** Skenario ini memakai mock
  engine sesuai arahan fase (`.claude/plan/phase-13-submission.md`: "SCORING_ENGINE=mock,
  jadi tidak ada ketergantungan jaringan"). `make test-live` menguji jalur Gemini secara
  terpisah dan harus dijalankan sekali sebelum submission untuk memastikan jalurnya hidup,
  tapi itu bukan bagian dari video demo 5 menit ini.
- **Proposal berstatus `failed` (refund setelah deadline lewat).** Seed sengaja tidak
  membuatnya: `10-api-contract.md` mematok kontrak seed sebagai 3 investor, 4 UMKM, 2
  campaign, 6 proposal dengan status `{listed, partially_funded, funded, rejected}` -- empat
  status itu saja, bukan lima. Jalur refund tetap bisa ditunjukkan secara terpisah di
  lingkungan lokal (`ENV=dev`) lewat `POST /internal/clock/tick` untuk memajukan jam virtual
  melewati `funding_deadline` salah satu proposal, tapi endpoint itu sendiri tidak ada di
  deployment yang dilihat juri (BR-63), jadi disebut di sini sebagai demo tambahan opsional,
  bukan bagian dari skenario utama.

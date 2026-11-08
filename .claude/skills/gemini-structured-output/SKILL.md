---
name: gemini-structured-output
description: Aturan menyentuh AI scoring di Logicodix. Gunakan saat mengubah prompt, schema output, rubrik skor, atau engine penilaian. Memuat pembagian tugas antara model dan kode, penanganan kutipan halusinasi, mode kegagalan, dan cara menguji tanpa memanggil Gemini.
---

# AI scoring di Logicodix

Provider: Google Gemini `gemini-2.5-flash` lewat Instructor, di belakang protocol `ScoringEngine`.

## Pembagian tugas yang tidak boleh dibalik

**Model menilai. Kode memutuskan.**

| Dikerjakan model | Dikerjakan kode |
| --- | --- |
| `fit_score`, `data_quality_score`, `impact_score` | penjumlahan total |
| daftar `red_flags` beserta kutipan bukti | perbandingan dengan `score_threshold` |
| `brief`: kekuatan, risiko, rekomendasi | keputusan `listed` atau `rejected` |

Schema `ProposalScore` **tidak punya field `total`**, dan itu disengaja. Kalau model
mengembalikannya, Pydantic mengabaikannya. Angka total yang dikarang model tidak bisa diaudit dan
tidak stabil antar-pemanggilan.

Prompt **tidak** memuat `score_threshold`. Model tidak perlu tahu ambangnya, supaya penilaiannya
tidak condong menyesuaikan ambang.

## Rentang pada schema adalah penjaga, bukan dokumentasi

```python
fit_score: int = Field(ge=0, le=40)
```

Kalau model mengembalikan 95, Instructor mengirim ulang permintaan dengan pesan validasinya.
Kalau setelah retry tetap gagal, mode kegagalan di bawah yang berlaku. Melonggarkan rentang untuk
"mengurangi error" berarti menyerahkan skala penilaian ke model.

## Kutipan halusinasi

Setiap `RedFlag` wajib membawa `evidence` berupa kutipan **persis** dari isi proposal. Setelah
pemanggilan, `buang_evidence_halusinasi()` membuang red flag yang kutipannya tidak ada di isi
proposal.

Sadari konsekuensinya: membuang red flag kritis yang halusinasi berarti proposal itu tidak jadi
ditolak. Itu memang pilihan yang diambil. Kutipan karangan yang ditampilkan ke pemilik usaha
sebagai alasan penolakan lebih merusak daripada satu red flag yang terlewat.

Pembandingan mengabaikan beda spasi dan huruf besar, tapi tidak mengabaikan parafrase.

## Mode kegagalan: tidak satu pun menolak proposal

| Yang terjadi | Hasilnya |
| --- | --- |
| Timeout, error jaringan | `scoring_status = failed`, proposal tetap `submitted` |
| Output gagal validasi setelah retry | sama |
| API key tidak ada | sama, plus peringatan saat startup |
| Job terpicu dua kali | transisi kedua tidak ditulis karena compare-and-set |

Menulis `proposal.status = REJECTED` di dalam blok `except` adalah pelanggaran paling berbahaya
di repo ini. Regression test **R6** yang menegakkannya.

## Menguji tanpa memanggil Gemini

Seluruh unit dan integration test memakai `MockScoringEngine`, yang deterministik dan tidak
menyentuh jaringan. Dua penanda yang hanya dikenali mock:

| Penanda di teks proposal | Efek |
| --- | --- |
| `[[SCORE:59]]` | memaksa total menjadi 59, untuk menguji perbatasan threshold dengan tepat |
| `[[RED_FLAG:critical]]` | memunculkan red flag dengan level itu |

Penanda ini tidak pernah dikirim ke Gemini.

Mock harus tetap masuk akal: proposal yang lebih lengkap harus mendapat skor lebih tinggi daripada
yang tipis. Mock yang memberi skor acak membuat seluruh integration test kehilangan arti.

## Contract test

`tests/contract/test_gemini_scoring.py`, ditandai `@pytest.mark.live`, di-skip default, dijalankan
dengan `make test-live`.

Jalankan setiap kali **prompt atau schema berubah**. Empat hal yang diuji:

1. Output lolos validasi `ProposalScore`.
2. Tiga proposal uji (bagus, biasa, red flag) menghasilkan urutan skor yang benar.
3. Proyeksi berlebihan memicu red flag berlevel `critical`.
4. Setiap `evidence` benar-benar ada sebagai substring di isi proposal.

Poin keempat paling sering jebol saat prompt diubah, dan paling berguna.

## Mengubah prompt

Prompt ada di `backend/app/ai/prompts/score_proposal.md`, bukan sebagai string di dalam kode
Python, supaya diff-nya bisa dibaca tanpa menembus kode.

Setelah mengubahnya:

1. Jalankan `make test-live` dan catat hasilnya.
2. Kalau urutan skor berubah drastis, periksa rubrik di `.claude/prd/11-ai-scoring-spec.md`.
3. Perbarui spec kalau rubriknya memang berubah. Prompt dan spec tidak boleh saling mendahului.

## Daftar periksa

- [ ] Schema tidak punya field `total`
- [ ] Prompt tidak memuat `score_threshold`
- [ ] Setiap komponen punya batas rentang di Pydantic
- [ ] `buang_evidence_halusinasi()` dipanggil setelah setiap pemanggilan sungguhan
- [ ] Tidak ada penulisan status proposal di dalam blok `except`
- [ ] Tidak ada test di luar `tests/contract/` yang menyentuh jaringan
- [ ] `make test-regression` hijau, R6 khususnya
- [ ] Kalau prompt berubah: `make test-live` dijalankan, hasilnya dicatat

---
name: testing-and-regression
description: Disiplin test wajib di Logicodix dan gerbang sebelum mengklaim pekerjaan selesai. Gunakan setiap kali menulis test, menyelesaikan sebuah task, atau hendak bilang sesuatu sudah beres. Memuat empat lapis test, enam kelompok invarian regression, dan aturan bahwa klaim selesai harus disertai output perintah.
---

# Test dan regression di Logicodix

## Gerbang sebelum bilang selesai

Tidak ada pekerjaan yang boleh disebut selesai sampai **semuanya** benar:

1. Test yang ditulis lebih dulu memang pernah merah karena alasan yang benar.
2. Test itu sekarang hijau.
3. `make test-regression` hijau.
4. `make check` lolos.
5. Kalau menyentuh UI: Delivery Gate antislop dijalankan dan laporannya disertakan.

**Klaim selesai harus disertai output perintahnya**, bukan ringkasan. "Semua test lolos" tanpa
output bukan bukti. Kalau ada yang gagal, katakan apa adanya beserta outputnya.

## Empat lapis

| Lapis | Direktori | Menjawab | Butuh |
| --- | --- | --- | --- |
| Unit | `tests/unit/` | Apakah aturannya benar? | tidak ada |
| Integration | `tests/integration/` | Apakah endpointnya menyambung? | Postgres |
| Regression | `tests/regression/` | Apakah invarian sistem masih berdiri? | Postgres |
| Contract | `tests/contract/` | Apakah Gemini masih menepati kontraknya? | Gemini, API key |

Kalau sebuah test di `unit/` butuh database, logikanya salah tempat. Pindahkan ke `domain/`.

## Enam kelompok invarian

Ini bukan test per fitur. Ini pernyataan tentang apa yang harus selalu benar, apa pun yang baru
ditambahkan.

| Kelompok | Menjaga | Menangkap |
| --- | --- | --- |
| **R1** | Matriks transisi lengkap, legal maupun yang harus ditolak | status baru yang lupa dipetakan, transisi yang diam-diam diizinkan |
| **R2** | Invarian ledger | dana cair dua kali, refund yang menghapus alih-alih mencatat |
| **R2b** | Status funding cocok dengan jumlah pledge | kode yang menulis status di luar `recompute_funding_status()` |
| **R3** | Happy path end-to-end | apa pun yang memutus rantai |
| **R4** | Jalur gagal | refund yang tidak jalan, pledge berlebih yang lolos |
| **R5** | Matriks RBAC endpoint kali peran | endpoint baru tanpa guard, guard yang lupa memeriksa kepemilikan |
| **R6** | Kegagalan AI tidak pernah menolak proposal | pelanggaran D-09, yang tidak terlihat sampai Gemini down |

Rinciannya di `.claude/plan/regression-checklist.md`.

## Regression suite harus tumbuh

Menambah status, endpoint, atau jenis entri ledger berarti menambah baris di suite. Beberapa test
sengaja dibuat merah kalau itu tidak dilakukan:

- `test_r1_jumlah_transisi_proposal_sesuai_spec` mengunci jumlah transisi
- `test_r5_setiap_route_punya_baris_di_matriks` memindai route terdaftar

Keduanya terasa menjengkelkan, dan itu memang maksudnya.

## Enam aturan yang menjaga suite tetap berguna

1. **Test ditulis lebih dulu dan harus pernah merah.** Test yang tidak pernah merah tidak
   membuktikan apa pun. Kalau sebuah test langsung hijau, periksa apakah ia benar-benar menguji
   sesuatu.
2. **Satu test, satu alasan gagal.** Test yang bisa merah karena lima sebab tidak memberi tahu
   apa-apa saat merah.
3. **Nama test menyebut nomor aturan.** `test_br21_pledge_melebihi_sisa_ditolak`.
4. **Tidak ada `sleep`.** Waktu dikendalikan lewat `domain/clock.py` dan `FrozenClock`.
5. **Tidak ada ketergantungan urutan eksekusi.** Semua fixture di-rollback.
6. **Tidak ada jaringan di luar lapis contract.**

## Membuktikan sebuah pagar benar-benar bekerja

Untuk test yang menjaga hal halus seperti penguncian baris, buktikan sekali bahwa ia bisa merah:
hapus sementara `with_for_update()`, jalankan testnya, pastikan merah, lalu kembalikan.

Pagar yang tidak pernah terbukti bisa merah adalah pagar yang mungkin tidak memagari apa pun.

## Saat menemukan bug di luar test

Pertanyaannya bukan "bagaimana memperbaikinya", melainkan **"invarian mana yang seharusnya
menangkapnya"**.

1. Tambahkan kasusnya ke kelompok R yang sesuai.
2. Pastikan merah.
3. Baru perbaiki kodenya.

Kalau bug itu tidak masuk kelompok mana pun, itu tanda ada invarian yang belum pernah dituliskan.
Tulis kelompok baru.

## Perintah

```
make test              # unit + integration + regression
make test-unit         # paling cepat, dipakai saat menulis domain
make test-regression   # gerbang wajib sebelum klaim selesai
make test-live         # contract test Gemini, manual
make test-fe           # vitest
make test-e2e          # playwright
make check             # ruff + mypy + eslint + tsc + seluruh test
```

---
name: state-machine-guard
description: Aturan menyentuh status apa pun di Logicodix. Gunakan sebelum menambah status, menambah transisi, atau menulis kode yang mengubah status proposal, milestone, laporan, atau campaign. Status yang tersebar adalah sumber regresi nomor satu di sistem ini.
---

# Menyentuh status di Logicodix

Ada empat mesin status: proposal, milestone, laporan milestone, campaign. Semuanya ditulis sebagai
data di `backend/app/domain/transitions.py`.

## Aturan pertama

**Tidak ada kode yang boleh menulis status dengan assignment langsung.** Semua lewat
`apply_proposal()` atau `apply_milestone()`, yang melempar `IllegalTransition` untuk kombinasi
yang tidak ada di peta.

```python
# Salah: transisi ilegal lolos tanpa suara.
proposal.status = ProposalStatus.FUNDED

# Benar: kombinasi yang tidak sah melempar IllegalTransition, yang jadi 409 di HTTP.
proposal.status = apply_proposal(proposal.status, ProposalEvent.PLEDGE_PENUH)
```

## Aturan kedua: status funding punya satu penulis

`listed`, `partially_funded`, dan `funded` **hanya** boleh ditulis oleh
`recompute_funding_status()` di `services/pledge.py`.

Fungsi itu menghitung ulang dari jumlah pledge aktif, jadi statusnya tidak bisa melenceng dari
angka sebenarnya. Setiap service yang menambah atau membatalkan pledge wajib memanggilnya di
transaksi yang sama.

Ini adalah penutup risiko dari keputusan [D-05](../../docs/decisions.md): menyimpan
`partially_funded` sebagai status di database, bukan menghitungnya saat dibaca. Regression test
**R2b** yang menegakkannya.

## Menambah status baru

Lima langkah, berurutan, dan tidak boleh ada yang dilewati:

1. Tambahkan ke tabel di `.claude/prd/08-state-machines.md` dengan nomor `T-xx` baru.
2. Tambahkan ke enum di `domain/transitions.py`.
3. Tambahkan entri ke peta transisi, dengan nomor `T-xx` sebagai komentar di barisnya.
4. Perbarui jumlah yang dikunci di `test_r1_jumlah_transisi_proposal_sesuai_spec`.
5. Jalankan `make test-regression`. R1 akan menguji seluruh kombinasi baru secara otomatis.

Langkah 4 terasa menjengkelkan, dan memang disengaja. Tanpa itu, seseorang bisa menambah transisi
dan seluruh suite tetap hijau meski spec tidak pernah diperbarui.

## Status terminal

`rejected`, `failed`, dan `completed` tidak punya jalan keluar. Ada test yang memastikan tidak ada
satu pun entri di peta yang berawal dari ketiganya.

Kalau sebuah kebutuhan baru menuntut keluar dari status terminal, itu bukan transisi baru,
melainkan tanda bahwa statusnya salah sejak awal. Bicarakan dulu.

## `scoring_status` bukan status proposal

Keduanya kolom terpisah dan tidak boleh dicampur.

| Kolom | Nilai | Artinya |
| --- | --- | --- |
| `proposal.status` | submitted, listed, ... | posisi proposal dalam siklus pendanaan |
| `proposal.scoring_status` | pending, processing, done, failed | posisi job penilaian AI |

`scoring_status = failed` berarti **penilaian gagal dijalankan**, bukan proposal ditolak. Proposal
yang penilaiannya gagal tetap `submitted` dan bisa dinilai ulang. Ini
[D-09](../../docs/decisions.md), ditegakkan oleh regression test **R6**.

Menulis `proposal.status = REJECTED` di dalam blok `except` adalah pelanggaran paling berbahaya
di seluruh repo ini, karena akibatnya adalah menolak usaha orang karena API sedang down.

## Compare-and-set untuk job

Job yang bisa terpicu dua kali harus memeriksa status sebelum menulis:

```python
if proposal.status is not ProposalStatus.SUBMITTED:
    return   # job kedua tidak melakukan apa-apa (BR-75)
```

## Daftar periksa

- [ ] Tidak ada assignment status langsung di luar `transitions.py` dan `recompute_funding_status()`
- [ ] Status baru sudah masuk ke spec, enum, peta, dan jumlah yang dikunci di R1
- [ ] `IllegalTransition` diterjemahkan menjadi `409` dengan `current_status` di `detail`
- [ ] Tidak ada penulisan `status = REJECTED` di dalam blok `except`
- [ ] `make test-regression` hijau, R1 dan R2b keduanya

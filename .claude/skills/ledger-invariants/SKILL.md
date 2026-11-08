---
name: ledger-invariants
description: Aturan menyentuh uang di Logicodix. Gunakan sebelum menulis kode yang mencatat pledge, refund, atau pencairan dana, atau saat menambah jenis pergerakan dana baru. Memuat aturan append-only, idempotensi, penguncian baris, dan invarian yang wajib tetap berdiri.
---

# Menyentuh uang di Logicodix

Tidak ada uang sungguhan yang berpindah di produk ini. Itu justru alasan aturannya harus ketat:
tanpa bank yang menolak, satu-satunya yang menahan kesalahan adalah kode dan testnya.

## Tiga aturan yang tidak bisa dilanggar

**1. `ledger_entries` hanya menerima INSERT.** Tidak ada UPDATE, tidak ada DELETE, termasuk untuk
koreksi. Koreksi adalah entri baru ke arah berlawanan.

**2. Saldo tidak pernah disimpan.** Tidak ada kolom `balance` di mana pun di skema. Saldo dihitung
dari penjumlahan entri setiap kali dibutuhkan. Kolom saldo yang di-update adalah tempat lahirnya
bug "dana cair dua kali".

**3. Setiap entri punya `idempotency_key` yang berasal dari sumber kejadiannya.**

| Kejadian | Pola kunci |
| --- | --- |
| Pledge masuk | `pledge:{pledge_id}` |
| Pledge dibatalkan | `refund:{pledge_id}` |
| Milestone cair | `disburse:{milestone_id}` |

Unique constraint pada kolom itu yang membuat approve ganda hanya menghasilkan satu pencairan,
bukan harapan bahwa tidak ada yang mengklik dua kali.

## Dua angka yang mirip tapi berbeda

```python
total_terkumpul(entri)   # pledge_in dikurangi refund_out
hitung_saldo(entri)      # total_terkumpul dikurangi disbursement_out
```

| Dipakai untuk | Fungsinya |
| --- | --- |
| Bilah progres funding, pengecekan sisa dana | `total_terkumpul` |
| Apakah dana cukup untuk dicairkan | `hitung_saldo` |

Mencampurnya membuat bilah progres turun setiap kali milestone cair, dan itu bug yang membingungkan
investor tanpa pernah melempar error.

## Penguncian baris

Setiap operasi yang **membaca lalu menulis** uang pada satu proposal harus mengambil proposalnya
lewat `ambil_proposal_terkunci()`, yang memakai `SELECT ... FOR UPDATE`.

Tanpa itu: dua investor pledge bersamaan, keduanya membaca "sisa Rp3 juta", keduanya lolos
pemeriksaan, total melampaui dana yang diminta. Pemeriksaan di Python tidak bisa mencegahnya.

Berlaku untuk: pledge, pembatalan pledge, approve milestone, dan evaluasi kedaluwarsa.

## Invarian yang wajib tetap berdiri

Regression test **R2** memeriksanya setelah setiap operasi, bukan hanya di akhir:

- jumlah `pledge_in` dikurangi `refund_out` dan `disbursement_out` sama dengan saldo escrow
- total `disbursement_out` tidak pernah melebihi dana terkumpul
- tidak ada entri dengan nominal nol atau negatif; arah ada di `entry_type`, bukan di tanda angka
- `idempotency_key` benar-benar unik
- himpunan baris lama tetap menjadi himpunan bagian dari yang baru, sehingga UPDATE dan DELETE
  tertangkap

## Menambah jenis entri baru

1. Tambahkan ke enum `EntryType`.
2. Putuskan arahnya: masuk atau keluar, lalu masukkan ke himpunan `MASUK` atau `KELUAR` di
   `services/ledger.py`.
3. Tentukan pola `idempotency_key`-nya dan tulis di tabel pada skill ini.
4. Tambahkan kasusnya ke R2.
5. Perbarui `.claude/prd/09-data-model.md`.

Langkah 2 mudah terlewat, dan akibatnya saldo salah hitung tanpa ada yang melempar error.

## Daftar periksa

- [ ] Tidak ada UPDATE atau DELETE pada `ledger_entries`
- [ ] Tidak ada kolom saldo yang disimpan
- [ ] Setiap entri punya `idempotency_key` dengan pola yang terdaftar
- [ ] Operasi yang membaca lalu menulis uang memakai `ambil_proposal_terkunci()`
- [ ] Entri ledger dan perubahan status berada di satu transaksi
- [ ] Nominal `BIGINT` rupiah utuh, tidak ada `float`
- [ ] `make test-regression` hijau, R2 dan R2b keduanya

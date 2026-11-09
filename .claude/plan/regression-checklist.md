# Regression Checklist

Enam kelompok invarian. Dijalankan dengan `make test-regression`, dan **wajib hijau sebelum
mengklaim task apa pun selesai**.

Ini bukan test per fitur. Ini pernyataan tentang apa yang harus selalu benar, apa pun yang baru
ditambahkan ke sistem.

---

## R1. Matriks transisi lengkap

File: `backend/tests/regression/test_r1_transitions.py`

Menguji **setiap** kombinasi status kali event, bukan hanya yang legal:

- Setiap `T-xx` di [08-state-machines](../prd/08-state-machines.md) berhasil.
- Setiap kombinasi yang **tidak** ada di tabel itu ditolak dengan `409`.
- Status terminal (`rejected`, `failed`, `completed`) menolak semua event.
- Berlaku untuk keempat mesin: proposal, milestone, laporan, campaign.

Dibangun dengan parametrize atas hasil kali kartesian status dan event, sehingga menambah satu
status otomatis menambah baris uji, dan suite merah sampai peta transisinya diperbarui.

**Menangkap:** status baru yang lupa dipetakan, transisi yang diam-diam diizinkan dari endpoint.

## R2. Invarian ledger

File: `backend/tests/regression/test_r2_ledger.py`

Setelah **setiap** operasi uang di skenario end-to-end:

- `jumlah(pledge_in) - jumlah(refund_out) - jumlah(disbursement_out) == saldo escrow proposal`
- `jumlah(disbursement_out) <= dana terkumpul`
- tidak ada entri dengan `amount <= 0`
- `idempotency_key` benar-benar unik; memanggil operasi yang sama dua kali tidak menambah baris
- tidak ada baris ledger yang pernah ter-UPDATE (diuji dengan membandingkan hash seluruh tabel
  sebelum dan sesudah operasi yang seharusnya hanya menambah)

**Menangkap:** dana cair dua kali, refund yang menghapus alih-alih mencatat, saldo yang dihitung
dari kolom alih-alih dari penjumlahan.

## R2b. Status funding konsisten dengan pledge

File: `backend/tests/regression/test_r2b_funding_status.py`

Setelah setiap operasi pledge, apa pun jalurnya:

```
status == f(jumlah pledge aktif, requested_amount, funding_deadline)
```

Diuji untuk seluruh urutan: pledge naik, pledge dibatalkan, pledge terakhir dibatalkan, deadline
lewat di tengah, pledge yang membuat tepat pas target.

**Menangkap:** kode yang menulis status di luar `recompute_funding_status()`. Ini adalah penutup
risiko dari [D-05](../docs/decisions.md).

## R3. Happy path end-to-end

File: `backend/tests/regression/test_r3_happy_path.py`

Satu test panjang, sengaja tidak dipecah, karena yang diuji adalah rantainya:

1. Investor registrasi dan membuat campaign.
2. UMKM registrasi dan submit proposal dengan dua milestone.
3. `MockScoringEngine` menilai, proposal menjadi `listed`.
4. Komunitas vote.
5. Investor A pledge separuh, status menjadi `partially_funded`.
6. Investor B pledge separuh sisanya, status menjadi `funded`, A menjadi lead investor.
7. Lead investor approve milestone 1, dana cair.
8. UMKM lapor milestone 2, lead investor approve, dana cair.
9. Proposal menjadi `completed`.
10. Jumlah seluruh `disbursement_out` sama persis dengan `requested_amount`.

**Menangkap:** apa pun yang memutus rantai.

## R4. Jalur gagal

File: `backend/tests/regression/test_r4_failure_paths.py`

- Deadline pendanaan lewat sebelum target tercapai, proposal menjadi `failed`, setiap pledge aktif
  mendapat entri `refund_out` sebesar nominalnya, saldo escrow kembali nol.
- Pledge melebihi sisa dana ditolak `409`, dan respons memuat `remaining_amount` yang benar.
- UMKM yang sama submit proposal kedua ke campaign yang sama, ditolak.
- Milestone 2 dilaporkan sebelum milestone 1 cair, ditolak `409`.
- Investor yang bukan lead investor mencoba approve, ditolak **`404`, bukan `403`**. Pola
  seluruh project ini adalah menolak tanpa memberitahu bahwa sumber dayanya ada; `403` akan
  mengonfirmasi ke investor mana pun bahwa milestone dengan id itu nyata.
- Approve pada proposal `failed` tidak pernah mencairkan dana. Yang dijamin **tidak ada
  `disbursement_out`**, bukan satu kode status tertentu: proposal yang gagal tanpa pledge
  tidak punya lead investor, jadi pagar otorisasi menolak lebih dulu, dan kode mana yang
  muncul tergantung pagar mana yang lebih dulu kena. Itu detail implementasi; ledger yang
  tetap bersih adalah jaminannya.
- Proposal yang sudah `funded` menerima pledge baru, ditolak `409`.
- **Tidak ada keadaan di mana proposal `failed` memegang pledge `active`.** Ini invarian, bukan
  skenario: ia dijaga apa pun jalan yang membuat proposal itu gagal, termasuk pledge yang masuk
  setelah `funding_deadline` lewat dan pembatalan yang menjatuhkan total di bawah target setelah
  tenggat. Review fase 06 mereproduksi keduanya terhadap database sungguhan, dan keduanya
  meninggalkan `pledge_in` tanpa `refund_out` dengan escrow menggantung. Testnya memeriksa
  seluruh proposal `failed` di akhir skenario, bukan satu proposal yang diketahui.

## R5. Matriks RBAC

File: `backend/tests/regression/test_r5_rbac.py`

Setiap endpoint kali setiap peran, ditambah kasus "peran benar tapi bukan pemilik".

Matriksnya ditulis sebagai data di satu tempat:

```python
RBAC_MATRIX = [
    # (method, path, peran, harapan)
    ("POST", "/api/v1/campaigns", "investor",  201),
    ("POST", "/api/v1/campaigns", "umkm",      403),
    ("POST", "/api/v1/campaigns", "community", 403),
    ("POST", "/api/v1/campaigns", None,        401),
    # ... satu baris per kombinasi
]
```

Ditambah test terpisah yang memastikan **setiap route terdaftar punya minimal satu baris di
matriks**. Endpoint baru tanpa baris baru membuat R5 merah.

**Menangkap:** endpoint baru yang lupa dipasangi guard, dan guard yang hanya memeriksa peran tanpa
memeriksa kepemilikan.

## R6. Kegagalan AI tidak pernah menolak proposal

File: `backend/tests/regression/test_r6_ai_failure.py`

Untuk setiap mode kegagalan (timeout, error jaringan, output gagal validasi, API key tidak ada):

- `scoring_status` menjadi `failed`
- `proposal.status` **tetap** `submitted`
- tidak ada baris baru di `scoring_results`
- endpoint rescore mengembalikan `scoring_status` ke `pending`
- memicu job dua kali tidak menghasilkan dua transisi

**Menangkap:** pelanggaran [D-09](../docs/decisions.md), yang akan merusak kepercayaan UMKM dan
tidak akan terlihat sampai Gemini benar-benar down.

---

## Cara menambah invarian

Saat sebuah bug ditemukan di luar test, pertanyaannya bukan "bagaimana memperbaikinya" melainkan
"invarian mana yang seharusnya menangkapnya". Tambahkan dulu kasusnya ke kelompok R yang sesuai,
pastikan merah, baru perbaiki kodenya.

Kalau bug itu tidak masuk ke kelompok mana pun, itu tanda ada invarian yang belum pernah
dituliskan. Tulis kelompok baru.

# 08. State Machine

Semua transisi melewati `backend/app/domain/transitions.py`. Peta di bawah ini ditulis di sana
sebagai data, bukan tersebar sebagai percabangan di banyak service ([D-04](../docs/decisions.md)).

Setiap `T-xx` wajib punya kasus di regression test **R1**, dan R1 juga menguji **seluruh kombinasi
yang tidak ada di tabel ini**, memastikan semuanya ditolak dengan `409 Conflict`.

---

## Proposal

Tujuh status. "Didanai sebagian" adalah status sungguhan di database, bukan hasil hitungan
([D-05](../docs/decisions.md)), dan penambahannya itulah yang membuat jumlahnya tujuh, bukan enam.

| ID | Dari | Event | Ke |
| --- | --- | --- | --- |
| T-01 | `submitted` | Scoring selesai, skor mencapai threshold, tanpa red flag kritis | `listed` |
| T-02 | `submitted` | Scoring selesai, skor di bawah threshold atau ada red flag kritis | `rejected` |
| T-03 | `listed` | Pledge pertama masuk, total masih di bawah dana diminta | `partially_funded` |
| T-04 | `listed` | Pledge pertama langsung memenuhi dana diminta | `funded` |
| T-05 | `listed` | `funding_deadline` campaign lewat, belum ada pledge sama sekali | `failed` |
| T-06 | `partially_funded` | Total pledge aktif mencapai dana diminta | `funded` |
| T-07 | `partially_funded` | Seluruh pledge dibatalkan, total kembali nol | `listed` |
| T-08 | `partially_funded` | `funding_deadline` campaign lewat, total masih kurang | `failed` |
| T-09 | `funded` | Seluruh milestone berstatus `disbursed` | `completed` |

Status terminal: `rejected`, `failed`, `completed`. Tidak ada jalan keluar dari ketiganya.

### Penulis tunggal status funding

`listed`, `partially_funded`, dan `funded` hanya boleh ditulis oleh `recompute_funding_status()`.
Fungsi itu membaca jumlah pledge aktif, lalu menentukan statusnya:

```
total == 0                    sebelum funding_deadline  -> listed
0 < total < requested_amount  sebelum funding_deadline  -> partially_funded
total == requested_amount                               -> funded
total < requested_amount      setelah funding_deadline  -> failed
```

Setiap service yang menambah atau membatalkan pledge wajib memanggilnya di transaksi yang sama.

Regression test **R2b** memeriksa invarian `status == f(jumlah pledge aktif)` setelah setiap
operasi pledge. Kode yang menulis status di luar fungsi ini akan membuat R2b merah.

## Milestone

Tiga status. Reject tidak menciptakan status keempat; dia mengembalikan milestone ke `pending`
dan menandai laporannya.

| ID | Dari | Event | Ke |
| --- | --- | --- | --- |
| T-20 | `pending` | UMKM mengirim laporan (`seq > 1`) | `reported` |
| T-21 | `pending` | Lead investor approve (`seq = 1`, tanpa laporan) | `disbursed` |
| T-22 | `reported` | Lead investor approve | `disbursed` |
| T-23 | `reported` | Lead investor reject dengan catatan | `pending` |

Prasyarat yang diperiksa sebelum T-20, T-21, dan T-22:

- proposal berstatus `funded` ([BR-40](07-business-rules.md))
- milestone `seq - 1` sudah `disbursed`, kecuali untuk `seq = 1` ([BR-43](07-business-rules.md))
- aktor adalah lead investor untuk T-21, T-22, T-23 ([BR-44](07-business-rules.md))

T-21 adalah satu-satunya transisi ke `disbursed` tanpa melewati `reported`, dan hanya berlaku
untuk `seq = 1` ([D-13](../docs/decisions.md)).

## Laporan milestone

Status laporan terpisah dari status milestone, supaya jejak revisi tersimpan.

| ID | Dari | Event | Ke |
| --- | --- | --- | --- |
| T-30 | `pending` | Lead investor approve | `approved` |
| T-31 | `pending` | Lead investor reject | `rejected` |

Laporan `rejected` tidak pernah dihapus. Revisi adalah baris baru berstatus `pending`
([BR-46](07-business-rules.md)).

## Campaign

| ID | Dari | Event | Ke |
| --- | --- | --- | --- |
| T-40 | `open` | Pemilik menutup manual | `closed` |
| T-41 | `open` | `apply_deadline` lewat | `closed` |

Campaign `closed` berhenti menerima proposal baru, tetapi jendela pendanaan proposal yang sudah
masuk tetap terbuka sampai `funding_deadline` ([BR-65](07-business-rules.md)).

Campaign `closed` tidak menerima proposal baru, tetapi proposal yang sudah masuk tetap berjalan
sampai `completed` atau `failed`.

## Scoring

`scoring_status` adalah kolom terpisah dari status proposal. Keduanya tidak boleh dicampur.

| ID | Dari | Event | Ke |
| --- | --- | --- | --- |
| T-50 | `pending` | Job diambil runner | `processing` |
| T-51 | `processing` | Penilaian selesai dan tervalidasi | `done` |
| T-52 | `processing` | Error jaringan, timeout, atau schema meleset | `failed` |
| T-53 | `failed` | UMKM atau investor memicu nilai ulang | `pending` |

T-52 **tidak** mengubah status proposal. Proposal tetap `submitted`
([BR-74](07-business-rules.md), ditegakkan oleh regression test R6).

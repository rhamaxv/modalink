---
name: logicodix-conventions
description: Konvensi dasar project Logicodix. Gunakan setiap kali menulis atau mengubah kode di repo ini, sebelum menyentuh berkas apa pun. Memuat struktur lapisan, aturan letak logika, penamaan, penanganan uang dan waktu, bentuk error, serta higiene komentar kode.
---

# Konvensi Logicodix

Baca ini sebelum menyentuh berkas apa pun di repo. Sumber kebenaran produk ada di `.claude/prd/`,
keputusan arsitektur di `.claude/docs/decisions.md`.

## Empat lapisan dan batasnya

```
api/v1/     HTTP, validasi bentuk, RBAC          boleh impor: schemas, services, deps
services/   orkestrasi database dan domain       boleh impor: models, domain, errors
domain/     aturan murni                          boleh impor: domain lain saja
models/     tabel SQLModel                        boleh impor: tidak ada lapisan lain
```

Panah hanya mengarah ke bawah. `domain/` tidak boleh mengimpor `sqlmodel`, `sqlalchemy`, atau
`fastapi`, dan ada test yang memeriksanya (`tests/unit/test_domain_murni.py`).

## Di mana logika harus tinggal

| Jenis logika | Tempatnya | Contoh |
| --- | --- | --- |
| Aturan yang bisa dihitung dari angka dan status saja | `domain/` | matriks transisi, status funding, pemilihan lead investor, verdict AI |
| Aturan yang butuh membaca atau menulis database | `services/` | memeriksa proposal aktif, mencatat ledger, menghitung ulang status |
| Pemeriksaan bentuk dan kewenangan | `api/` | peran, kepemilikan, panjang field, tipe |

Pertanyaan untuk memutuskan: **bisakah aturan ini diuji tanpa database?** Kalau ya, ia milik
`domain/`. Logika bisnis di dalam router adalah hal yang paling dihindari di project ini.

## Uang

- Selalu `BIGINT` rupiah utuh. Tidak ada `float`, tidak ada `Decimal`, tidak ada sen.
- Di SQLModel wajib `sa_column=Column(BigInteger)`. Tanpa itu kolomnya jadi `INTEGER` dan meluap
  di Rp2,1 miliar.
- Parsing dan format hanya lewat `domain/money.py` di backend dan `lib/money.ts` di frontend.
- Schema yang menerima nominal memakai `Field(strict=True, gt=0)`. Tanpa `strict=True`, Pydantic
  membulatkan `1_000_000.5` diam-diam.

## Waktu

- Hanya `domain/clock.py` yang boleh memanggil `datetime.now()`. Ada test yang memeriksanya.
- Service dan router menerima `Clock` sebagai dependency, bukan memanggil jam sendiri.
- Di test, pakai `FrozenClock`. Tidak ada `sleep` di test mana pun.

## Penamaan

- Identifier, nama tabel, nama kolom, dan pesan commit: **bahasa Inggris**.
- Komentar, docstring, nama test, dan pesan error untuk pengguna: **bahasa Indonesia**.
- Nama test menyebut nomor aturan: `test_br21_pledge_melebihi_sisa_ditolak`. Saat aturan berubah,
  testnya ketemu lewat grep.

Alasan campuran ini: identifier Inggris menyambung dengan pustaka dan dokumentasi, sementara pesan
error dibaca pemilik warung yang tidak berbahasa Inggris.

## Bentuk error

Satu bentuk untuk seluruh endpoint:

```json
{ "error": { "code": "pledge_melebihi_sisa", "message": "...", "detail": { } } }
```

Lempar subclass `DomainError` dari `app/errors.py`, jangan `HTTPException` langsung.

| Kelas | Status | Dipakai untuk |
| --- | --- | --- |
| `UnprocessableError` | 422 | payload valid bentuknya tapi gagal aturan domain |
| `ForbiddenError` | 403 | peran tidak berhak, atau bukan pemilik |
| `NotFoundError` | 404 | tidak ada, atau tidak boleh diketahui keberadaannya |
| `ConflictError` | 409 | transisi status tidak sah, aturan bisnis dilanggar |

Untuk sumber daya yang tidak boleh dilihat, pakai `404`, bukan `403`. `403` mengonfirmasi bahwa
sumber dayanya ada, dan itu sendiri sudah kebocoran informasi.

Pesan ditujukan ke pengguna, bukan ke programmer. "Pledge melebihi sisa dana yang dibutuhkan,
sisa Rp3.000.000" dan bukan "ValidationError on field amount". Tidak ada tanda pisah em.

## Komentar kode

Muat skill `antislop:antislop-code` sebelum menulis komentar. Ringkasnya:

- Komentar menjelaskan **kenapa**, bukan **apa**. `# Hitung total` di atas `total = a + b` adalah
  beban baca tanpa isi.
- Tidak ada pemisah dekoratif, banner huruf besar, atau emoji.
- Tidak ada narasi langkah demi langkah (`# Langkah 1`, `# Langkah 2`).
- Tidak ada TODO yang tidak menyebut tugas konkret.
- Satu komentar per blok logis, bukan per baris.
- Satu baris, dua hanya kalau baris kedua membawa fakta baru.

Yang justru **harus** ada: alasan sebuah constraint dipilih, jebakan platform, perilaku konkuren,
dan keputusan yang kelihatan aneh tanpa konteks. Contoh yang layak:

```python
# Menangkap IntegrityError alih-alih memeriksa dulu dengan SELECT: pemeriksaan
# lebih dulu punya celah balapan, constraint database tidak.
```

## Commit

Format dipatok panitia lomba dan tidak boleh menyimpang
(`.claude/docs/aturan-lomba.md`):

```
feat: reject pledge that exceeds the remaining amount
fix: lock proposal row during milestone disbursement
docs: update installation guide
```

- Awalan: `feat`, `fix`, `docs`, `style`, `refactor`, `chore`. **Tidak ada `test`**, karena
  panitia mencontohkan "test" sebagai pesan yang ditolak.
- Satu kalimat, bahasa Inggris, tanpa scope dalam kurung.
- Test dan implementasinya masuk **satu commit `feat:`**. Memang begitu bentuk yang benar untuk
  TDD, dan sekaligus memenuhi aturan lomba.
- **Tidak ada baris `Co-Authored-By`.**
- Nomor aturan (`BR-xx`, `T-xx`, `D-xx`, `RF-x`) disebut di **nama test**, bukan di pesan commit,
  supaya pesan commit tetap satu kalimat yang menjelaskan perubahan.

Setelah di-push, riwayat **tidak boleh diubah**: dilarang force push, rebase, squash, menghapus
commit, atau memanipulasi tanggal. Salah commit berarti memperbaikinya dengan commit baru.

## Sebelum bilang selesai

`make check` dan `make test-regression` hijau, dengan outputnya ditunjukkan. Lihat skill
`testing-and-regression`.

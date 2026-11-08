# Strategi Test

Empat lapis. Setiap lapis menjawab pertanyaan yang berbeda, dan mencampurnya membuat suite jadi
lambat sekaligus tidak meyakinkan.

| Lapis | Direktori | Menjawab | Kecepatan | Butuh |
| --- | --- | --- | --- | --- |
| Unit | `backend/tests/unit/` | Apakah aturannya benar? | milidetik | tidak ada |
| Integration | `backend/tests/integration/` | Apakah endpointnya menyambung dengan benar? | ratusan ms | Postgres |
| Regression | `backend/tests/regression/` | Apakah invarian sistem masih berdiri? | detik | Postgres |
| Contract | `backend/tests/contract/` | Apakah Gemini masih menepati kontraknya? | puluhan detik | Gemini, API key |

## Unit

Menguji fungsi murni di `backend/app/domain/`. Tidak ada `Session`, tidak ada `TestClient`, tidak
ada `async`. Kalau sebuah test di sini butuh database, berarti logikanya salah tempat dan harus
dipindah ke `domain/`.

Isi lapis ini: aritmetika uang, matriks transisi, aturan verdict AI, pemutus seri lead investor,
penghitungan status funding, validasi rentang skor.

## Integration

Menguji endpoint lewat `httpx.AsyncClient` terhadap aplikasi FastAPI sungguhan, dengan Postgres
test. Setiap test berjalan di dalam transaksi yang di-rollback setelahnya, sehingga tidak ada
kebocoran data antar test dan urutannya tidak penting.

Fixture inti ada di `backend/tests/conftest.py`:

| Fixture | Memberi |
| --- | --- |
| `db` | Session yang di-rollback setelah test |
| `client` | `AsyncClient` yang sudah terikat ke app dengan `db` di atas |
| `investor`, `umkm`, `community` | User beserta token, satu per peran |
| `campaign` | Campaign milik `investor`, `open`, threshold 60 |
| `listed_proposal` | Proposal milik `umkm` yang sudah `listed` lewat `MockScoringEngine` |
| `funded_proposal` | Proposal `funded` dengan dua milestone dan dua investor |

Fixture terakhir adalah yang paling sering dipakai di fase 07 ke atas. Dibangun sekali, dipakai
di mana-mana.

## Regression

Lapis ini yang menjawab permintaan "jangan sampai merusak fitur yang ada". Isinya bukan test per
fitur, melainkan **invarian sistem** yang harus benar kapan pun, apa pun yang baru ditambahkan.

Daftar lengkapnya ada di [regression-checklist.md](regression-checklist.md). Suite ini dijalankan
dengan `make test-regression` dan **wajib hijau sebelum mengklaim task apa pun selesai**.

Regression suite tumbuh seiring fase. Menambah status, endpoint, atau jenis entri ledger berarti
menambah baris di suite ini, dan suite akan merah sampai itu dilakukan. Itu disengaja.

## Contract

Satu file, `backend/tests/contract/test_gemini_scoring.py`, ditandai `@pytest.mark.live`.

```python
# backend/tests/conftest.py
def pytest_collection_modifyitems(config, items):
    if config.getoption("-m") != "live":
        skip = pytest.mark.skip(reason="butuh GEMINI_API_KEY, jalankan dengan: make test-live")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip)
```

Dijalankan manual dengan `make test-live` saat prompt atau schema berubah. Tidak pernah ikut di
`make test` dan tidak pernah ikut di CI.

## Frontend

| Lapis | Alat | Isi |
| --- | --- | --- |
| Unit | Vitest | Format rupiah, hitung persentase progres, penentuan badge status, util tanggal |
| Komponen | Vitest + Testing Library | Form validasi, empty state, loading state, error state |
| End-to-end | Playwright | Satu skenario happy path penuh, dijalankan terhadap backend seed |

Satu skenario Playwright, bukan dua puluh. Yang dicari adalah bukti bahwa seluruh rantai
menyambung, bukan cakupan.

## Perintah

```
make test              # unit + integration + regression
make test-unit         # paling cepat, dipakai saat menulis domain
make test-regression   # gerbang wajib sebelum klaim selesai
make test-live         # contract test Gemini, manual
make test-fe           # vitest
make test-e2e          # playwright
make check             # ruff + mypy + eslint + tsc + make test + make test-fe
```

## Aturan yang menjaga suite ini tetap berguna

1. **Test ditulis lebih dulu dan harus pernah merah.** Test yang tidak pernah merah tidak
   membuktikan apa pun.
2. **Satu test, satu alasan gagal.** Kalau sebuah test bisa merah karena lima sebab berbeda,
   kegagalannya tidak memberi tahu apa-apa.
3. **Nama test menyebut nomor aturan.** `test_br21_pledge_melebihi_sisa_ditolak`. Saat aturan
   berubah, testnya ketemu lewat grep.
4. **Tidak ada `sleep` di test mana pun.** Waktu dikendalikan lewat `domain/clock.py`.
5. **Tidak ada test yang bergantung pada urutan eksekusi.** Semua fixture di-rollback.
6. **Tidak ada jaringan di luar lapis contract.**

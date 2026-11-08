# 03. Modul Investor

## Buat campaign

Form berisi:

| Field | Tipe | Aturan |
| --- | --- | --- |
| `title` | teks | wajib, 5 sampai 120 karakter |
| `description` | teks panjang | wajib, minimal 50 karakter |
| `sector` | pilihan | wajib, satu dari daftar sektor tetap |
| `target_amount` | rupiah | wajib, minimal Rp1.000.000 |
| `apply_deadline` | tanggal | wajib, minimal 1 hari ke depan. Batas UMKM mengajukan proposal |
| `funding_deadline` | tanggal | wajib, harus setelah `apply_deadline`. Batas dana harus terkumpul |
| `score_threshold` | 0 sampai 100 | wajib, default 60 |

Campaign lahir berstatus `open`. `score_threshold` boleh diubah selama belum ada proposal masuk;
setelah ada, diubah akan membuat penilaian lama tidak sebanding dengan yang baru, jadi dikunci.

## Daftar proposal masuk

Hanya pembuat campaign yang melihat daftar lengkap, termasuk yang `rejected`. Publik hanya melihat
yang `listed` ke atas.

Urutan default: skor AI menurun, lalu jumlah vote menurun, lalu waktu submit menaik. Urutan ketiga
ada supaya hasilnya stabil dan bisa di-test; tanpa itu, dua proposal berskor sama bisa bertukar
posisi antar-request.

Tiap baris menampilkan: nama usaha, dana yang diminta, skor total, jumlah red flag berlevel
`critical` dan `warning`, jumlah vote, dan progres funding.

## Baca brief AI

Panel di halaman detail proposal berisi tiga bagian yang datang langsung dari `scoring_results`:

- **Kekuatan**: daftar poin
- **Risiko**: daftar poin
- **Rekomendasi**: satu paragraf

Di sebelahnya, skor ditampilkan **terurai**: `fit_score` dari 40, `data_quality_score` dari 30,
`impact_score` dari 30, lalu total. Red flag ditampilkan sebagai daftar dengan level dan kutipan
bukti dari isi proposal.

Satu kalimat wajib ada di panel ini: penilaian AI adalah alat bantu, keputusan akhir ada di
investor. Ini bukan basa-basi hukum, melainkan cara produk ini memposisikan AI-nya.

## Pledge dana (co-funding)

Investor mana pun boleh pledge ke proposal berstatus `listed` atau `partially_funded`. Tidak harus
pembuat campaign ([D-12](../docs/decisions.md)).

Form hanya meminta nominal. Di atasnya ditampilkan sisa dana yang masih dibutuhkan, dan nominal
yang melebihi sisa itu ditolak dengan pesan yang menyebut angka sisanya ([BR-21](07-business-rules.md)).

Pledge bisa dibatalkan selama proposal belum `funded`. Setelah `funded`, pledge terkunci.

## Approve pencairan milestone

Hanya **lead investor** yang melihat tombol approve dan reject. Lead investor adalah pemilik pledge
terbesar; bila seri, pledge yang lebih dulu masuk yang menang ([BR-23](07-business-rules.md)).

Untuk milestone `seq = 1`, tombol approve aktif begitu proposal `funded`, tanpa menunggu laporan.
Untuk `seq > 1`, tombol aktif hanya setelah UMKM mengirim laporan dan milestone sebelumnya cair.

Reject wajib disertai catatan. Catatan itu yang dibaca UMKM untuk merevisi.

## Lihat status funding dan progres milestone

Satu halaman memuat:

- bar progres: total terkumpul dibanding dana diminta, dengan daftar investor yang ikut dan
  nominal masing-masing
- daftar milestone dengan status, nominal, dan tanggal cair
- tautan ke jejak ledger proposal ini

## Yang investor tidak bisa lakukan

- Mengubah skor AI atau memaksa proposal `rejected` menjadi `listed`. Kalau tidak setuju dengan
  AI, caranya adalah menurunkan `score_threshold` di campaign berikutnya.
- Menarik dana yang sudah cair.
- Melihat proposal di campaign milik investor lain yang belum `listed`.

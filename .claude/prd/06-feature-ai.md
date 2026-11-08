# 06. Modul AI, dari sisi produk

Spesifikasi teknisnya ada di [11-ai-scoring-spec.md](11-ai-scoring-spec.md). File ini hanya
menjelaskan apa yang pengguna lihat dan janji apa yang produk ini buat.

## Dua hal yang dikerjakan AI

### 1. Screening dan scoring

Menilai kecocokan proposal dengan kriteria campaign, memberi skor terurai, dan menandai red flag
seperti data tidak konsisten, proyeksi tidak realistis, atau isian yang terasa template.

Yang dilihat investor:

```
Kecocokan kriteria    34 / 40
Kualitas data         21 / 30
Potensi dampak        18 / 30
                      ────────
Total                 73 / 100     ambang campaign: 60

Red flag
  [kritis]  Proyeksi omzet naik 40x dalam 6 bulan untuk usaha
            dengan 2 pekerja
            kutipan: "target omzet Rp400 juta per bulan"
  [ringan]  Rencana penggunaan dana tidak merinci porsi
            untuk bahan baku
```

### 2. Brief generator

Meringkas proposal panjang menjadi kekuatan, risiko, dan satu paragraf rekomendasi.

## Janji produk soal AI

Tiga hal ini adalah posisi produk, dan ditegakkan oleh kode serta test, bukan hanya ditulis di
halaman "tentang kami".

**AI tidak pernah auto-reject tanpa indikasi jelas.** Penolakan hanya terjadi karena skor di bawah
ambang yang diset investor sendiri, atau karena red flag berlevel `critical`. Untuk kasus abu-abu,
proposal tetap `listed` dan keputusan ada di investor.

**Ambang eliminasi dikonfigurasi per campaign oleh investor,** bukan ditetapkan platform. Investor
yang merasa AI terlalu galak bisa menurunkannya.

**Kegagalan teknis tidak pernah berarti penolakan.** Error jaringan atau schema yang meleset
menghasilkan status "perlu dinilai ulang", bukan "ditolak" ([D-09](../docs/decisions.md)).

## Yang tidak dilakukan AI

- Tidak menentukan nominal pendanaan.
- Tidak memilih lead investor.
- Tidak menilai laporan progres milestone. Itu murni penilaian manusia.
- Tidak menulis atau memperbaiki proposal untuk UMKM.

Batas terakhir disengaja: kalau AI ikut menulis proposal, skor AI terhadap proposal itu kehilangan
arti.

## Transparansi ke pengguna

Panel skor selalu menyertakan: nama model yang dipakai, waktu penilaian, dan ambang yang berlaku
saat itu. Penilaian ulang membuat baris baru, tidak menimpa yang lama, sehingga riwayatnya bisa
ditelusuri.

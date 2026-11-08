# Tim

Dipakai untuk README (panitia mewajibkan nama tim dan daftar anggota) dan untuk Surat Pernyataan
Orisinalitas Karya yang ditandatangani Ketua Tim.

## Nama tim

**Onde Mande Dinamika**

## Anggota

Empat orang, sesuai batas maksimal panitia.

| # | Nama |
| --- | --- |
| 1 | Janzen Firdaus Al Zam Zami |
| 2 | Rhama Damarwijaya |
| 3 | Moch Hanafi Gus Ageng Manik |
| 4 | Naufal Ardallah Budianto |

Ejaan di atas yang dipakai di README dan di Surat Pernyataan Orisinalitas. Kalau berbeda dengan
data pendaftaran, yang diperbaiki adalah dokumen ini, bukan data panitia, karena daftar anggota
dibandingkan dengan data pendaftaran saat verifikasi.

## Akun GitHub

Panitia mewajibkan **seluruh commit berasal dari akun GitHub anggota terdaftar**.

**Yang melakukan commit dan push: Rhama Damarwijaya seorang**, lewat akun `rhamaxv`.
Terverifikasi dengan `gh auth status` pada 9 November 2026.

| Nama | Username GitHub | Peran di repositori |
| --- | --- | --- |
| Rhama Damarwijaya | `rhamaxv` | Satu-satunya yang commit dan push |
| Janzen Firdaus Al Zam Zami | tidak dipakai | Tidak commit |
| Moch Hanafi Gus Ageng Manik | tidak dipakai | Tidak commit |
| Naufal Ardallah Budianto | tidak dipakai | Tidak commit |

Ini **memenuhi aturan**. Yang dipatok panitia adalah asal commit, bukan sebarannya, dan `rhamaxv`
adalah akun anggota terdaftar. Tim satu orang pun sah menurut ketentuan umum.

### Konsekuensi yang harus ditangani

Empat nama di README dengan satu akun di riwayat commit adalah hal yang wajar ditanyakan juri,
dan panitia memang berhak meminta klarifikasi. Dua langkah yang menutupnya:

1. **README wajib memuat pembagian peran**, bukan sekadar daftar nama. Siapa mengerjakan ideasi
   dan pemetaan masalah, siapa desain UI/UX, siapa pengujian dan video, siapa menulis kode.
   Guidebook menyatakan ide, riset, wireframe, dan desain UI/UX boleh disiapkan sebelum Hacking
   Week, jadi kontribusi itu nyata meski tidak muncul sebagai commit. Menjelaskannya lebih dulu
   lebih kuat daripada menunggu ditanya.
2. **Seluruh anggota harus bisa menjelaskan implementasi teknisnya** saat Grand Final, karena ada
   3 menit Q&A di depan juri industri dan panitia mewajibkan tim mampu mempertanggungjawabkan
   seluruh implementasi. Ini risiko yang sesungguhnya, bukan riwayat commit.

### Yang dilarang untuk "meratakan" riwayat

- Menambahkan `Co-Authored-By` anggota yang tidak ikut mengerjakan commit itu
- Meminta anggota lain membuat commit kosong atau kosmetik

Keduanya masuk kategori memanipulasi bukti pengembangan, yang hukumannya diskualifikasi.

Periksa asal commit kapan saja:

```bash
git log --format='%an <%ae>' | sort -u
```

## Ketua Tim

**Rhama Damarwijaya.**

Menandatangani Surat Pernyataan Orisinalitas Karya, yang wajib bermaterai Rp10.000 atau e-meterai
dan dikumpulkan dalam format PDF bersama submission, paling lambat 14 November 2026 pukul 23.59 WIB.

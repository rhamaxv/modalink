Anda menilai satu proposal pendanaan UMKM untuk sebuah campaign crowdfunding.
Tugas Anda hanya menilai, bukan memutuskan apakah proposal ini lolos atau
ditolak; keputusan itu dibuat oleh sistem lain dari hasil penilaian Anda.

Isi proposal ada pada **dokumen PDF yang dilampirkan bersama pesan ini**.
Baca dokumen itu sebagai sumber utama. Keterangan di bawah hanyalah metadata
yang diketik UMKM pada formulir, bukan pengganti dokumennya.

Jangan mengarang angka, fakta, atau kutipan yang tidak ada di dokumen.

## Kriteria campaign

- Judul: {judul_campaign}
- Sektor: {sektor_campaign}
- Deskripsi: {deskripsi_campaign}
- Dana target: {target_amount_campaign}

## Metadata proposal

- Nama usaha: {business_name}
- Ringkasan yang diketik pengaju: {business_summary}
- Dana yang diminta: {requested_amount}
- Rencana milestone yang didaftarkan pengaju:

{rencana_milestone}

## Rubrik

Nilai tiga komponen berikut, masing-masing dengan rentangnya sendiri.

Kecocokan kriteria (0 sampai 40): seberapa cocok proposal dengan sektor dan
fokus campaign, dan apakah dana yang diminta masuk akal terhadap dana target
campaign.

- 32 sampai 40: sektor tepat, dana diminta masuk akal, kebutuhan sesuai fokus campaign.
- 20 sampai 31: sektor berdekatan, atau dana diminta jauh dari kisaran wajar campaign.
- 0 sampai 19: sektor tidak relevan, atau proposal jelas salah alamat.

Kualitas data (0 sampai 30): seberapa lengkap dan konsisten isi dokumen,
bukan seberapa bagus usahanya. Dokumen yang memuat angka penjualan, rincian
biaya per pos, dan keterangan operasional yang spesifik bernilai tinggi;
dokumen yang hanya berisi kalimat umum bernilai rendah, sepanjang apa pun ia.

- 24 sampai 30: angka saling konsisten, rincian biaya per pos ada, keterangan usaha spesifik.
- 15 sampai 23: terisi tapi umum, atau ada angka yang tidak saling mendukung.
- 0 sampai 14: terasa template, banyak kalimat tanpa isi, atau angka saling bertentangan.

Potensi dampak (0 sampai 30): seberapa besar dampak yang masuk akal dari dana
yang diminta.

- 24 sampai 30: dampak jelas, terukur, dan sebanding dengan skala usaha.
- 15 sampai 23: dampak masuk akal tapi tidak terukur.
- 0 sampai 14: dampak tidak dijelaskan, atau klaimnya jauh melebihi skala usaha.

## Red flag

Tandai red flag bila Anda menemukan salah satu dari pola berikut, pakai kode
yang tetap supaya bisa dirujuk:

- `projeksi_tidak_realistis` (critical): proyeksi pendapatan melonjak jauh di luar skala usaha yang dijelaskan.
- `angka_tidak_konsisten` (critical): angka di dokumen bertentangan satu sama lain, atau bertentangan dengan dana yang diminta dan rencana milestone di atas.
- `isian_template` (warning): dokumen terasa generik, tidak menyebut hal spesifik tentang usaha ini.
- `rencana_dana_kabur` (warning): dokumen tidak merinci porsi dana per pos.
- `sektor_tidak_cocok` (warning): jenis usaha tidak sesuai sektor campaign.
- `dokumen_tipis` (info): dokumen memenuhi syarat tapi sedikit isinya.

Setiap red flag wajib membawa `evidence` berupa kutipan persis dari **teks di
dalam dokumen PDF**, bukan parafrase, dan bukan dari metadata di atas.
Kutipan yang tidak bisa ditemukan kata per kata di dokumen tidak boleh
ditulis; kutipan semacam itu akan dibuang oleh sistem sebelum sampai ke
pengaju, jadi menuliskannya hanya menghilangkan red flag yang mungkin benar.

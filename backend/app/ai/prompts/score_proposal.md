Anda menilai satu proposal pendanaan UMKM untuk sebuah campaign crowdfunding.
Tugas Anda hanya menilai, bukan memutuskan apakah proposal ini lolos atau
ditolak; keputusan itu dibuat oleh sistem lain dari hasil penilaian Anda.
Jangan mengarang angka, fakta, atau kutipan yang tidak ada di isi proposal.

## Kriteria campaign

- Judul: {judul_campaign}
- Sektor: {sektor_campaign}
- Deskripsi: {deskripsi_campaign}
- Dana target: {target_amount_campaign}

## Isi proposal

- Nama usaha: {business_name}
- Profil usaha (business_profile): {business_profile}
- Dana yang diminta: {requested_amount}
- Rencana penggunaan dana (fund_usage_plan): {fund_usage_plan}
- Proyeksi usaha (business_projection): {business_projection}

## Rubrik

Nilai tiga komponen berikut, masing-masing dengan rentangnya sendiri.

Kecocokan kriteria (0 sampai 40): seberapa cocok proposal dengan sektor dan
fokus campaign, dan apakah dana yang diminta masuk akal terhadap dana target
campaign.

- 32 sampai 40: sektor tepat, dana diminta masuk akal, kebutuhan sesuai fokus campaign.
- 20 sampai 31: sektor berdekatan, atau dana diminta jauh dari kisaran wajar campaign.
- 0 sampai 19: sektor tidak relevan, atau proposal jelas salah alamat.

Kualitas data (0 sampai 30): seberapa lengkap dan konsisten isian proposal,
bukan seberapa bagus usahanya.

- 24 sampai 30: semua field terisi spesifik, angka saling konsisten, rencana penggunaan dana terinci.
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
- `angka_tidak_konsisten` (critical): angka di proyeksi bertentangan dengan angka di profil atau rencana dana.
- `isian_template` (warning): isian terasa generik, tidak menyebut hal spesifik tentang usaha ini.
- `rencana_dana_kabur` (warning): rencana penggunaan dana tidak merinci porsi per pos.
- `sektor_tidak_cocok` (warning): jenis usaha tidak sesuai sektor campaign.
- `profil_tipis` (info): profil usaha memenuhi panjang minimum tapi sedikit isinya.

Setiap red flag wajib membawa `evidence` berupa kutipan persis dari isi
proposal di atas, bukan parafrase. Kutipan yang tidak bisa ditemukan kata per
kata di isi proposal tidak boleh ditulis.

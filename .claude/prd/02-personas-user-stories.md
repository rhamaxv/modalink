# 02. Peran dan User Story

Tiga peran, dipilih saat registrasi, disimpan di kolom `users.role`, dan dibawa di dalam JWT.
Satu akun punya tepat satu peran. Tidak ada peran ganda di MVP.

## Investor

Punya dana dan kriteria. Membuat campaign sebagai kurator, lalu mendanai proposal yang lolos.

| ID | User story |
| --- | --- |
| US-I1 | Sebagai investor, saya ingin membuat campaign dengan kriteria jelas agar proposal yang masuk relevan dengan minat saya. |
| US-I2 | Sebagai investor, saya ingin melihat skor AI dan ringkasan tiap proposal agar saya tidak perlu membaca semua proposal secara detail. |
| US-I3 | Sebagai investor, saya ingin tahu **kenapa** sebuah proposal mendapat skor tertentu agar saya bisa tidak setuju dengan penilaian AI. |
| US-I4 | Sebagai investor, saya ingin ikut patungan mendanai satu proposal bersama investor lain agar risiko saya lebih kecil. |
| US-I5 | Sebagai investor, saya ingin menyetujui pencairan dana per milestone agar dana tidak disalahgunakan. |
| US-I6 | Sebagai investor, saya ingin melihat sisa dana yang masih dibutuhkan sebuah proposal agar saya tahu berapa yang masuk akal saya sanggupi. |

US-I3 adalah alasan skor disimpan terurai per komponen, bukan sebagai satu angka.

## UMKM

Pemilik usaha yang butuh modal. Mengajukan proposal, lalu melaporkan progres.

| ID | User story |
| --- | --- |
| US-U1 | Sebagai pemilik usaha, saya ingin mengajukan proposal dengan form terstruktur agar usaha saya dinilai secara adil. |
| US-U2 | Sebagai pemilik usaha, saya ingin tahu status proposal saya tanpa harus bertanya ke siapa pun. |
| US-U3 | Sebagai pemilik usaha, saya ingin tahu alasan proposal saya ditolak agar saya bisa memperbaikinya. |
| US-U4 | Sebagai pemilik usaha, saya ingin melaporkan progres milestone agar dana tahap berikutnya bisa cair. |
| US-U5 | Sebagai pemilik usaha, saya ingin bisa merevisi laporan yang ditolak tanpa kehilangan isi laporan sebelumnya. |

US-U3 adalah alasan `scoring_results` menyimpan `red_flags` beserta `evidence`, bukan hanya kode.

## Komunitas

Publik yang memberi dukungan non-finansial.

| ID | User story |
| --- | --- |
| US-K1 | Sebagai anggota komunitas, saya ingin memberi dukungan pada proposal yang saya percaya agar suara saya jadi sinyal tambahan bagi investor. |
| US-K2 | Sebagai anggota komunitas, saya ingin membatalkan vote saya kalau saya berubah pikiran. |
| US-K3 | Sebagai anggota komunitas, saya ingin meninggalkan komentar singkat yang terbaca oleh investor dan pemilik usaha. |

## Yang tidak punya user story

Peran admin atau moderator tidak ada di MVP. Tidak ada moderasi komentar, tidak ada penghapusan
proposal oleh pihak ketiga. Kalau muncul kebutuhan itu saat demo, jawabannya adalah "roadmap",
bukan fitur yang dikerjakan diam-diam.

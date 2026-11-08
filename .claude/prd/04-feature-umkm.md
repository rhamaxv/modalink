# 04. Modul UMKM

## Submit proposal

Form terstruktur, dan strukturnya disengaja: AI menilai berdasarkan field-field ini, jadi field
yang ambigu menghasilkan skor yang ambigu.

| Field | Tipe | Aturan |
| --- | --- | --- |
| `business_name` | teks | wajib, 3 sampai 120 karakter |
| `business_profile` | teks panjang | wajib, minimal 100 karakter. Jenis usaha, lama berjalan, lokasi, jumlah pekerja |
| `requested_amount` | rupiah | wajib, tidak boleh melebihi `target_amount` campaign |
| `fund_usage_plan` | teks panjang | wajib, minimal 100 karakter. Rincian penggunaan dana |
| `business_projection` | teks panjang | wajib, minimal 50 karakter. Proyeksi omzet atau dampak |
| `milestones` | daftar | wajib, minimal 2 baris |

Tiap milestone berisi `title`, `description`, dan `amount`. Jumlah seluruh `amount` wajib sama
persis dengan `requested_amount` ([BR-14](07-business-rules.md)). Pesan errornya menyebut selisihnya,
bukan sekadar "jumlah tidak sesuai".

Satu UMKM hanya boleh punya satu proposal aktif per campaign ([BR-13](07-business-rules.md)).
"Aktif" berarti status selain `rejected` dan `failed`.

## Lihat status proposal

| Yang dilihat UMKM | Status di database |
| --- | --- |
| Sedang dinilai AI | `submitted` dengan `scoring_status` `pending` atau `processing` |
| Penilaian gagal, bisa dicoba lagi | `submitted` dengan `scoring_status` `failed` |
| Ditolak | `rejected` |
| Terbuka untuk pendanaan | `listed` |
| Didanai sebagian | `partially_funded`, dengan persentase |
| Dana terkumpul penuh | `funded` |
| Gagal terkumpul | `failed` |
| Selesai | `completed` |

Baris kedua penting: kalau pemanggilan AI gagal, UMKM melihat tombol **Nilai ulang**, bukan
penolakan ([D-09](../docs/decisions.md)).

Untuk proposal `rejected`, UMKM melihat daftar red flag beserta kutipan bukti dan skor terurai.
Tanpa itu, penolakan tidak memberi apa-apa untuk diperbaiki ([US-U3](02-personas-user-stories.md)).

## Lapor progres milestone

Tersedia hanya untuk milestone yang boleh dilaporkan: `seq > 1`, dan `seq - 1` sudah `disbursed`.

| Field | Tipe | Aturan |
| --- | --- | --- |
| `narrative` | teks panjang | wajib, minimal 50 karakter |
| `metrics` | JSON opsional | pasangan label dan angka, misal omzet bulan berjalan |

Setiap pengiriman membuat baris baru di `milestone_reports`. Laporan yang ditolak tidak dihapus
dan tidak ditimpa; revisi adalah baris berikutnya ([US-U5](02-personas-user-stories.md)). Halaman
laporan menampilkan seluruh riwayat beserta catatan penolakan dari lead investor.

## Update dampak pasca-pendanaan

Tidak dibangun di MVP. Disebut sebagai roadmap saat pitching
([01-goals-scope.md](01-goals-scope.md)).

## Yang UMKM tidak bisa lakukan

- Mengubah proposal setelah submit. Kalau ditolak, jalurnya adalah mengajukan proposal baru di
  campaign lain, atau menunggu campaign berikutnya.
- Melihat identitas investor yang pledge sebelum proposal `funded`.
- Mencairkan dana tanpa approve lead investor, termasuk milestone pertama.

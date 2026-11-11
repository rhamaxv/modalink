# 07. Business Rules

Setiap aturan bernomor. Nomornya dipakai langsung di nama test, misalnya
`test_br21_pledge_melebihi_sisa_ditolak`. Kalau sebuah aturan berubah, cari nomornya di
`backend/tests/` dan perbarui testnya di tempat yang sama.

Pengelompokan nomor: 01-09 auth, 10-19 proposal, 20-29 pledge, 30-39 komunitas, 40-49 milestone,
50-59 uang, 60-69 waktu, 70-79 AI.

---

## Auth dan peran

| ID | Aturan |
| --- | --- |
| BR-01 | Satu akun punya tepat satu peran, dipilih saat registrasi, tidak bisa diubah di MVP. |
| BR-02 | Email unik lintas peran. Satu alamat email tidak bisa dipakai dua akun. |
| BR-03 | Password minimal 8 karakter, disimpan sebagai hash argon2, tidak pernah dikembalikan oleh endpoint mana pun. |
| BR-04 | Role dibawa di dalam JWT dan diverifikasi ulang terhadap database pada setiap request. Token lama dengan role yang sudah berubah tidak boleh lolos. |
| BR-05 | Endpoint publik (daftar campaign, daftar proposal `listed`, komentar) bisa diakses tanpa token. |

## Validasi proposal

| ID | Aturan |
| --- | --- |
| BR-10 | Seluruh field wajib harus terisi dan memenuhi panjang minimum sebelum proposal bisa disubmit. |
| BR-11 | `requested_amount` tidak boleh melebihi `target_amount` campaign. |
| BR-12 | `requested_amount` minimal Rp500.000. Di bawah itu, biaya screening tidak sepadan. |
| BR-13 | Satu UMKM hanya boleh punya satu proposal aktif per campaign. "Aktif" berarti status selain `rejected` dan `failed`. Ditegakkan oleh partial unique index, bukan hanya oleh kode. |
| BR-14 | Proposal wajib punya minimal 2 milestone, dan jumlah seluruh `amount` milestone harus sama persis dengan `requested_amount`. Pesan error menyebut selisihnya. |
| BR-15 | Nomor urut milestone (`seq`) berawal dari 1 dan berurutan tanpa lompatan. |
| BR-16 | Setiap milestone wajib punya `amount` lebih besar dari nol. |
| BR-17 | Proposal hanya bisa disubmit ke campaign berstatus `open` yang `apply_deadline`-nya belum lewat. |
| BR-18 | Proposal tidak bisa diubah setelah disubmit. Tidak ada endpoint PATCH untuk proposal. |

## Co-funding dan pledge

| ID | Aturan |
| --- | --- |
| BR-20 | Hanya proposal berstatus `listed` atau `partially_funded` yang bisa menerima pledge. |
| BR-21 | Pledge yang membuat total melebihi `requested_amount` ditolak dengan `409`. Respons menyertakan sisa yang masih bisa didanai. Tidak ada pemotongan otomatis dan tidak ada over-funding. |
| BR-22 | Investor mana pun boleh pledge, tidak harus pembuat campaign. Pembuat campaign berperan sebagai kurator. |
| BR-23 | Lead investor adalah pemilik total pledge aktif terbesar pada proposal itu. Bila ada nilai yang seri, pledge yang lebih dulu masuk yang menang. Dihitung ulang setiap kali pledge masuk atau dibatalkan. |
| BR-24 | Satu investor boleh pledge lebih dari sekali pada proposal yang sama. Totalnya yang dihitung untuk BR-23. |
| BR-25 | Pledge bisa dibatalkan selama proposal belum `funded`. Setelah `funded`, pledge terkunci. |
| BR-26 | Pembatalan pledge membuat entri `refund_out` di ledger, bukan menghapus entri `pledge_in`. |
| BR-27 | Nominal pledge minimal Rp100.000. |
| BR-28 | Peran UMKM dan komunitas tidak punya akses ke endpoint pledge sama sekali. |

## Komunitas

| ID | Aturan |
| --- | --- |
| BR-30 | Hanya proposal berstatus `listed` ke atas yang bisa divote dan dikomentari. |
| BR-31 | Vote tidak pernah mengubah status proposal. Dia hanya ditampilkan di sebelah skor AI sebagai sinyal tambahan. |
| BR-32 | Satu akun komunitas hanya bisa vote satu kali per proposal. Vote bersifat toggle. Ditegakkan oleh unique constraint pada pasangan `(proposal_id, user_id)`. |
| BR-33 | Komentar maksimal 500 karakter, tanpa format kaya dan tanpa lampiran. |
| BR-34 | Komentar hanya bisa dihapus oleh penulisnya sendiri. |
| BR-35 | Red flag dan brief AI tidak pernah terlihat oleh peran komunitas. |

## Milestone dan pencairan

| ID | Aturan |
| --- | --- |
| BR-40 | Pencairan hanya mungkin pada proposal berstatus `funded`. |
| BR-41 | Milestone `seq = 1` tidak memerlukan laporan progres, tetapi tetap butuh approve lead investor sebelum cair. |
| BR-42 | Milestone `seq > 1` wajib disertai laporan progres yang disetujui sebelum cair. |
| BR-43 | Milestone `seq N` hanya bisa diproses setelah `seq N-1` berstatus `disbursed`. |
| BR-44 | Hanya lead investor yang bisa approve atau reject pencairan. Investor lain yang ikut mendanai tidak bisa. |
| BR-45 | Reject wajib disertai catatan, minimal 10 karakter. |
| BR-46 | Reject mengembalikan milestone ke `pending` dan menandai laporan itu `rejected`. Laporan tidak dihapus dan tidak ditimpa; revisi adalah baris baru. |
| BR-47 | Approve mencatat satu entri `disbursement_out` sebesar `amount` milestone dan mengubah statusnya menjadi `disbursed`, dalam satu transaksi database. |
| BR-48 | Approve yang dikirim dua kali untuk milestone yang sama tidak boleh menghasilkan dua pencairan. Ditegakkan oleh `idempotency_key` di ledger. |

## Uang dan ledger

| ID | Aturan |
| --- | --- |
| BR-50 | Semua nominal disimpan sebagai `BIGINT` rupiah utuh. Tidak ada desimal, tidak ada `float`. |
| BR-51 | `ledger_entries` hanya menerima INSERT. Tidak ada UPDATE dan tidak ada DELETE, termasuk untuk koreksi. Koreksi adalah entri lawan arah. |
| BR-52 | Saldo escrow sebuah proposal dihitung sebagai jumlah `pledge_in` dikurangi `refund_out` dan `disbursement_out`. Tidak pernah disimpan sebagai kolom. |
| BR-53 | Total `disbursement_out` tidak boleh melebihi dana terkumpul pada proposal itu. |
| BR-54 | Tidak ada entri ledger dengan nominal nol atau negatif. Arah ditentukan oleh `entry_type`, bukan oleh tanda angka. |
| BR-55 | Setiap entri wajib punya `idempotency_key` unik yang berasal dari sumber kejadiannya, misalnya `disburse:{milestone_id}`. |

## Waktu dan deadline

| ID | Aturan |
| --- | --- |
| BR-60 | Waktu "sekarang" hanya boleh diambil dari `domain/clock.py`. Memanggil `datetime.now()` langsung di service atau router dilarang. |
| BR-61 | Transisi ke `failed` dievaluasi saat proposal atau campaign dibaca, bukan oleh scheduler. |
| BR-62 | Proposal yang melewati `funding_deadline` campaign tanpa mencapai target menjadi `failed`, dan seluruh pledge aktifnya dibatalkan dengan entri `refund_out`. |
| BR-63 | Endpoint `POST /internal/clock/tick` hanya aktif bila `ENV=dev`. Di `ENV=prod` dia mengembalikan `404`. |
| BR-64 | Campaign punya dua deadline. `apply_deadline` membatasi pengajuan proposal, `funding_deadline` membatasi terkumpulnya dana. `funding_deadline` wajib setelah `apply_deadline`, ditegakkan oleh `CHECK` di database. |
| BR-65 | Proposal yang masuk tepat sebelum `apply_deadline` tetap punya jendela pendanaan penuh sampai `funding_deadline`. Tidak ada proposal yang gagal hanya karena masuk belakangan. |

## AI scoring

| ID | Aturan |
| --- | --- |
| BR-70 | Total skor dijumlahkan di Python dari tiga komponen. Angka total yang dikembalikan model dibuang tanpa dibaca. |
| BR-71 | Perbandingan dengan `score_threshold` dikerjakan di kode, bukan di dalam prompt. |
| BR-72 | Red flag berlevel `critical` menghasilkan `rejected` tanpa memandang total skor. |
| BR-73 | Skor di bawah `score_threshold` campaign menghasilkan `rejected`. |
| BR-74 | Kegagalan jaringan, timeout, atau validasi schema menghasilkan `scoring_status = failed` sementara status proposal tetap `submitted`. Tidak pernah `rejected`. |
| BR-75 | Transisi hasil scoring hanya ditulis bila proposal masih berstatus `submitted`. Job yang terpicu dua kali tidak menghasilkan dua transisi. |
| BR-76 | Setiap percobaan scoring membuat baris baru di `scoring_results`. Baris lama tidak pernah ditimpa. |
| BR-77 | `score_threshold` campaign dikunci setelah proposal pertama masuk, supaya penilaian antar proposal tetap sebanding. |
| BR-78 | Setiap komponen skor dibatasi rentangnya oleh validator Pydantic. Nilai di luar rentang memicu retry Instructor, dan kalau tetap gagal, BR-74 berlaku. |
| BR-79 | Tahap yang belum cair dianggap **macet** bila 30 hari lewat sejak tahap sebelumnya cair tanpa laporan masuk. Tahap yang sudah dilaporkan tidak pernah macet: bolanya ada di lead investor. |
| BR-80 | Lead investor boleh **mengajukan penghentian** proposal `funded` yang tahapnya macet. Pengajuan tidak mengembalikan dana apa pun. |
| BR-81 | UMKM punya **7 hari** menjawab pengajuan itu. Laporan yang masuk dalam jendela tersebut membatalkan pengajuan dan pendanaan berlanjut normal. |
| BR-82 | Lewat jendela tanpa laporan, **sisa dana yang belum cair** dikembalikan ke para pendana secara proporsional terhadap kontribusi masing-masing, dan proposal menjadi `failed` (T-10). Dana yang sudah cair tidak pernah ditarik kembali. |
| BR-83 | Pembagian pro-rata wajib berjumlah **sama persis** dengan sisa dana: tidak boleh menghilangkan maupun menciptakan satu rupiah pun. Sisa pembagian dialokasikan dengan metode largest remainder yang deterministik, bukan pembulatan float. |

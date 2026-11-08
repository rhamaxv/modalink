# 05. Modul Komunitas

Modul paling kecil, tapi perannya jelas: memberi investor sumber sinyal kedua yang tidak berasal
dari AI.

## Lihat daftar proposal

Publik, tanpa login, hanya proposal berstatus `listed` ke atas. Proposal `submitted` dan
`rejected` tidak pernah terlihat publik, karena memamerkan proposal yang ditolak akan merugikan
pemilik usaha tanpa memberi manfaat ke siapa pun.

Yang ditampilkan di kartu proposal: nama usaha, sektor, dana diminta, progres funding, skor total,
dan jumlah vote. Red flag **tidak** ditampilkan ke publik, hanya ke investor dan pemilik proposal.

## Vote

Butuh login dengan peran komunitas.

- Satu akun, satu vote per proposal.
- Toggle: menekan lagi membatalkan vote ([US-K2](02-personas-user-stories.md)).
- Vote tidak pernah mengubah status proposal. Dia hanya ditampilkan di sebelah skor AI sebagai
  sinyal tambahan ([BR-31](07-business-rules.md)).

Batasan terakhir itu disengaja. Kalau vote ikut menentukan status, proposal dengan jejaring sosial
luas akan mengalahkan proposal yang lebih baik, dan itu persis masalah yang ingin dihindari produk ini.

## Komentar

Butuh login dengan peran komunitas. Maksimal 500 karakter, tidak ada format kaya, tidak ada
lampiran. Terbaca oleh publik, investor, dan pemilik proposal.

Tidak ada balasan bertingkat, tidak ada reaksi, tidak ada moderasi. Komentar bisa dihapus hanya
oleh penulisnya sendiri.

## Yang komunitas tidak bisa lakukan

- Mendanai. Peran komunitas tidak punya akses ke endpoint pledge.
- Melihat brief AI lengkap atau red flag.
- Vote pada proposal yang belum `listed`.

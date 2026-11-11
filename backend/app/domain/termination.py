"""Aturan waktu penghentian proposal yang tahapnya macet. Fungsi murni.

Masalah yang ditutup aturan ini: sebelum ada mekanisme ini, satu-satunya
jalan keluar dari status `funded` adalah `completed`, dan itu menuntut
SELURUH milestone cair. UMKM yang berhenti melapor setelah tahap pertama
cair karena itu membuat sisa dana tertahan selamanya: lead investor tidak
bisa menyetujui (belum ada laporan), tidak bisa menolak (menolak hanya sah
untuk laporan yang masuk), dan tidak ada tenggat apa pun yang berlaku lagi
setelah proposal penuh.

Bentuk aturannya meniru yang dipakai platform escrow bermilestone (Upwork,
Cad Crowd): dana di escrow tidak boleh tertahan tanpa batas waktu, dan
KEDUA pihak punya jam, bukan hanya satu. UMKM tetap diberi kesempatan
melapor sebelum dananya ditarik kembali.
"""

from datetime import datetime, timedelta

# Sejak tahap sebelumnya cair, UMKM punya 30 hari untuk mengirim laporan
# tahap berikutnya. Lewat itu, tahapnya dianggap macet dan lead investor
# boleh mengajukan penghentian.
#
# Tiga puluh hari, bukan empat belas seperti jendela review Upwork: yang
# diukur di sini bukan waktu membaca laporan, melainkan waktu MENGERJAKAN
# satu tahap usaha, dan tahap seperti "membeli mesin lalu memasangnya"
# wajar memakan berminggu-minggu.
HARI_TAHAP_MACET = 30

# Setelah penghentian diajukan, UMKM punya 7 hari untuk tetap mengirim
# laporan. Laporan yang masuk dalam jendela ini MEMBATALKAN pengajuan, dan
# proses berjalan normal lagi.
#
# Angka ini yang dipakai Upwork untuk membantah permintaan refund, dan
# alasannya sama: pihak yang dananya akan ditarik harus punya kesempatan
# menjawab lebih dulu, bukan kehilangan dana karena diam beberapa hari.
HARI_JENDELA_JAWABAN = 7


def tahap_macet(disbursed_at_sebelumnya: datetime | None, sekarang: datetime) -> bool:
    """Apakah tahap berikutnya sudah lewat tenggat laporannya.

    `disbursed_at_sebelumnya` None berarti tahap sebelumnya belum cair, jadi
    tahap ini belum mulai dihitung sama sekali dan belum bisa macet.
    """
    if disbursed_at_sebelumnya is None:
        return False
    return sekarang >= disbursed_at_sebelumnya + timedelta(days=HARI_TAHAP_MACET)


def jendela_jawaban_habis(diajukan_pada: datetime | None, sekarang: datetime) -> bool:
    """Apakah jendela UMKM untuk menjawab pengajuan penghentian sudah lewat."""
    if diajukan_pada is None:
        return False
    return sekarang >= diajukan_pada + timedelta(days=HARI_JENDELA_JAWABAN)


def batas_jawaban(diajukan_pada: datetime) -> datetime:
    """Batas waktu yang ditampilkan ke layar, supaya kedua pihak melihat
    tanggal yang sama persis dengan yang dipakai mesinnya."""
    return diajukan_pada + timedelta(days=HARI_JENDELA_JAWABAN)

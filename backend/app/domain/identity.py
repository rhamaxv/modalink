"""Pemeriksaan bentuk identitas dan rekening. Fungsi murni, tanpa database.

Yang diperiksa di sini hanyalah BENTUK, dan itu batasnya. NIK yang lolos
seluruh aturan di bawah tetap bisa saja milik orang lain, tidak terdaftar,
atau dikarang begitu saja; satu-satunya cara mengetahuinya adalah bertanya ke
Dukcapil, dan itu tidak dilakukan produk ini. Lihat app/models/kyc.py.

Aturan NIK diambil dari struktur resminya (Permendagri 19/2010): enam digit
kode wilayah, enam digit tanggal lahir, empat digit nomor urut. Perempuan
ditandai dengan menambahkan 40 pada tanggal lahir, jadi 1-31 dan 41-71
sama-sama sah.
"""

import re
from datetime import date

PANJANG_NIK = 16
PANJANG_REKENING_MIN = 8
PANJANG_REKENING_MAX = 20

# [0-9], BUKAN \d. Di Python, \d cocok dengan digit Unicode apa pun, dan
# int() juga mau mengurainya. Akibatnya nyata, bukan teoretis: NIK yang
# ditulis dengan angka Arab-India ("٣٢٠١...") lolos seluruh aturan di bawah
# lalu disimpan apa adanya, sehingga dua baris KYC bisa menunjuk orang yang
# sama tanpa pernah bentrok di unique index, dan pencarian dengan angka biasa
# tidak akan menemukannya. Ditemukan lewat test, bukan lewat pembacaan kode.
_HANYA_ANGKA = re.compile(r"^[0-9]+$")


class IdentityError(ValueError):
    """Bentuk identitas tidak sah. Pesannya untuk dibaca pengguna."""


def normalkan_digit(nilai: str) -> str:
    """Membuang spasi, titik, dan tanda hubung yang biasa diketik orang.

    Nomor rekening sering disalin dengan pemisah ("1234-5678-90"), dan
    menolaknya karena itu memindahkan beban ke pengguna untuk kesalahan yang
    bukan kesalahan.
    """
    return re.sub(r"[\s.\-]", "", nilai or "")


def periksa_nik(nik_mentah: str, *, hari_ini: date | None = None) -> str:
    """Mengembalikan NIK yang sudah dinormalkan, atau melempar IdentityError."""
    nik = normalkan_digit(nik_mentah)
    if len(nik) != PANJANG_NIK or not _HANYA_ANGKA.match(nik):
        raise IdentityError("NIK harus 16 digit angka.")

    # Kode wilayah: provinsi, kabupaten/kota, kecamatan. Tidak ada yang
    # bernomor 00, jadi tiga pasang nol adalah tanda angka yang dikarang
    # asal panjangnya pas.
    if nik[0:2] == "00" or nik[2:4] == "00" or nik[4:6] == "00":
        raise IdentityError("Kode wilayah pada NIK tidak sah.")

    hari = int(nik[6:8])
    bulan = int(nik[8:10])
    tahun_dua = int(nik[10:12])

    # Perempuan: tanggal lahir ditambah 40.
    hari_lahir = hari - 40 if hari > 40 else hari
    if not 1 <= hari_lahir <= 31:
        raise IdentityError("Tanggal lahir pada NIK tidak sah.")
    if not 1 <= bulan <= 12:
        raise IdentityError("Bulan lahir pada NIK tidak sah.")

    # Dua digit tahun tanpa abad. Dipulihkan terhadap tahun berjalan: tahun
    # yang menghasilkan tanggal di masa depan pasti milik abad sebelumnya.
    acuan = hari_ini or date.today()
    abad = acuan.year // 100 * 100
    tahun = abad + tahun_dua
    try:
        lahir = date(tahun, bulan, hari_lahir)
    except ValueError:
        raise IdentityError("Tanggal lahir pada NIK tidak sah.") from None
    # Dibandingkan per TANGGAL, bukan per tahun. Versi pertama memakai
    # `tahun > acuan.year`, sehingga tanggal yang lebih akhir di tahun
    # berjalan tidak ikut digeser: NIK lahir 25 Desember 2026 yang diperiksa
    # pada 11 November 2026 menghasilkan umur negatif, lalu ditolak dengan
    # kalimat "harus berusia minimal 17 tahun" untuk tanggal yang bahkan
    # belum terjadi.
    if lahir > acuan:
        lahir = date(tahun - 100, bulan, hari_lahir)

    umur = (
        acuan.year - lahir.year - ((acuan.month, acuan.day) < (lahir.month, lahir.day))
    )
    # Hanya batas bawah. Batas atas sengaja tidak ada: pemulihan abad di
    # atas sudah menjepit tahun lahir ke seratus tahun terakhir, jadi umur
    # tidak pernah bisa melebihi 99. Versi pertama punya cabang "umur > 120"
    # yang tidak pernah bisa menyala, dan penjagaan yang tidak pernah
    # berjalan lebih buruk daripada tidak ada: ia terbaca seolah bekerja.
    #
    # Batasnya umur, bukan sekadar "bukan masa depan": pendanaan adalah
    # perjanjian, dan anak di bawah umur tidak bisa mengikatkan diri padanya.
    if umur < 17:
        raise IdentityError("Pemilik NIK harus berusia minimal 17 tahun.")

    # Nomor urut 0000 tidak pernah diterbitkan.
    if nik[12:16] == "0000":
        raise IdentityError("Nomor urut pada NIK tidak sah.")

    return nik


def periksa_rekening(nomor_mentah: str) -> str:
    """Mengembalikan nomor rekening yang sudah dinormalkan, atau melempar.

    Panjangnya saja yang diperiksa: setiap bank di Indonesia memakai panjang
    dan aturan sendiri, dan menebak-nebak aturan itu akan menolak rekening
    yang sebenarnya sah. Pemeriksaan sungguhan hanya bisa dilakukan bank
    yang bersangkutan.
    """
    nomor = normalkan_digit(nomor_mentah)
    if not _HANYA_ANGKA.match(nomor or ""):
        raise IdentityError("Nomor rekening hanya boleh berisi angka.")
    if not PANJANG_REKENING_MIN <= len(nomor) <= PANJANG_REKENING_MAX:
        raise IdentityError(
            f"Nomor rekening harus {PANJANG_REKENING_MIN} sampai "
            f"{PANJANG_REKENING_MAX} digit."
        )
    if len(set(nomor)) == 1:
        raise IdentityError("Nomor rekening tidak sah.")
    return nomor


def empat_terakhir(nilai: str) -> str:
    return nilai[-4:]


def samarkan(nilai: str) -> str:
    """ "3201••••••••4521": cukup untuk dikenali pemiliknya, tidak cukup untuk
    dipakai orang lain."""
    # Nilai sependek empat karakter tidak bisa disamarkan sambil tetap
    # menyisakan empat digit terakhir yang bisa dikenali pemiliknya.
    # Mengembalikannya utuh adalah kebocoran penuh dari fungsi yang namanya
    # menjanjikan penyamaran, dan pemanggil tidak punya cara mengetahuinya.
    if len(nilai) <= 4:
        raise IdentityError("Nilai terlalu pendek untuk disamarkan.")
    if len(nilai) <= 8:
        return "•" * (len(nilai) - 4) + nilai[-4:]
    return f"{nilai[:4]}{'•' * (len(nilai) - 8)}{nilai[-4:]}"

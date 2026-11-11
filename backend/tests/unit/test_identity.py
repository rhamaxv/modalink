"""Test bentuk NIK dan nomor rekening.

Semua pemanggilan periksa_nik memakai hari_ini eksplisit. Tanpa itu fungsinya
membaca date.today(), dan test batas usia 17 tahun akan berubah hasilnya
sendiri begitu tanggal berganti.
"""

from datetime import date

import pytest

from app.domain.identity import (
    IdentityError,
    empat_terakhir,
    periksa_nik,
    periksa_rekening,
    samarkan,
)

HARI_INI = date(2026, 11, 11)

# NIK acuan: wilayah 32-01-01, lahir 17 Agustus 1990, nomor urut 0001.
NIK_SAH = "3201011708900001"


def nik(
    *,
    region: str = "320101",
    day: str = "17",
    month: str = "08",
    year: str = "90",
    seq: str = "0001",
) -> str:
    """Menyusun NIK dari potongan yang sedang diuji, sisanya tetap sah.

    Supaya setiap test hanya mengubah satu hal, dan 16 digit yang panjang itu
    tidak perlu dibaca ulang untuk tahu bagian mana yang jadi pokok soal.
    """
    return region + day + month + year + seq


def test_valid_nik_is_accepted_and_returned_unchanged():
    assert periksa_nik(NIK_SAH, hari_ini=HARI_INI) == NIK_SAH


@pytest.mark.parametrize(
    "typed",
    [
        "3201-0117-0890-0001",
        " 3201 0117 0890 0001 ",
        "3201.0117.0890.0001",
        "3201 0117-0890.0001",
    ],
)
def test_nik_typed_with_separators_is_normalised(typed):
    assert periksa_nik(typed, hari_ini=HARI_INI) == NIK_SAH


@pytest.mark.parametrize(
    "value",
    ["320101170890001", "32010117089000012", "3201", ""],
)
def test_nik_of_the_wrong_length_is_rejected(value):
    with pytest.raises(IdentityError, match="16 digit angka"):
        periksa_nik(value, hari_ini=HARI_INI)


@pytest.mark.parametrize(
    "value",
    ["320101170890000A", "3201O11708900001", "abcdefghijklmnop"],
)
def test_nik_containing_letters_is_rejected(value):
    with pytest.raises(IdentityError, match="16 digit angka"):
        periksa_nik(value, hari_ini=HARI_INI)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(nik(region="000101"), id="provinsi"),
        pytest.param(nik(region="320001"), id="kabupaten"),
        pytest.param(nik(region="320100"), id="kecamatan"),
    ],
)
def test_region_code_00_is_rejected_at_every_level(value):
    with pytest.raises(IdentityError, match="Kode wilayah"):
        periksa_nik(value, hari_ini=HARI_INI)


def test_region_code_containing_a_zero_is_still_accepted():
    """Yang ditolak adalah pasangan "00" utuh, bukan sekadar ada angka nol di
    dalam kode wilayah; 32-01-01 sah dan dipakai sebagai NIK acuan."""
    assert periksa_nik(nik(region="320101"), hari_ini=HARI_INI) == NIK_SAH


@pytest.mark.parametrize("day", ["41", "51", "57", "71"])
def test_female_birth_day_offset_by_forty_is_accepted(day):
    """Perempuan ditandai dengan tanggal lahir + 40, jadi 41-71 sah persis
    seperti 1-31. Ini aturan yang paling sering disalahartikan sebagai cacat
    data."""
    assert periksa_nik(nik(day=day), hari_ini=HARI_INI) == nik(day=day)


def test_female_day_decodes_to_the_same_calendar_date_as_the_male_form():
    """Bukti 40 dikurangi sebelum tanggalnya dipakai, bukan hanya dipakai
    sebagai lolos-lolosan rentang angka."""
    # 11 + 40 = 51, tetap 11 November 2009, jadi usianya tetap tepat 17.
    perempuan_17 = nik(day="51", month="11", year="09")
    assert periksa_nik(perempuan_17, hari_ini=HARI_INI) == perempuan_17
    # 31 + 40 = 71, dan 31 Februari tetap tanggal yang tidak ada.
    with pytest.raises(IdentityError, match="Tanggal lahir"):
        periksa_nik(nik(day="71", month="02"), hari_ini=HARI_INI)


@pytest.mark.parametrize("day", ["00", "32", "35", "40", "72", "80", "99"])
def test_birth_day_outside_1_31_and_41_71_is_rejected(day):
    with pytest.raises(IdentityError, match="Tanggal lahir"):
        periksa_nik(nik(day=day), hari_ini=HARI_INI)


@pytest.mark.parametrize("month", ["00", "13", "40", "99"])
def test_birth_month_outside_1_12_is_rejected(month):
    with pytest.raises(IdentityError, match="Bulan lahir"):
        periksa_nik(nik(month=month), hari_ini=HARI_INI)


@pytest.mark.parametrize(
    ("day", "month"),
    [("31", "02"), ("30", "02"), ("31", "04"), ("31", "06")],
)
def test_calendar_date_that_does_not_exist_is_rejected(day, month):
    with pytest.raises(IdentityError, match="Tanggal lahir"):
        periksa_nik(nik(day=day, month=month), hari_ini=HARI_INI)


def test_february_29_is_rejected_in_a_common_year_and_accepted_in_a_leap_year():
    with pytest.raises(IdentityError, match="Tanggal lahir"):
        periksa_nik(nik(day="29", month="02", year="90"), hari_ini=HARI_INI)
    kabisat = nik(day="29", month="02", year="96")
    assert periksa_nik(kabisat, hari_ini=HARI_INI) == kabisat


def test_exactly_seventeen_years_old_is_accepted():
    # Lahir 11 November 2009, diperiksa pada 11 November 2026.
    ulang_tahun_ke_17 = nik(day="11", month="11", year="09")
    assert periksa_nik(ulang_tahun_ke_17, hari_ini=HARI_INI) == ulang_tahun_ke_17


def test_one_day_short_of_seventeen_is_rejected():
    """Pasangan dari test di atas: NIK yang sama, acuan digeser satu hari ke
    belakang. Kalau umurnya dibulatkan per tahun, keduanya tidak bisa
    sama-sama lulus."""
    ulang_tahun_ke_17 = nik(day="11", month="11", year="09")
    with pytest.raises(IdentityError, match="17 tahun"):
        periksa_nik(ulang_tahun_ke_17, hari_ini=date(2026, 11, 10))


@pytest.mark.parametrize("year", ["10", "15", "20", "25"])
def test_under_seventeen_is_rejected(year):
    with pytest.raises(IdentityError, match="17 tahun"):
        periksa_nik(nik(year=year), hari_ini=HARI_INI)


def test_two_digit_year_falling_in_the_future_is_pulled_back_one_century():
    """Tahun "99" dibaca 1999. Kalau dibaca 2099, usianya negatif dan NIK ini
    akan ditolak, jadi lulusnya test ini hanya mungkin kalau abadnya dipulihkan."""
    tahun_99 = nik(year="99")
    assert periksa_nik(tahun_99, hari_ini=HARI_INI) == tahun_99


def test_century_pivot_follows_hari_ini_instead_of_a_hardcoded_year():
    tahun_20 = nik(year="20")
    # Pada 2026, "20" jatuh di 2020: pemiliknya baru 6 tahun.
    with pytest.raises(IdentityError, match="17 tahun"):
        periksa_nik(tahun_20, hari_ini=date(2026, 11, 11))
    # Pada 2019, 2020 masih masa depan, jadi "20" dibaca 1920 dan lolos.
    assert periksa_nik(tahun_20, hari_ini=date(2019, 11, 11)) == tahun_20


def test_century_pivot_sits_at_the_current_two_digit_year():
    # "26" pada 2026 tetap 2026, dan bayi tahun ini belum 17.
    with pytest.raises(IdentityError, match="17 tahun"):
        periksa_nik(nik(year="26"), hari_ini=HARI_INI)
    # "27" sudah di masa depan, jadi digeser ke 1927.
    tahun_27 = nik(year="27")
    assert periksa_nik(tahun_27, hari_ini=HARI_INI) == tahun_27


def test_sequence_number_0000_is_rejected():
    with pytest.raises(IdentityError, match="Nomor urut"):
        periksa_nik(nik(seq="0000"), hari_ini=HARI_INI)


@pytest.mark.parametrize("seq", ["0001", "0010", "0100", "1000", "9999"])
def test_sequence_number_with_some_zeroes_is_still_accepted(seq):
    """Yang ditolak hanya 0000 utuh. Nomor urut bernol di sebagian digit adalah
    mayoritas NIK yang beredar."""
    assert periksa_nik(nik(seq=seq), hari_ini=HARI_INI) == nik(seq=seq)


def test_identity_error_is_a_value_error():
    """Lapisan service menangkap ValueError untuk diubah jadi 422; kalau
    IdentityError lepas dari rantai itu, errornya jadi 500."""
    with pytest.raises(ValueError):
        periksa_nik("bukan nik", hari_ini=HARI_INI)


@pytest.mark.parametrize("nomor", ["12345678", "123456789012", "12345678901234567890"])
def test_account_number_within_the_length_range_is_accepted(nomor):
    assert periksa_rekening(nomor) == nomor


@pytest.mark.parametrize(
    "nomor",
    ["1234567", "123456", "1", "123456789012345678901", "123456789012345678901234"],
)
def test_account_number_outside_the_length_range_is_rejected(nomor):
    with pytest.raises(IdentityError, match="8 sampai 20 digit"):
        periksa_rekening(nomor)


@pytest.mark.parametrize("nomor", ["1234567A", "rekening", "1234 5678 90a", "12-34-ab"])
def test_account_number_containing_letters_is_rejected(nomor):
    with pytest.raises(IdentityError, match="hanya boleh berisi angka"):
        periksa_rekening(nomor)


@pytest.mark.parametrize("nomor", ["11111111", "00000000", "9" * 20])
def test_account_number_of_one_repeated_digit_is_rejected(nomor):
    """Panjangnya pas dan semuanya angka, tapi tidak ada bank yang menerbitkan
    nomor begini; yang mengisi begitu sedang melewati formulir, bukan menyetor
    rekening."""
    with pytest.raises(IdentityError, match="tidak sah"):
        periksa_rekening(nomor)


@pytest.mark.parametrize(
    "typed",
    ["1234-5678-90", " 1234 5678 90 ", "1234.5678.90", "1234 5678-90"],
)
def test_account_number_separators_are_normalised(typed):
    assert periksa_rekening(typed) == "1234567890"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("3201011708900001", "3201••••••••0001"),
        ("1234567890", "1234••7890"),
        ("123456789", "1234•6789"),
        ("12345678", "••••5678"),
        ("123456", "••3456"),
    ],
)
def test_samarkan_hides_the_middle_and_keeps_the_length(value, expected):
    assert samarkan(value) == expected
    # Panjang yang tetap sama membuat kolom di UI tidak ikut berubah lebar
    # antara nilai yang disamarkan dan yang tidak.
    assert len(samarkan(value)) == len(value)


def test_samarkan_leaves_only_the_first_and_last_four_digits_readable():
    terbaca = [c for c in samarkan(NIK_SAH) if c.isdigit()]
    assert terbaca == list("32010001")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("3201011708900001", "0001"), ("1234567890", "7890"), ("1234", "1234")],
)
def test_empat_terakhir_returns_the_last_four_characters(value, expected):
    assert empat_terakhir(value) == expected


def test_empat_terakhir_of_a_shorter_value_returns_all_of_it():
    assert empat_terakhir("12") == "12"


class TestOnlyAsciiDigitsCount:
    """Bug sungguhan yang pernah ada di sini, dikunci supaya tidak kembali.

    Pola lamanya `^\\d+$`. Di Python, `\\d` cocok dengan digit Unicode apa pun
    dan `int()` juga mau menguraikannya, sehingga NIK yang ditulis dengan
    angka Arab-India lolos SELURUH aturan lalu disimpan apa adanya. Dua baris
    KYC bisa menunjuk orang yang sama tanpa pernah bentrok di unique index,
    dan pencarian dengan angka biasa tidak akan menemukannya.
    """

    # Dua sistem angka yang berbeda, keduanya cocok dengan \\d.
    @pytest.mark.parametrize(
        "nik_asing",
        [
            "٣٢٠١٠١١٧٠٨٩٠٠٠٠١",  # Arab-India
            "३२०१०११७०८९०००१",  # Devanagari
        ],
    )
    def test_rejects_a_nik_written_in_non_ascii_digits(self, nik_asing):
        with pytest.raises(IdentityError):
            periksa_nik(nik_asing, hari_ini=HARI_INI)

    def test_rejects_an_account_number_written_in_non_ascii_digits(self):
        with pytest.raises(IdentityError):
            periksa_rekening("١٢٣٤٥٦٧٨٩٠")

    def test_still_accepts_the_same_digits_written_in_ascii(self):
        """Sisi sebaliknya: perbaikannya menolak sistem angka lain, bukan
        menolak angka yang panjangnya kebetulan sama."""
        assert periksa_nik("3201011708900001", hari_ini=HARI_INI) == "3201011708900001"


class TestBirthDateIsComparedByDateNotYear:
    """Pemulihan abad membandingkan TANGGAL, bukan tahun.

    Versi lamanya memakai `tahun > acuan.year`, sehingga tanggal yang lebih
    akhir di tahun berjalan tidak ikut digeser ke abad sebelumnya.
    """

    def test_a_birth_date_later_this_year_is_read_as_the_previous_century(self):
        # Lahir 25 Desember, diperiksa 11 November tahun yang sama: tanggal
        # itu belum terjadi, jadi "26" harus dibaca 1926, bukan 2026.
        nik = "320101251226" + "0001"
        assert periksa_nik(nik, hari_ini=HARI_INI) == nik

    def test_a_birth_date_earlier_this_year_stays_in_this_century(self):
        # Lahir 1 Januari tahun yang sama: sudah terjadi, umurnya 0, dan
        # ditolak karena di bawah 17, bukan karena tanggalnya tidak sah.
        with pytest.raises(IdentityError, match="17 tahun"):
            periksa_nik("320101010126" + "0001", hari_ini=HARI_INI)


class TestMaskingNeverReturnsTheValueWhole:
    def test_refuses_a_value_too_short_to_mask(self):
        """Mengembalikan nilai pendek apa adanya adalah kebocoran penuh dari
        fungsi yang namanya menjanjikan penyamaran, dan pemanggil tidak punya
        cara mengetahuinya."""
        with pytest.raises(IdentityError):
            samarkan("1234")

    def test_always_hides_everything_except_the_last_four(self):
        hasil = samarkan("1234567890")
        assert hasil.endswith("7890")
        assert "123456" not in hasil

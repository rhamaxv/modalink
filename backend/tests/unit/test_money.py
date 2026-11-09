import pytest

from app.domain.money import MAX_RUPIAH, format_rupiah, parse_rupiah


def test_parse_accepts_positive_integer():
    assert parse_rupiah(5_000_000) == 5_000_000


@pytest.mark.parametrize("nilai", [0, -1, -5_000_000])
def test_br54_parse_rejects_zero_and_negative(nilai):
    with pytest.raises(ValueError, match="harus lebih besar dari nol"):
        parse_rupiah(nilai)


@pytest.mark.parametrize("nilai", ["1e9", 1_000_000.5, "5.000.000", None, "abc", True])
def test_rf2_parse_rejects_non_integer_forms(nilai):
    with pytest.raises(ValueError):
        parse_rupiah(nilai)


def test_rf2_parse_rejects_out_of_bigint_range():
    with pytest.raises(ValueError, match="terlalu besar"):
        parse_rupiah(MAX_RUPIAH + 1)


def test_format_uses_dot_as_thousands_separator():
    assert format_rupiah(5_000_000) == "Rp5.000.000"
    assert format_rupiah(750) == "Rp750"

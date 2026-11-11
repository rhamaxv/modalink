"""Pembagian sisa dana ke investor. Yang diuji terutama satu hal: jumlah
keluaran sama persis dengan sisa, berapa pun bentuk masukannya.

Tidak ada hypothesis di dependensi repo ini, jadi test berbasis properti di
bawah memakai random.Random dengan seed tetap: kasusnya banyak dan beragam,
tapi kegagalannya tetap bisa diulang persis.
"""

import random
from uuid import UUID

import pytest

from app.domain.refund_split import KontribusiPledge, bagi_sisa_pro_rata

# UUID yang berurutan, supaya test yang menguji pemutus seri bisa menyebut
# pemenangnya dengan pasti. Pemutus serinya pledge_id terkecil.
P1, P2, P3 = UUID(int=1), UUID(int=2), UUID(int=3)
INV_A, INV_B, INV_C = UUID(int=101), UUID(int=102), UUID(int=103)


def _kontribusi(*pasangan: tuple[UUID, UUID, int]) -> list[KontribusiPledge]:
    return [KontribusiPledge(pid, inv, amount) for pid, inv, amount in pasangan]


def test_two_investors_split_the_remaining_fund_by_share():
    # A 6 juta dan B 4 juta dari total 10 juta; 5 juta sudah cair, 5 juta sisa.
    kontribusi = _kontribusi((P1, INV_A, 6_000_000), (P2, INV_B, 4_000_000))
    assert bagi_sisa_pro_rata(kontribusi, 5_000_000) == {
        P1: 3_000_000,
        P2: 2_000_000,
    }


def test_indivisible_amount_gives_the_spare_rupiah_to_the_largest_remainder():
    # Total 7 juta, sisa 1 juta. Bagian dasar hasil pembagian bulat:
    #   A 3jt/7jt -> 428_571 sisa pembagian 3.000.000
    #   B 2jt/7jt -> 285_714 sisa pembagian 2.000.000
    #   C 2jt/7jt -> 285_714 sisa pembagian 2.000.000
    # Jumlahnya 999.999, kurang satu rupiah. Rupiah itu jatuh ke A karena
    # pecahan yang terpotong darinya paling besar.
    kontribusi = _kontribusi(
        (P1, INV_A, 3_000_000), (P2, INV_B, 2_000_000), (P3, INV_C, 2_000_000)
    )
    hasil = bagi_sisa_pro_rata(kontribusi, 1_000_000)
    assert hasil == {P1: 428_572, P2: 285_714, P3: 285_714}
    assert sum(hasil.values()) == 1_000_000


def test_tie_on_remainder_is_broken_by_the_smallest_pledge_id():
    # Komposisi sama, sisa 2 juta. Bagian dasar berjumlah 1.999.998, jadi ada
    # dua rupiah yang harus dibagikan. Yang pertama ke A (pecahan 6.000.000).
    # Yang kedua diperebutkan B dan C: pecahan sama (4.000.000) dan amount sama
    # (2 juta), sehingga pemutusnya pledge_id terkecil, yaitu P2.
    kontribusi = _kontribusi(
        (P1, INV_A, 3_000_000), (P2, INV_B, 2_000_000), (P3, INV_C, 2_000_000)
    )
    hasil = bagi_sisa_pro_rata(kontribusi, 2_000_000)
    assert hasil == {P1: 857_143, P2: 571_429, P3: 571_428}
    assert sum(hasil.values()) == 2_000_000


def test_result_does_not_depend_on_input_order():
    kontribusi = [
        KontribusiPledge(UUID(int=i), UUID(int=1000 + i), 1_000_000 + i * 7)
        for i in range(1, 9)
    ]
    rng = random.Random(20261111)
    acuan = bagi_sisa_pro_rata(kontribusi, 3_333_333)
    for _ in range(50):
        teracak = list(kontribusi)
        rng.shuffle(teracak)
        assert bagi_sisa_pro_rata(teracak, 3_333_333) == acuan


def test_empty_contribution_list_with_nothing_left_returns_nothing():
    assert bagi_sisa_pro_rata([], 0) == {}


def test_empty_contribution_list_cannot_absorb_money():
    with pytest.raises(ValueError, match="melebihi total kontribusi"):
        bagi_sisa_pro_rata([], 1)


def test_zero_remaining_fund_refunds_nothing_to_everyone():
    kontribusi = _kontribusi((P1, INV_A, 6_000_000), (P2, INV_B, 4_000_000))
    assert bagi_sisa_pro_rata(kontribusi, 0) == {P1: 0, P2: 0}


def test_full_refund_returns_each_contribution_untouched():
    kontribusi = _kontribusi(
        (P1, INV_A, 1_234_567), (P2, INV_B, 7_654_321), (P3, INV_C, 9)
    )
    total = 1_234_567 + 7_654_321 + 9
    assert bagi_sisa_pro_rata(kontribusi, total) == {
        P1: 1_234_567,
        P2: 7_654_321,
        P3: 9,
    }


def test_single_investor_takes_the_whole_remaining_fund():
    kontribusi = _kontribusi((P1, INV_A, 12_000_000))
    assert bagi_sisa_pro_rata(kontribusi, 7_000_001) == {P1: 7_000_001}


def test_hundreds_of_billions_are_split_without_losing_a_rupiah():
    # Nominal sebesar ini yang membuat float gagal: hasil kali sisa dan amount
    # jauh melewati 2^53, sehingga pembagian pecahan akan meleset ribuan rupiah.
    kontribusi = _kontribusi(
        (P1, INV_A, 333_333_333_333),
        (P2, INV_B, 666_666_666_667),
        (P3, INV_C, 999_999_999_999),
    )
    total = sum(k.amount for k in kontribusi)
    sisa = total - 1
    hasil = bagi_sisa_pro_rata(kontribusi, sisa)
    assert sum(hasil.values()) == sisa
    for k in kontribusi:
        # Kuota Hare: setiap bagian menyimpang kurang dari satu rupiah dari
        # porsi sebenarnya. Diperiksa tanpa pecahan sama sekali.
        assert abs(hasil[k.pledge_id] * total - sisa * k.amount) < total


def test_remaining_fund_larger_than_contributions_is_rejected():
    kontribusi = _kontribusi((P1, INV_A, 1_000_000))
    with pytest.raises(ValueError, match="melebihi total kontribusi"):
        bagi_sisa_pro_rata(kontribusi, 1_000_001)


def test_negative_remaining_fund_is_rejected():
    kontribusi = _kontribusi((P1, INV_A, 1_000_000))
    with pytest.raises(ValueError, match="tidak boleh negatif"):
        bagi_sisa_pro_rata(kontribusi, -1)


def test_negative_contribution_is_rejected():
    kontribusi = _kontribusi((P1, INV_A, 1_000_000), (P2, INV_B, -5))
    with pytest.raises(ValueError, match="Kontribusi pledge tidak boleh negatif"):
        bagi_sisa_pro_rata(kontribusi, 100)


def test_duplicate_pledge_id_is_rejected_instead_of_silently_losing_money():
    # Dict keluaran dikunci pledge_id, jadi baris kedua akan menimpa yang
    # pertama dan jumlah refund diam-diam tidak lagi sama dengan sisa.
    kontribusi = _kontribusi((P1, INV_A, 1_000_000), (P1, INV_B, 2_000_000))
    with pytest.raises(ValueError, match="lebih dari sekali"):
        bagi_sisa_pro_rata(kontribusi, 1_500_000)


def test_all_zero_contributions_can_only_refund_nothing():
    kontribusi = _kontribusi((P1, INV_A, 0), (P2, INV_B, 0))
    assert bagi_sisa_pro_rata(kontribusi, 0) == {P1: 0, P2: 0}
    with pytest.raises(ValueError, match="melebihi total kontribusi"):
        bagi_sisa_pro_rata(kontribusi, 1)


@pytest.mark.parametrize("seed", range(20))
def test_sum_of_refunds_always_equals_the_remaining_fund(seed: int):
    """Properti utama, diuji pada 20 x 30 kombinasi acak."""
    rng = random.Random(seed)
    for _ in range(30):
        jumlah_investor = rng.randint(1, 15)
        # Rentang nominal sengaja lebar: dari receh sampai ratusan miliar,
        # karena kesalahan pembulatan paling mudah muncul saat satu kontribusi
        # jauh lebih besar dari yang lain.
        kontribusi = [
            KontribusiPledge(
                UUID(int=rng.getrandbits(128)),
                UUID(int=rng.getrandbits(128)),
                rng.randint(0, 10 ** rng.randint(0, 12)),
            )
            for _ in range(jumlah_investor)
        ]
        total = sum(k.amount for k in kontribusi)
        sisa = rng.randint(0, total)

        hasil = bagi_sisa_pro_rata(kontribusi, sisa)

        assert sum(hasil.values()) == sisa
        assert len(hasil) == jumlah_investor
        assert all(nominal >= 0 for nominal in hasil.values())
        if total:
            for k in kontribusi:
                assert abs(hasil[k.pledge_id] * total - sisa * k.amount) < total

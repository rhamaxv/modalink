import pytest

from app.domain.milestone_plan import MilestoneDraft, validate_milestone_plan


def draft(seq: int, amount: int) -> MilestoneDraft:
    return MilestoneDraft(
        seq=seq, title=f"Tahap {seq}", description="x" * 20, amount=amount
    )


def test_rencana_valid_lolos():
    validate_milestone_plan([draft(1, 5_000_000), draft(2, 5_000_000)], 10_000_000)


def test_br14_kurang_dari_dua_milestone_ditolak():
    with pytest.raises(ValueError, match="minimal dua"):
        validate_milestone_plan([draft(1, 10_000_000)], 10_000_000)


def test_br14_jumlah_tidak_sama_ditolak_dan_menyebut_selisihnya():
    with pytest.raises(ValueError, match="kurang Rp1.000.000"):
        validate_milestone_plan([draft(1, 5_000_000), draft(2, 4_000_000)], 10_000_000)


def test_br14_jumlah_berlebih_juga_menyebut_selisihnya():
    with pytest.raises(ValueError, match="lebih Rp2.000.000"):
        validate_milestone_plan([draft(1, 6_000_000), draft(2, 6_000_000)], 10_000_000)


def test_br15_seq_harus_berurutan_dari_satu():
    with pytest.raises(ValueError, match="berurutan"):
        validate_milestone_plan([draft(1, 5_000_000), draft(3, 5_000_000)], 10_000_000)


def test_br16_amount_nol_ditolak():
    with pytest.raises(ValueError):
        validate_milestone_plan([draft(1, 10_000_000), draft(2, 0)], 10_000_000)

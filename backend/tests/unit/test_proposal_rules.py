import pytest

from app.domain.milestone_plan import MilestoneDraft, validate_milestone_plan


def draft(seq: int, amount: int) -> MilestoneDraft:
    return MilestoneDraft(
        seq=seq, title=f"Tahap {seq}", description="x" * 20, amount=amount
    )


def test_valid_plan_passes():
    validate_milestone_plan([draft(1, 5_000_000), draft(2, 5_000_000)], 10_000_000)


def test_br14_fewer_than_two_milestones_rejected():
    with pytest.raises(ValueError, match="minimal dua"):
        validate_milestone_plan([draft(1, 10_000_000)], 10_000_000)


def test_br14_amount_mismatch_rejected_and_reports_difference():
    with pytest.raises(ValueError, match="kurang Rp1.000.000"):
        validate_milestone_plan([draft(1, 5_000_000), draft(2, 4_000_000)], 10_000_000)


def test_br14_amount_surplus_also_reports_difference():
    with pytest.raises(ValueError, match="lebih Rp2.000.000"):
        validate_milestone_plan([draft(1, 6_000_000), draft(2, 6_000_000)], 10_000_000)


def test_br15_seq_must_be_sequential_from_one():
    with pytest.raises(ValueError, match="berurutan"):
        validate_milestone_plan([draft(1, 5_000_000), draft(3, 5_000_000)], 10_000_000)


def test_br16_zero_amount_rejected():
    with pytest.raises(ValueError):
        validate_milestone_plan([draft(1, 10_000_000), draft(2, 0)], 10_000_000)


def test_t3_milestone_plan_over_maximum_count_rejected():
    """Diulang di domain, bukan hanya di schemas/proposal.py Field(max_length
    =30): pemanggil lain (test, job batch) bisa menyusun MilestoneDraft
    langsung tanpa lewat ProposalIn sama sekali, sama seperti alasan
    MIN_PLEDGE_AMOUNT diulang di services/pledge.py."""
    drafts = [draft(i, 1) for i in range(1, 32)]
    with pytest.raises(ValueError, match="maksimal 30"):
        validate_milestone_plan(drafts, 31)

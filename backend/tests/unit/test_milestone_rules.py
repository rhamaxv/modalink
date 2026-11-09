"""Prasyarat pelaporan dan pencairan milestone (BR-40 sampai BR-43, D-13)."""

import pytest

from app.domain.milestone_rules import (
    can_be_reported,
    disbursement_precondition,
    requires_report,
)
from app.domain.transitions import MilestoneStatus as M


def test_d13_first_milestone_does_not_need_report():
    assert requires_report(seq=1) is False


@pytest.mark.parametrize("seq", [2, 3, 7])
def test_br42_later_milestones_need_report(seq):
    assert requires_report(seq) is True


def test_br41_first_milestone_cannot_be_reported():
    assert can_be_reported(seq=1, previous_status=None) is False


def test_br43_second_milestone_reportable_after_first_disbursed():
    assert can_be_reported(seq=2, previous_status=M.DISBURSED) is True


@pytest.mark.parametrize("status", [M.PENDING, M.REPORTED])
def test_br43_second_milestone_not_reportable_before_first_disbursed(status):
    assert can_be_reported(seq=2, previous_status=status) is False


def test_br43_disbursement_precondition_rejects_skipped_milestone():
    with pytest.raises(ValueError, match="Milestone sebelumnya"):
        disbursement_precondition(
            seq=3, previous_status=M.PENDING, proposal_funded=True
        )


def test_br40_disbursement_precondition_rejects_unfunded_proposal():
    with pytest.raises(ValueError, match="belum funded"):
        disbursement_precondition(seq=1, previous_status=None, proposal_funded=False)

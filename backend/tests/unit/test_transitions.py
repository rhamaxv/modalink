import pytest

from app.domain.transitions import (
    IllegalTransition,
    MilestoneEvent,
    MilestoneStatus,
    ProposalEvent,
    ProposalStatus,
    apply_milestone,
    apply_proposal,
)


def test_t01_submitted_ke_listed():
    assert apply_proposal(ProposalStatus.SUBMITTED, ProposalEvent.SCORING_LULUS) \
        is ProposalStatus.LISTED


def test_t03_listed_ke_partially_funded():
    assert apply_proposal(ProposalStatus.LISTED, ProposalEvent.PLEDGE_SEBAGIAN) \
        is ProposalStatus.PARTIALLY_FUNDED


def test_t07_partially_funded_kembali_ke_listed_saat_semua_pledge_batal():
    assert apply_proposal(ProposalStatus.PARTIALLY_FUNDED, ProposalEvent.PLEDGE_KOSONG) \
        is ProposalStatus.LISTED


@pytest.mark.parametrize("status", [
    ProposalStatus.REJECTED, ProposalStatus.FAILED, ProposalStatus.COMPLETED,
])
@pytest.mark.parametrize("event", list(ProposalEvent))
def test_status_terminal_menolak_semua_event(status, event):
    with pytest.raises(IllegalTransition):
        apply_proposal(status, event)


def test_t21_milestone_pertama_cair_tanpa_laporan():
    assert apply_milestone(MilestoneStatus.PENDING, MilestoneEvent.APPROVE_TANPA_LAPORAN) \
        is MilestoneStatus.DISBURSED


def test_t23_reject_mengembalikan_milestone_ke_pending():
    assert apply_milestone(MilestoneStatus.REPORTED, MilestoneEvent.REJECT) \
        is MilestoneStatus.PENDING


def test_illegal_transition_menyebut_status_dan_event():
    with pytest.raises(IllegalTransition) as err:
        apply_proposal(ProposalStatus.FUNDED, ProposalEvent.PLEDGE_SEBAGIAN)
    assert "funded" in str(err.value)
    assert err.value.current is ProposalStatus.FUNDED

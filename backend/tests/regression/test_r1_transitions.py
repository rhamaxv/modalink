"""R1: setiap kombinasi status kali event diuji, yang legal maupun yang harus ditolak."""
import itertools

import pytest

from app.domain.transitions import (
    MILESTONE_MAP,
    PROPOSAL_MAP,
    IllegalTransition,
    MilestoneEvent,
    MilestoneStatus,
    ProposalEvent,
    ProposalStatus,
    apply_milestone,
    apply_proposal,
)

PROPOSAL_KOMBINASI = list(itertools.product(ProposalStatus, ProposalEvent))
MILESTONE_KOMBINASI = list(itertools.product(MilestoneStatus, MilestoneEvent))


@pytest.mark.parametrize("status,event", PROPOSAL_KOMBINASI)
def test_r1_proposal_setiap_kombinasi_sesuai_peta(status, event):
    if (status, event) in PROPOSAL_MAP:
        assert apply_proposal(status, event) is PROPOSAL_MAP[(status, event)]
    else:
        with pytest.raises(IllegalTransition):
            apply_proposal(status, event)


@pytest.mark.parametrize("status,event", MILESTONE_KOMBINASI)
def test_r1_milestone_setiap_kombinasi_sesuai_peta(status, event):
    if (status, event) in MILESTONE_MAP:
        assert apply_milestone(status, event) is MILESTONE_MAP[(status, event)]
    else:
        with pytest.raises(IllegalTransition):
            apply_milestone(status, event)


def test_r1_jumlah_transisi_proposal_sesuai_spec():
    """Mengunci jumlahnya ke spec. Menambah transisi tanpa memperbarui
    08-state-machines.md akan membuat test ini merah."""
    assert len(PROPOSAL_MAP) == 9   # T-01 sampai T-09


def test_r1_jumlah_transisi_milestone_sesuai_spec():
    assert len(MILESTONE_MAP) == 4  # T-20 sampai T-23


@pytest.mark.parametrize("terminal", [
    ProposalStatus.REJECTED, ProposalStatus.FAILED, ProposalStatus.COMPLETED,
])
def test_r1_status_terminal_tidak_punya_jalan_keluar(terminal):
    assert not any(s is terminal for s, _ in PROPOSAL_MAP)

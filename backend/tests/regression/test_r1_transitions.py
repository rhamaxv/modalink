"""R1: setiap kombinasi status kali event diuji, yang legal maupun yang harus ditolak."""

import itertools

import pytest

from app.domain.transitions import (
    CAMPAIGN_MAP,
    MILESTONE_MAP,
    PROPOSAL_MAP,
    REPORT_MAP,
    SCORING_MAP,
    CampaignEvent,
    CampaignStatus,
    IllegalTransition,
    MilestoneEvent,
    MilestoneStatus,
    ProposalEvent,
    ProposalStatus,
    ReportEvent,
    ReportStatus,
    ScoringEvent,
    ScoringStatus,
    apply_campaign,
    apply_milestone,
    apply_proposal,
    apply_report,
    apply_scoring,
)

PROPOSAL_KOMBINASI = list(itertools.product(ProposalStatus, ProposalEvent))
MILESTONE_KOMBINASI = list(itertools.product(MilestoneStatus, MilestoneEvent))
REPORT_KOMBINASI = list(itertools.product(ReportStatus, ReportEvent))
CAMPAIGN_KOMBINASI = list(itertools.product(CampaignStatus, CampaignEvent))
SCORING_KOMBINASI = list(itertools.product(ScoringStatus, ScoringEvent))


@pytest.mark.parametrize("status,event", PROPOSAL_KOMBINASI)
def test_r1_proposal_every_combination_matches_map(status, event):
    if (status, event) in PROPOSAL_MAP:
        assert apply_proposal(status, event) is PROPOSAL_MAP[(status, event)]
    else:
        with pytest.raises(IllegalTransition):
            apply_proposal(status, event)


@pytest.mark.parametrize("status,event", MILESTONE_KOMBINASI)
def test_r1_milestone_every_combination_matches_map(status, event):
    if (status, event) in MILESTONE_MAP:
        assert apply_milestone(status, event) is MILESTONE_MAP[(status, event)]
    else:
        with pytest.raises(IllegalTransition):
            apply_milestone(status, event)


@pytest.mark.parametrize("status,event", REPORT_KOMBINASI)
def test_r1_report_every_combination_matches_map(status, event):
    if (status, event) in REPORT_MAP:
        assert apply_report(status, event) is REPORT_MAP[(status, event)]
    else:
        with pytest.raises(IllegalTransition):
            apply_report(status, event)


@pytest.mark.parametrize("status,event", CAMPAIGN_KOMBINASI)
def test_r1_campaign_every_combination_matches_map(status, event):
    if (status, event) in CAMPAIGN_MAP:
        assert apply_campaign(status, event) is CAMPAIGN_MAP[(status, event)]
    else:
        with pytest.raises(IllegalTransition):
            apply_campaign(status, event)


@pytest.mark.parametrize("status,event", SCORING_KOMBINASI)
def test_r1_scoring_every_combination_matches_map(status, event):
    if (status, event) in SCORING_MAP:
        assert apply_scoring(status, event) is SCORING_MAP[(status, event)]
    else:
        with pytest.raises(IllegalTransition):
            apply_scoring(status, event)


def test_r1_proposal_transition_count_matches_spec():
    """Mengunci jumlahnya ke spec. Menambah transisi tanpa memperbarui
    08-state-machines.md akan membuat test ini merah."""
    assert len(PROPOSAL_MAP) == 9  # T-01 sampai T-09


def test_r1_milestone_transition_count_matches_spec():
    assert len(MILESTONE_MAP) == 4  # T-20 sampai T-23


def test_r1_report_transition_count_matches_spec():
    assert len(REPORT_MAP) == 2  # T-30, T-31


def test_r1_campaign_transition_count_matches_spec():
    assert len(CAMPAIGN_MAP) == 2  # T-40, T-41


def test_r1_scoring_transition_count_matches_spec():
    assert len(SCORING_MAP) == 4  # T-50 sampai T-53


@pytest.mark.parametrize(
    "terminal",
    [
        ProposalStatus.REJECTED,
        ProposalStatus.FAILED,
        ProposalStatus.COMPLETED,
    ],
)
def test_r1_terminal_status_has_no_way_out(terminal):
    assert not any(s is terminal for s, _ in PROPOSAL_MAP)

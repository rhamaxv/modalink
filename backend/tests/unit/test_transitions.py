import pytest

from app.domain.transitions import (
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


def test_t01_submitted_to_listed():
    assert (
        apply_proposal(ProposalStatus.SUBMITTED, ProposalEvent.SCORING_LULUS)
        is ProposalStatus.LISTED
    )


def test_t03_listed_to_partially_funded():
    assert (
        apply_proposal(ProposalStatus.LISTED, ProposalEvent.PLEDGE_SEBAGIAN)
        is ProposalStatus.PARTIALLY_FUNDED
    )


def test_t07_partially_funded_returns_to_listed_when_all_pledges_cancelled():
    assert (
        apply_proposal(ProposalStatus.PARTIALLY_FUNDED, ProposalEvent.PLEDGE_KOSONG)
        is ProposalStatus.LISTED
    )


@pytest.mark.parametrize(
    "status",
    [
        ProposalStatus.REJECTED,
        ProposalStatus.FAILED,
        ProposalStatus.COMPLETED,
    ],
)
@pytest.mark.parametrize("event", list(ProposalEvent))
def test_terminal_status_rejects_every_event(status, event):
    with pytest.raises(IllegalTransition):
        apply_proposal(status, event)


def test_t21_first_milestone_disburses_without_report():
    assert (
        apply_milestone(MilestoneStatus.PENDING, MilestoneEvent.APPROVE_TANPA_LAPORAN)
        is MilestoneStatus.DISBURSED
    )


def test_t23_reject_returns_milestone_to_pending():
    assert (
        apply_milestone(MilestoneStatus.REPORTED, MilestoneEvent.REJECT)
        is MilestoneStatus.PENDING
    )


def test_illegal_transition_names_status_and_event():
    with pytest.raises(IllegalTransition) as err:
        apply_proposal(ProposalStatus.FUNDED, ProposalEvent.PLEDGE_SEBAGIAN)
    assert "funded" in str(err.value)
    assert err.value.current is ProposalStatus.FUNDED


def test_t30_approve_marks_report_approved():
    assert (
        apply_report(ReportStatus.PENDING, ReportEvent.APPROVE) is ReportStatus.APPROVED
    )


def test_t31_reject_marks_report_rejected():
    assert (
        apply_report(ReportStatus.PENDING, ReportEvent.REJECT) is ReportStatus.REJECTED
    )


def test_already_reviewed_report_cannot_be_reviewed_again():
    with pytest.raises(IllegalTransition):
        apply_report(ReportStatus.APPROVED, ReportEvent.REJECT)


def test_t40_campaign_closed_manually():
    assert (
        apply_campaign(CampaignStatus.OPEN, CampaignEvent.TUTUP_MANUAL)
        is CampaignStatus.CLOSED
    )


def test_t41_campaign_closed_because_apply_deadline_passed():
    assert (
        apply_campaign(CampaignStatus.OPEN, CampaignEvent.APPLY_DEADLINE_LEWAT)
        is CampaignStatus.CLOSED
    )


def test_closed_campaign_cannot_be_closed_again():
    with pytest.raises(IllegalTransition):
        apply_campaign(CampaignStatus.CLOSED, CampaignEvent.TUTUP_MANUAL)


def test_t50_through_t53_scoring_flow():
    assert (
        apply_scoring(ScoringStatus.PENDING, ScoringEvent.AMBIL)
        is ScoringStatus.PROCESSING
    )
    assert (
        apply_scoring(ScoringStatus.PROCESSING, ScoringEvent.SELESAI)
        is ScoringStatus.DONE
    )
    assert (
        apply_scoring(ScoringStatus.PROCESSING, ScoringEvent.GAGAL)
        is ScoringStatus.FAILED
    )
    assert (
        apply_scoring(ScoringStatus.FAILED, ScoringEvent.NILAI_ULANG)
        is ScoringStatus.PENDING
    )


def test_scoring_already_done_is_terminal():
    with pytest.raises(IllegalTransition):
        apply_scoring(ScoringStatus.DONE, ScoringEvent.AMBIL)

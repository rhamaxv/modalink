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


def test_t01_submitted_ke_listed():
    assert (
        apply_proposal(ProposalStatus.SUBMITTED, ProposalEvent.SCORING_LULUS)
        is ProposalStatus.LISTED
    )


def test_t03_listed_ke_partially_funded():
    assert (
        apply_proposal(ProposalStatus.LISTED, ProposalEvent.PLEDGE_SEBAGIAN)
        is ProposalStatus.PARTIALLY_FUNDED
    )


def test_t07_partially_funded_kembali_ke_listed_saat_semua_pledge_batal():
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
def test_status_terminal_menolak_semua_event(status, event):
    with pytest.raises(IllegalTransition):
        apply_proposal(status, event)


def test_t21_milestone_pertama_cair_tanpa_laporan():
    assert (
        apply_milestone(MilestoneStatus.PENDING, MilestoneEvent.APPROVE_TANPA_LAPORAN)
        is MilestoneStatus.DISBURSED
    )


def test_t23_reject_mengembalikan_milestone_ke_pending():
    assert (
        apply_milestone(MilestoneStatus.REPORTED, MilestoneEvent.REJECT)
        is MilestoneStatus.PENDING
    )


def test_illegal_transition_menyebut_status_dan_event():
    with pytest.raises(IllegalTransition) as err:
        apply_proposal(ProposalStatus.FUNDED, ProposalEvent.PLEDGE_SEBAGIAN)
    assert "funded" in str(err.value)
    assert err.value.current is ProposalStatus.FUNDED


def test_t30_approve_menandai_laporan_approved():
    assert (
        apply_report(ReportStatus.PENDING, ReportEvent.APPROVE) is ReportStatus.APPROVED
    )


def test_t31_reject_menandai_laporan_rejected():
    assert (
        apply_report(ReportStatus.PENDING, ReportEvent.REJECT) is ReportStatus.REJECTED
    )


def test_laporan_yang_sudah_dinilai_tidak_bisa_dinilai_ulang():
    with pytest.raises(IllegalTransition):
        apply_report(ReportStatus.APPROVED, ReportEvent.REJECT)


def test_t40_campaign_ditutup_manual():
    assert (
        apply_campaign(CampaignStatus.OPEN, CampaignEvent.TUTUP_MANUAL)
        is CampaignStatus.CLOSED
    )


def test_t41_campaign_tertutup_karena_apply_deadline_lewat():
    assert (
        apply_campaign(CampaignStatus.OPEN, CampaignEvent.APPLY_DEADLINE_LEWAT)
        is CampaignStatus.CLOSED
    )


def test_campaign_tertutup_tidak_bisa_ditutup_lagi():
    with pytest.raises(IllegalTransition):
        apply_campaign(CampaignStatus.CLOSED, CampaignEvent.TUTUP_MANUAL)


def test_t50_sampai_t53_alur_scoring():
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


def test_scoring_yang_sudah_done_adalah_terminal():
    with pytest.raises(IllegalTransition):
        apply_scoring(ScoringStatus.DONE, ScoringEvent.AMBIL)

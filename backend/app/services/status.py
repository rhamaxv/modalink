"""Jembatan nilai antara enum transisi domain dan enum kolom database.

Nilai stringnya sama, kelasnya beda, dan menulis hasil apply_* langsung ke kolom
gagal tanpa bersuara: mypy menolaknya dan perbandingan `is` di test selalu salah.
Konversinya dipusatkan di sini supaya tests/unit/test_transition_guard.py bisa
menegakkannya, bukan supaya lebih singkat.

advance_milestone dan advance_report ditambahkan di sini bersama Task 2 fase
07 (laporan progres milestone): begitu services/milestone.py butuh memajukan
status milestone atau laporan, pola yang benar harus sudah ada di modul ini,
bukan memanggil apply_milestone/apply_report mentah seperti yang sempat
terjadi di services/scoring.py dan services/campaign.py sebelum Task 0.
"""

from app.domain.transitions import (
    CampaignEvent,
    MilestoneEvent,
    ProposalEvent,
    ReportEvent,
    ScoringEvent,
    apply_campaign,
    apply_milestone,
    apply_proposal,
    apply_report,
    apply_scoring,
)
from app.domain.transitions import CampaignStatus as DomainCampaignStatus
from app.domain.transitions import MilestoneStatus as DomainMilestoneStatus
from app.domain.transitions import ProposalStatus as DomainProposalStatus
from app.domain.transitions import ReportStatus as DomainReportStatus
from app.domain.transitions import ScoringStatus as DomainScoringStatus
from app.models.campaign import Campaign, CampaignStatus
from app.models.milestone_report import MilestoneReport
from app.models.milestone_report import ReportStatus as MilestoneReportStatus
from app.models.proposal import (
    MilestoneStatus,
    Proposal,
    ProposalMilestone,
    ProposalStatus,
    ScoringStatus,
)


def advance_proposal(proposal: Proposal, event: ProposalEvent) -> None:
    baru = apply_proposal(DomainProposalStatus(proposal.status.value), event)
    proposal.status = ProposalStatus(baru.value)


def advance_scoring(proposal: Proposal, event: ScoringEvent) -> None:
    baru = apply_scoring(DomainScoringStatus(proposal.scoring_status.value), event)
    proposal.scoring_status = ScoringStatus(baru.value)


def advance_campaign(campaign: Campaign, event: CampaignEvent) -> None:
    baru = apply_campaign(DomainCampaignStatus(campaign.status.value), event)
    campaign.status = CampaignStatus(baru.value)


def advance_milestone(milestone: ProposalMilestone, event: MilestoneEvent) -> None:
    baru = apply_milestone(DomainMilestoneStatus(milestone.status.value), event)
    milestone.status = MilestoneStatus(baru.value)


def advance_report(report: MilestoneReport, event: ReportEvent) -> None:
    baru = apply_report(DomainReportStatus(report.review_status.value), event)
    report.review_status = MilestoneReportStatus(baru.value)

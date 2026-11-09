"""Jembatan nilai antara enum transisi domain dan enum kolom database.

Nilai stringnya sama, kelasnya beda, dan menulis hasil apply_* langsung ke kolom
gagal tanpa bersuara: mypy menolaknya dan perbandingan `is` di test selalu salah.
Konversinya dipusatkan di sini supaya tests/unit/test_transition_guard.py bisa
menegakkannya, bukan supaya lebih singkat.
"""

from app.domain.transitions import (
    CampaignEvent,
    ProposalEvent,
    ScoringEvent,
    apply_campaign,
    apply_proposal,
    apply_scoring,
)
from app.domain.transitions import CampaignStatus as DomainCampaignStatus
from app.domain.transitions import ProposalStatus as DomainProposalStatus
from app.domain.transitions import ScoringStatus as DomainScoringStatus
from app.models.campaign import Campaign, CampaignStatus
from app.models.proposal import Proposal, ProposalStatus, ScoringStatus


def advance_proposal(proposal: Proposal, event: ProposalEvent) -> None:
    baru = apply_proposal(DomainProposalStatus(proposal.status.value), event)
    proposal.status = ProposalStatus(baru.value)


def advance_scoring(proposal: Proposal, event: ScoringEvent) -> None:
    baru = apply_scoring(DomainScoringStatus(proposal.scoring_status.value), event)
    proposal.scoring_status = ScoringStatus(baru.value)


def advance_campaign(campaign: Campaign, event: CampaignEvent) -> None:
    baru = apply_campaign(DomainCampaignStatus(campaign.status.value), event)
    campaign.status = CampaignStatus(baru.value)

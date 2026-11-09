"""Re-ekspor model agar terdaftar ke SQLModel.metadata saat package ini diimpor."""

from app.models.campaign import Campaign, CampaignStatus, Sector
from app.models.proposal import (
    MilestoneStatus,
    Proposal,
    ProposalMilestone,
    ProposalStatus,
    ScoringStatus,
)
from app.models.scoring import ScoringResult, ScoringVerdict
from app.models.user import Role, User

__all__ = [
    "Campaign",
    "CampaignStatus",
    "MilestoneStatus",
    "Proposal",
    "ProposalMilestone",
    "ProposalStatus",
    "Role",
    "ScoringResult",
    "ScoringStatus",
    "ScoringVerdict",
    "Sector",
    "User",
]

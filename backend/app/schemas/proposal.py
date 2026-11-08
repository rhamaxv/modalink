"""Skema response minimal untuk daftar proposal per campaign.

Kolom bisnis (judul, nominal diminta, hasil skoring) belum ada: itu cakupan
fase proposal, bukan fase campaign ini.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.proposal import ProposalStatus


class ProposalOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    campaign_id: UUID
    umkm_id: UUID
    status: ProposalStatus
    created_at: datetime


class ProposalListOut(BaseModel):
    items: list[ProposalOut]

"""Skema request/response untuk campaign (BR-64, BR-77)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.campaign import CampaignStatus, Sector


class CampaignIn(BaseModel):
    # Panjang sesuai form di 03-feature-investor.md.
    title: str = Field(min_length=5, max_length=120)
    description: str = Field(min_length=50)
    sector: Sector
    # strict=True: tanpa itu Pydantic membulatkan nominal pecahan diam-diam.
    target_amount: int = Field(strict=True, gt=0)
    apply_deadline: datetime
    funding_deadline: datetime
    score_threshold: int = Field(default=60, ge=0, le=100)


class CampaignUpdateIn(BaseModel):
    """Semua field opsional: PATCH hanya mengubah yang dikirim."""

    title: str | None = Field(default=None, min_length=5, max_length=120)
    description: str | None = Field(default=None, min_length=50)
    score_threshold: int | None = Field(default=None, ge=0, le=100)


class CampaignOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    investor_id: UUID
    title: str
    description: str
    sector: Sector
    target_amount: int
    apply_deadline: datetime
    funding_deadline: datetime
    score_threshold: int
    status: CampaignStatus
    created_at: datetime


class CampaignListOut(BaseModel):
    items: list[CampaignOut]

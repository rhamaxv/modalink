"""Skema response hasil scoring (BR-76, 10-api-contract.md)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.models.scoring import ScoringVerdict


class ScoringResultOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    proposal_id: UUID
    engine_name: str
    model_name: str
    fit_score: int
    data_quality_score: int
    impact_score: int
    total_score: int
    red_flags: list[dict[str, Any]]
    brief: dict[str, Any]
    threshold_used: int
    verdict: ScoringVerdict
    latency_ms: int
    created_at: datetime

"""Skema output penilaian AI (BR-70, BR-78, [11-ai-scoring-spec])."""

from typing import Literal

from pydantic import BaseModel, Field


class RedFlag(BaseModel):
    code: str
    severity: Literal["info", "warning", "critical"]
    message: str
    evidence: str  # kutipan persis dari isi proposal, bukan parafrase


class Brief(BaseModel):
    strengths: list[str] = Field(min_length=1, max_length=5)
    risks: list[str] = Field(min_length=1, max_length=5)
    recommendation: str


class ProposalScore(BaseModel):
    """Tidak ada field 'total' di sini, dan itu disengaja (BR-70).

    Model hanya menilai komponen. Total dan verdict diputuskan oleh kode.
    Field tambahan apa pun yang dikembalikan model akan diabaikan Pydantic.
    """

    fit_score: int = Field(ge=0, le=40)
    data_quality_score: int = Field(ge=0, le=30)
    impact_score: int = Field(ge=0, le=30)
    red_flags: list[RedFlag] = Field(default_factory=list, max_length=8)
    brief: Brief

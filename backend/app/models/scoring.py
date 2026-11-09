"""Model `scoring_results`: satu baris per percobaan scoring, append-only (BR-76).

Tidak ada endpoint PATCH atau PUT untuk tabel ini: baris lama tidak pernah
ditimpa, rescore selalu menambah baris baru, ditegakkan secara struktural
dengan tidak pernah menulis UPDATE, bukan dengan menolaknya di runtime.

ScoringVerdict didefinisikan ulang di sini, bukan diimpor dari
domain/verdict.py, dengan alasan yang sama seperti ProposalStatus di
models/proposal.py: ini tipe kolom database, bukan tipe yang dipakai mesin
keputusan verdict.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, Index, SmallInteger
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock


class ScoringVerdict(StrEnum):
    LISTED = "listed"
    REJECTED = "rejected"


class ScoringResult(SQLModel, table=True):
    __tablename__ = "scoring_results"
    __table_args__ = (
        CheckConstraint(
            "fit_score BETWEEN 0 AND 40", name="ck_scoring_results_fit_score"
        ),
        CheckConstraint(
            "data_quality_score BETWEEN 0 AND 30",
            name="ck_scoring_results_data_quality_score",
        ),
        CheckConstraint(
            "impact_score BETWEEN 0 AND 30", name="ck_scoring_results_impact_score"
        ),
        # Skor yang dipakai UI adalah baris terbaru per proposal (lihat
        # 09-data-model.md), jadi query-nya selalu proposal_id + created_at DESC.
        Index("ix_scoring_results_proposal_id_created_at", "proposal_id", "created_at"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Tanpa index=True: query pada proposal_id saja sudah terlayani oleh
    # kolom pertama index komposit (proposal_id, created_at) di atas, jadi
    # index tunggal di sini cuma duplikat yang menambah beban setiap write.
    proposal_id: UUID = Field(foreign_key="proposals.id")
    engine_name: str
    model_name: str
    fit_score: int = Field(sa_column=Column(SmallInteger, nullable=False))
    data_quality_score: int = Field(sa_column=Column(SmallInteger, nullable=False))
    impact_score: int = Field(sa_column=Column(SmallInteger, nullable=False))
    total_score: int = Field(sa_column=Column(SmallInteger, nullable=False))
    # JSONB, bukan TEXT berisi JSON: frontend membaca ulang lewat kunci
    # (code, severity, evidence), bukan menampilkan isinya mentah-mentah.
    red_flags: list[dict[str, Any]] = Field(sa_column=Column(JSONB, nullable=False))
    brief: dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    threshold_used: int = Field(sa_column=Column(SmallInteger, nullable=False))
    verdict: ScoringVerdict = Field(
        sa_column=Column(
            SAEnum(
                ScoringVerdict,
                name="scoring_verdict",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        )
    )
    latency_ms: int
    created_at: datetime = Field(default_factory=lambda: SystemClock().now())

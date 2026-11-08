"""Keputusan verdict AI: total dijumlahkan dan dibandingkan di kode, bukan di
model (BR-70, BR-71, BR-72, BR-73)."""

from enum import StrEnum

from app.ai.models import ProposalScore


class Verdict(StrEnum):
    LISTED = "listed"
    REJECTED = "rejected"


def total_score(score: ProposalScore) -> int:
    return score.fit_score + score.data_quality_score + score.impact_score


def decide_verdict(score: ProposalScore, threshold: int) -> Verdict:
    # Urutan penting: red flag kritis menolak tanpa memandang total (BR-72).
    if any(f.severity == "critical" for f in score.red_flags):
        return Verdict.REJECTED
    if total_score(score) < threshold:
        return Verdict.REJECTED
    return Verdict.LISTED

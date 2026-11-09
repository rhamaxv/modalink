"""Prasyarat pelaporan dan pencairan milestone (BR-40 sampai BR-43, D-13). Murni,
tanpa database."""

from app.domain.transitions import MilestoneStatus


def requires_report(seq: int) -> bool:
    """Milestone pertama cair tanpa laporan, tetap butuh approve lead investor
    (D-13). Milestone berikutnya wajib disertai laporan yang disetujui (BR-42)."""
    return seq > 1


def can_be_reported(seq: int, previous_status: MilestoneStatus | None) -> bool:
    if not requires_report(seq):
        return False
    return previous_status is MilestoneStatus.DISBURSED


def disbursement_precondition(
    seq: int, previous_status: MilestoneStatus | None, proposal_funded: bool
) -> None:
    if not proposal_funded:
        raise ValueError("Proposal belum funded, pencairan belum bisa dilakukan.")
    if seq > 1 and previous_status is not MilestoneStatus.DISBURSED:
        raise ValueError("Milestone sebelumnya belum cair.")

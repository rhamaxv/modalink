"""Peta transisi keempat mesin status, ditulis sebagai data (D-04).

Menambah status berarti menambah entri di sini DAN baris di regression test R1.
Suite akan merah sampai keduanya dilakukan. Itu disengaja.
"""
from enum import StrEnum


class ProposalStatus(StrEnum):
    SUBMITTED = "submitted"
    LISTED = "listed"
    PARTIALLY_FUNDED = "partially_funded"
    REJECTED = "rejected"
    FUNDED = "funded"
    FAILED = "failed"
    COMPLETED = "completed"


class ProposalEvent(StrEnum):
    SCORING_LULUS = "scoring_lulus"
    SCORING_GAGAL = "scoring_gagal"
    PLEDGE_SEBAGIAN = "pledge_sebagian"
    PLEDGE_PENUH = "pledge_penuh"
    PLEDGE_KOSONG = "pledge_kosong"
    DEADLINE_LEWAT = "deadline_lewat"
    SEMUA_MILESTONE_CAIR = "semua_milestone_cair"


class MilestoneStatus(StrEnum):
    PENDING = "pending"
    REPORTED = "reported"
    DISBURSED = "disbursed"


class MilestoneEvent(StrEnum):
    LAPOR = "lapor"
    APPROVE_TANPA_LAPORAN = "approve_tanpa_laporan"
    APPROVE = "approve"
    REJECT = "reject"


S, E = ProposalStatus, ProposalEvent
# Anotasi tipe memakai nama penuh karena mypy menolak S/E sebagai tipe
# (keduanya variabel biasa, bukan TypeAlias); isi peta tetap pakai alias
# pendek agar kolom T-xx di sebelah kanan tetap sejajar.
PROPOSAL_MAP: dict[tuple[ProposalStatus, ProposalEvent], ProposalStatus] = {
    (S.SUBMITTED, E.SCORING_LULUS):         S.LISTED,             # T-01
    (S.SUBMITTED, E.SCORING_GAGAL):         S.REJECTED,           # T-02
    (S.LISTED, E.PLEDGE_SEBAGIAN):          S.PARTIALLY_FUNDED,   # T-03
    (S.LISTED, E.PLEDGE_PENUH):             S.FUNDED,             # T-04
    (S.LISTED, E.DEADLINE_LEWAT):           S.FAILED,             # T-05
    (S.PARTIALLY_FUNDED, E.PLEDGE_PENUH):   S.FUNDED,             # T-06
    (S.PARTIALLY_FUNDED, E.PLEDGE_KOSONG):  S.LISTED,             # T-07
    (S.PARTIALLY_FUNDED, E.DEADLINE_LEWAT): S.FAILED,             # T-08
    (S.FUNDED, E.SEMUA_MILESTONE_CAIR):     S.COMPLETED,          # T-09
}

M, ME = MilestoneStatus, MilestoneEvent
MILESTONE_MAP: dict[tuple[MilestoneStatus, MilestoneEvent], MilestoneStatus] = {
    (M.PENDING, ME.LAPOR):                  M.REPORTED,    # T-20
    (M.PENDING, ME.APPROVE_TANPA_LAPORAN):  M.DISBURSED,   # T-21
    (M.REPORTED, ME.APPROVE):               M.DISBURSED,   # T-22
    (M.REPORTED, ME.REJECT):                M.PENDING,     # T-23
}


class IllegalTransition(Exception):
    """Dilempar untuk kombinasi status-event yang tidak ada di peta.

    Lapisan domain tidak tahu apa-apa soal HTTP, jadi exception ini bukan
    turunan dari apa pun di app/errors.py. Pemetaan ke 409 terjadi di lapisan
    service/router pada fase berikutnya.
    """

    def __init__(self, current: StrEnum, event: StrEnum) -> None:
        super().__init__(f"Transisi tidak sah: {current.value} tidak menerima {event.value}.")
        self.current = current
        self.event = event


def apply_proposal(current: ProposalStatus, event: ProposalEvent) -> ProposalStatus:
    try:
        return PROPOSAL_MAP[(current, event)]
    except KeyError:
        raise IllegalTransition(current, event) from None


def apply_milestone(current: MilestoneStatus, event: MilestoneEvent) -> MilestoneStatus:
    try:
        return MILESTONE_MAP[(current, event)]
    except KeyError:
        raise IllegalTransition(current, event) from None

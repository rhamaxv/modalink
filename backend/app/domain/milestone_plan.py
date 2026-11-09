"""Validasi rencana milestone (BR-14, BR-15, BR-16). Murni, tanpa database."""

from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.money import Rupiah, format_rupiah, parse_rupiah

MINIMAL_MILESTONE = 2
# T-3 (bounds audit): schema sudah membatasi panjang daftar milestone lewat
# Field(max_length=...), tapi pemanggil service lain (termasuk test dan
# kode yang menyusun Proposal langsung) bisa melewati Pydantic sama sekali.
# Diulang di sini, bukan hanya di schemas/proposal.py, dengan alasan yang
# sama dengan pengulangan MIN_PLEDGE_AMOUNT di services/pledge.py.
MAKSIMAL_MILESTONE = 30


@dataclass(frozen=True, slots=True)
class MilestoneDraft:
    seq: int
    title: str
    description: str
    amount: Rupiah


def validate_milestone_plan(
    milestones: Sequence[MilestoneDraft], requested: Rupiah
) -> None:
    if len(milestones) < MINIMAL_MILESTONE:
        raise ValueError("Rencana milestone harus berisi minimal dua tahap.")
    if len(milestones) > MAKSIMAL_MILESTONE:
        raise ValueError(f"Rencana milestone maksimal {MAKSIMAL_MILESTONE} tahap.")

    for m in milestones:
        parse_rupiah(m.amount)  # menolak nol, negatif, dan bentuk bukan integer

    urutan = [m.seq for m in milestones]
    if urutan != list(range(1, len(milestones) + 1)):
        raise ValueError(
            "Nomor urut milestone harus berurutan mulai dari 1, tanpa lompatan."
        )

    total = sum(m.amount for m in milestones)
    if total < requested:
        raise ValueError(
            f"Jumlah nominal milestone kurang {format_rupiah(requested - total)} "
            f"dari dana yang diminta."
        )
    if total > requested:
        raise ValueError(
            f"Jumlah nominal milestone lebih {format_rupiah(total - requested)} "
            f"dari dana yang diminta."
        )

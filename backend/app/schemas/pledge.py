"""Skema request/response untuk pledge dan pembatalannya (BR-20 sampai BR-28)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.money import MAX_RUPIAH
from app.models.pledge import PledgeStatus

# BR-27: pledge di bawah Rp100.000 ditolak. Konstanta khusus pledge, bukan
# ditaruh di domain/money.py: batas bawah ini tidak berlaku untuk nominal
# proposal atau milestone, jadi menaruhnya di modul uang generik akan
# menyesatkan pembaca yang mengira ini batas rupiah yang berlaku umum.
MIN_PLEDGE_AMOUNT = 100_000


class PledgeIn(BaseModel):
    # strict=True (RF-2): nilai di parametrize test_pledge_amount.py (string
    # non-integer, pecahan, di luar jangkauan BIGINT) sudah ditolak ge/le dan
    # parsing int bawaan Pydantic v2 tanpa strict. strict=True menutup kasus
    # yang parsing longgar justru meluluskan diam-diam: angka desimal bulat
    # seperti 2_000_000.0 dan string numerik seperti "5000000" (dibuktikan
    # manual, bukan ditebak dari dokumentasi). ge=MIN_PLEDGE_AMOUNT menegakkan
    # BR-27 di batas HTTP, bukan sesudahnya.
    amount: Annotated[int, Field(strict=True, ge=MIN_PLEDGE_AMOUNT, le=MAX_RUPIAH)]


class PledgeOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    proposal_id: UUID
    investor_id: UUID
    amount: int
    status: PledgeStatus
    created_at: datetime


class PledgeListItemOut(BaseModel):
    """GET /proposals/{id}/pledges (10-api-contract.md:67). Bukan subclass
    PledgeOut meski field-nya hampir sama: `investor_id` di sini opsional
    (None sebelum proposal `funded`), sementara PledgeOut dipakai apa
    adanya untuk respons POST/DELETE pledge sendiri, yang selalu tahu
    identitasnya sendiri dan tidak pernah butuh disembunyikan.

    10-api-contract.md:106-107 melarang identitas investor terlihat sebelum
    `funded`; review keamanan menemukan endpoint ini membiarkan investor
    manapun membaca UUID dan nominal pasti investor lain pada proposal yang
    masih `partially_funded` -- cukup untuk sengaja menyaingi pledge lead
    investor sebelum posisinya settle. `amount` dan `is_lead_investor` tetap
    tampil: keduanya informasi publik yang sah (bilah progres, penanda
    lead), bukan identitas. Redaksinya terjadi di
    `list_active_pledges` (services/pledge.py), bukan di sini lewat
    model_validator: fungsi itu sudah memegang `proposal.status` di tangan,
    jadi tidak perlu membawa status proposal ke skema ini hanya untuk
    keputusan yang sama."""

    model_config = {"from_attributes": True}

    id: UUID
    proposal_id: UUID
    investor_id: UUID | None
    amount: int
    status: PledgeStatus
    created_at: datetime
    is_lead_investor: bool


class PledgeListOut(BaseModel):
    items: list[PledgeListItemOut]

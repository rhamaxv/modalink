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


class PledgeListItemOut(PledgeOut):
    """GET /proposals/{id}/pledges (10-api-contract.md:67) menambah satu
    kolom di atas PledgeOut: penanda lead investor. Bukan kolom tabel, jadi
    tidak bisa divalidasi lewat from_attributes atas baris Pledge mentah;
    lihat PledgeAktifDenganLeadMarker di services/pledge.py yang merakitnya."""

    is_lead_investor: bool


class PledgeListOut(BaseModel):
    items: list[PledgeListItemOut]

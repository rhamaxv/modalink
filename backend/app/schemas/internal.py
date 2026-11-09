"""Skema request/response endpoint internal, hanya aktif saat ENV=dev (BR-63)."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class TickIn(BaseModel):
    # strict=True: "30" atau 30.0 tidak boleh diam-diam diterima sebagai 30
    # hari, sama seperti alasan strict=True di schemas/pledge.py.
    hari: Annotated[int, Field(strict=True, gt=0)]


class ClockOut(BaseModel):
    virtual_now: datetime


class SeedOut(BaseModel):
    """Ringkasan `POST /internal/seed`, dibangun dari `HasilSeed`
    (app/seed/demo.py) supaya test lokal bisa memeriksa idempotensinya lewat
    HTTP tanpa menghitung baris sendiri."""

    sudah_pernah_disemai: bool
    jumlah_user: int
    jumlah_campaign: int
    jumlah_proposal: int
    jumlah_pledge: int
    jumlah_ledger_entry: int

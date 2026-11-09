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

"""Jam virtual tersimpan di database, dipakai demo juri memajukan deadline
tanpa menunggu (D-06, BR-60, BR-63).

Satu baris saja per database: `CHECK id = 1` yang memaksanya, bukan sekadar
konvensi. `virtual_now = None` berarti belum ada offset -- `ambil_clock()`
jatuh balik ke `SystemClock()`.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint
from sqlmodel import Field, SQLModel


class SystemClockRow(SQLModel, table=True):
    __tablename__ = "system_clock"
    __table_args__ = (CheckConstraint("id = 1", name="ck_system_clock_tunggal"),)

    id: int = Field(default=1, primary_key=True)
    virtual_now: datetime | None = Field(default=None, nullable=True)

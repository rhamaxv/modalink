"""Satu-satunya sumber waktu di seluruh aplikasi (BR-60).

Memanggil datetime.now() di luar modul ini dilarang. Ada test yang memeriksanya.
"""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    def __init__(self, at: datetime) -> None:
        self._at = at

    def now(self) -> datetime:
        return self._at


class VirtualClock:
    """Jam dasar ditambah offset, dipakai endpoint tick untuk mendemokan deadline (D-06)."""

    def __init__(self, base: Clock, offset: timedelta) -> None:
        self._base = base
        self._offset = offset

    def now(self) -> datetime:
        return self._base.now() + self._offset

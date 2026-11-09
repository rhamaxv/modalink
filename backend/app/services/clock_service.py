"""Baca dan ubah jam virtual tersimpan (D-06, BR-60, BR-63).

`VirtualClock` yang dikembalikan `ambil_clock` dibangun dari offset
`virtual_now - SystemClock().now()` yang dihitung ulang setiap kali, bukan
dari `virtual_now` yang dibekukan secara statis. Efeknya: `.now()` pada
instance yang baru dikembalikan sama dengan `virtual_now` yang tersimpan
(sampai beberapa milidetik, selisih antara baris ini dan baris pemanggil),
dan `majukan_jam` berikutnya tetap menumpuk dari titik itu, bukan dari jam
asli -- itulah yang membuat tick bersifat akumulatif.
"""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clock import Clock, SystemClock, VirtualClock
from app.models.system_clock import SystemClockRow

_BARIS_TUNGGAL_ID = 1


async def ambil_clock(session: AsyncSession) -> Clock:
    baris = await session.get(SystemClockRow, _BARIS_TUNGGAL_ID)
    if baris is None or baris.virtual_now is None:
        return SystemClock()
    dasar = SystemClock()
    return VirtualClock(dasar, baris.virtual_now - dasar.now())


async def majukan_jam(session: AsyncSession, hari: int) -> None:
    sekarang = (await ambil_clock(session)).now()
    baris = await session.get(SystemClockRow, _BARIS_TUNGGAL_ID)
    if baris is None:
        baris = SystemClockRow(id=_BARIS_TUNGGAL_ID)
        session.add(baris)
    baris.virtual_now = sekarang + timedelta(days=hari)
    await session.flush()


async def reset_jam(session: AsyncSession) -> None:
    baris = await session.get(SystemClockRow, _BARIS_TUNGGAL_ID)
    if baris is not None:
        baris.virtual_now = None
        await session.flush()

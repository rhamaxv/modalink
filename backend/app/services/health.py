"""Orkestrasi untuk endpoint /health: memastikan koneksi database hidup."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def check_database(session: AsyncSession) -> None:
    await session.execute(text("SELECT 1"))

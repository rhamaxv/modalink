from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    # Tanpa commit di sini, setiap endpoint menulis ke sesi lalu sesi itu
    # ditutup begitu saja saat response selesai: Postgres tidak pernah
    # melihat perubahannya. Rollback pada exception supaya error di tengah
    # request tidak meninggalkan flush sebagian yang sempat terjadi.
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

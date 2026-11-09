"""Adapter JobRunner di atas BackgroundTasks milik FastAPI (D-01).

coro_factory yang diserahkan ke submit() wajib membuka session database-nya
sendiri (lewat session_factory, lihat app/api/deps.py), bukan memakai session
request, karena FastAPI menjalankan BackgroundTasks sebelum exit code
dependency `yield` (Depends(get_session), yang meng-commit session request)
berjalan -- urutan ini didokumentasikan resmi oleh FastAPI sendiri, bukan hal
yang kebetulan. Tanpa commit eksplisit di _jalankan di bawah, job yang
membuka session terpisah lewat session_factory membaca database sebelum
baris yang baru ditulis request ini benar-benar ter-commit, dan tidak
menemukan apa-apa (C-31: terbukti lewat test_persistence_commit.py yang
menjalankan jalur ini tanpa dependency_overrides).
"""

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.runner import CoroFactory


class InlineRunner:
    def __init__(
        self, background_tasks: BackgroundTasks, session: AsyncSession
    ) -> None:
        self._background_tasks = background_tasks
        self._session = session

    def submit(self, coro_factory: CoroFactory) -> None:
        # add_task(coro_factory) langsung tidak cukup: coro_factory adalah
        # lambda biasa yang mengembalikan coroutine, bukan coroutine function
        # itu sendiri, jadi Starlette menganggapnya sinkron dan menjalankannya
        # di threadpool tanpa pernah di-await, membuat coroutine di dalamnya
        # tidak pernah benar-benar berjalan.
        self._background_tasks.add_task(self._jalankan, coro_factory)

    async def _jalankan(self, coro_factory: CoroFactory) -> None:
        # Commit eksplisit, bukan menunggu Depends(get_session): lihat
        # docstring modul ini. expire_on_commit=False pada SessionLocal
        # (app/db/session.py) membuat ini aman dilakukan di sini -- objek
        # yang sudah diserialisasi ke response tidak ikut berubah.
        await self._session.commit()
        await coro_factory()

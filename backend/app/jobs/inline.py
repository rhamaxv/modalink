"""Adapter JobRunner di atas BackgroundTasks milik FastAPI (D-01).

coro_factory yang diserahkan ke submit() wajib membuka session database-nya
sendiri (lewat session_factory, lihat app/api/deps.py), bukan memakai session
request: FastAPI menjalankan exit code dependency `yield` (yang menutup
session request) sebelum BackgroundTasks benar-benar dieksekusi, jadi session
request sudah tertutup pada saat tugas ini berjalan.
"""

from fastapi import BackgroundTasks

from app.jobs.runner import CoroFactory


class InlineRunner:
    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self._background_tasks = background_tasks

    def submit(self, coro_factory: CoroFactory) -> None:
        # add_task(coro_factory) langsung tidak cukup: coro_factory adalah
        # lambda biasa yang MENGEMBALIKAN coroutine, bukan coroutine function
        # itu sendiri, jadi Starlette menganggapnya sinkron dan menjalankannya
        # di threadpool tanpa pernah di-await, membuat coroutine di dalamnya
        # tidak pernah benar-benar berjalan.
        self._background_tasks.add_task(self._jalankan, coro_factory)

    async def _jalankan(self, coro_factory: CoroFactory) -> None:
        await coro_factory()

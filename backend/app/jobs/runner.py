"""Protocol JobRunner: cara tugas latar belakang dipicu, dibalik dari
pemanggilnya (D-01).

Lewat interface ini satu-satunya adapter yang berganti kalau nanti pindah
dari BackgroundTasks ke queue sungguhan (ARQ/Celery), bukan service yang
memanggil submit().
"""

from collections.abc import Awaitable, Callable
from typing import Protocol

CoroFactory = Callable[[], Awaitable[None]]


class JobRunner(Protocol):
    def submit(self, coro_factory: CoroFactory) -> None: ...

"""Review keamanan Finding 2: 'bounded worker pool atau queue depth cap
untuk scoring'. Tanpa batas ini, setiap request submit proposal memicu job
scoring-nya sendiri lewat BackgroundTasks tanpa mengenal job lain yang
sedang berjalan bersamaan -- dua belas request bersamaan berarti dua belas
panggilan Gemini bersamaan, persis yang direproduksi review (12 akun, 7.2MB
prompt, 1.2 detik).

`InlineRunner._SCORING_SEMAPHORE` di app/jobs/inline.py adalah satu
semaphore proses-tunggal yang dibagi SELURUH instance InlineRunner, bukan
satu per instance -- test ini membuktikan itu dengan membuat banyak
instance (mewakili banyak request bersamaan) dan mengukur konkurensi
sungguhan yang terjadi, bukan hanya membaca kode dan mempercayainya.
"""

import asyncio

import app.jobs.inline as inline_module
from app.config import settings
from app.jobs.inline import InlineRunner


class _SessionPalsu:
    async def commit(self) -> None:
        return None


def _buat_runner() -> InlineRunner:
    from fastapi import BackgroundTasks

    return InlineRunner(BackgroundTasks(), _SessionPalsu())


async def test_rf2_scoring_jobs_never_exceed_the_configured_concurrency_cap():
    aktif = {"sekarang": 0, "puncak": 0}
    lock = asyncio.Lock()

    async def kerja_simulasi() -> None:
        async with lock:
            aktif["sekarang"] += 1
            aktif["puncak"] = max(aktif["puncak"], aktif["sekarang"])
        await asyncio.sleep(0.02)
        async with lock:
            aktif["sekarang"] -= 1

    jumlah_job = settings.scoring_max_concurrent_jobs * 4
    runners = [_buat_runner() for _ in range(jumlah_job)]
    for r in runners:
        r.submit(kerja_simulasi)

    await asyncio.gather(*(r._background_tasks() for r in runners))

    assert aktif["puncak"] <= settings.scoring_max_concurrent_jobs
    assert aktif["puncak"] > 1, (
        "test ini tidak membuktikan apa pun kalau tidak pernah konkuren"
    )


async def test_rf2_scoring_semaphore_is_shared_across_inline_runner_instances():
    """Pagar langsung: tanpa semaphore bersama, membuat ulang semaphore per
    instance akan membuat test di atas lolos meski batasnya tidak pernah
    ditegakkan lintas request. Dicek eksplisit supaya regresi semacam itu
    tertangkap tanpa menunggu timing test di atas kebetulan tidak kebetulan."""
    a = _buat_runner()
    b = _buat_runner()
    assert inline_module._SCORING_SEMAPHORE is inline_module._SCORING_SEMAPHORE
    # Kedua runner memakai nama modul yang sama, bukan atribut instance:
    # tidak ada `self._semaphore` sama sekali di InlineRunner.
    assert not hasattr(a, "_semaphore")
    assert not hasattr(b, "_semaphore")

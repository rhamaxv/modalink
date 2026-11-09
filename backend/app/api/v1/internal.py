"""Endpoint internal untuk demo dan verifikasi juri (BR-63, D-06).

Seluruh router ini hanya didaftarkan bila `ENV=dev` (lihat app/main.py), jadi
di produksi setiap endpoint di bawahnya mengembalikan 404 murni dari routing,
bukan dari pemeriksaan di dalam handler yang bisa lupa dipasang.

Tidak ada pagar peran atau kepemilikan di sini, dan itu keputusan sadar, bukan
kelalaian. Kontrak menempatkan endpoint-endpoint ini di bawah header "Internal"
tanpa kolom peran sama sekali, beda dari setiap endpoint lain di
10-api-contract.md. Dan yang lebih menentukan: `POST /auth/register` publik dan
gratis, jadi mewajibkan token di sini tidak menutup akses sungguhan, siapa pun
bisa mendaftar lalu memakai tokennya. Satu-satunya pagar yang benar-benar
menutup sesuatu adalah apakah router ini terdaftar, dan itu dikendalikan ENV.

Konsekuensinya harus dibaca terang-terangan: endpoint ini **terbuka** bagi
siapa pun yang bisa menjangkau deployment dengan `ENV=dev`. Karena itu
`docker-compose.prod.yml` menyetel `ENV: prod`, dan demo yang dilihat juri
berjalan tanpa endpoint ini. Kalau suatu saat demo perlu memajukan jam di depan
juri, keputusan itu harus diambil ulang secara eksplisit, bukan dengan
menyalakan ENV=dev di server publik.
"""

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.errors import NotFoundError
from app.schemas.internal import ClockOut, SeedOut, TickIn
from app.schemas.ledger import LedgerOut
from app.seed.demo import seed_demo_data
from app.services.clock_service import ambil_clock, majukan_jam
from app.services.ledger import ambil_ledger_proposal
from app.services.proposal import ambil_proposal

# Tanpa prefix, dengan path penuh di tiap dekorator: dua kelompok endpoint di
# bawah ini tidak berbagi awalan yang sama (/internal/clock/... dan
# /internal/ledger/...), jadi prefix router hanya akan memindahkan separuhnya.
router = APIRouter(tags=["internal"])


@router.post("/api/v1/internal/clock/tick", response_model=ClockOut)
async def tick_endpoint(
    body: TickIn,
    session: AsyncSession = Depends(get_session),
) -> ClockOut:
    await majukan_jam(session, body.advance_days)
    clock = await ambil_clock(session)
    return ClockOut(virtual_now=clock.now())


@router.post("/api/v1/internal/seed", response_model=SeedOut)
async def seed_endpoint(session: AsyncSession = Depends(get_session)) -> SeedOut:
    """Dipakai test lokal dan demo tanpa server produksi (10-api-contract.md:97).

    Logikanya sendiri hidup di app/seed/demo.py, dipakai juga oleh
    `python -m app.seed` untuk server produksi (lihat peringatan di
    `.claude/plan/phase-13-submission.md` soal kenapa endpoint ini tidak
    bisa dipakai di sana: ENV=prod tidak pernah mendaftarkannya).
    """
    hasil = await seed_demo_data(session)
    return SeedOut(**asdict(hasil))


@router.get("/api/v1/internal/ledger/{proposal_id}", response_model=LedgerOut)
async def ambil_ledger_endpoint(
    proposal_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> LedgerOut:
    proposal = await ambil_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    entries, balance = await ambil_ledger_proposal(session, proposal_id)
    return LedgerOut(entries=entries, balance=balance)

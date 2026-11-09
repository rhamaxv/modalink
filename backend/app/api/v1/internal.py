"""Endpoint internal untuk demo dan verifikasi juri (BR-63).

Seluruh router ini hanya didaftarkan bila ENV bukan "prod" (lihat
app/main.py); itu sendiri sudah dibangun sebelum berkas ini ada, untuk
POST /internal/clock/tick dan POST /internal/seed. GET /internal/ledger/{id}
di sini mengikuti pagar yang sama, bukan membuat pagar baru.

Keputusan akses (brief Fase 07 Task 6): tidak ada pemeriksaan peran atau
kepemilikan di endpoint ini. Dua alasan. Pertama, kontrak menyebut endpoint
ini di bawah header "Internal" tanpa kolom "Peran" sama sekali, beda dari
setiap endpoint lain di 10-api-contract.md -- berbeda dari kelalaian
(seperti empat endpoint yang jadi alasan task ini), ini konsisten dengan
seluruh endpoint lain di bawah header yang sama (clock/tick, clock/reset,
seed) yang juga tidak diberi peran. Kedua, dan lebih penting: POST
/auth/register bersifat publik dan gratis, jadi mewajibkan token di sini
tidak menutup akses sungguhan -- siapa pun bisa mendaftar lewat peran
apa pun dalam satu permintaan lalu memakai tokennya di sini. Satu-satunya
pagar yang pernah menutup sesuatu adalah apakah router ini terdaftar sama
sekali, dan itu dikendalikan oleh ENV, bukan oleh kredensial yang di-hardcode.

Ini membuat endpoint ini TERBUKA bagi siapa pun yang bisa menjangkau
deployment yang berjalan dengan ENV != "prod" (termasuk demo yang dilihat
juri, yang sengaja memakai ENV=dev supaya /internal/clock dan /internal/seed
ikut berfungsi untuk demo). Dicatat terang-terangan di laporan task ini
supaya controller fase ini bisa menolak keputusan ini bila dianggap tidak
cukup aman untuk deployment demo yang sungguhan.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.errors import NotFoundError
from app.schemas.ledger import LedgerOut
from app.services.ledger import ambil_ledger_proposal
from app.services.proposal import ambil_proposal

router = APIRouter(tags=["internal"])


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

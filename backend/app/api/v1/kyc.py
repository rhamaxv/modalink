"""Endpoint verifikasi identitas dan rekening tujuan pencairan.

Verifikasinya simulasi; lihat app/models/kyc.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, get_clock, require_role
from app.db.session import get_session
from app.domain.clock import Clock
from app.errors import NotFoundError
from app.models.kyc import KycSubmission
from app.models.user import Role, User
from app.schemas.kyc import KycIn, KycOut
from app.services.kyc import get_kyc, submit_kyc

router = APIRouter(tags=["kyc"])


@router.post("/api/v1/kyc", response_model=KycOut)
async def submit_kyc_endpoint(
    body: KycIn,
    # Peran komunitas tidak diminta verifikasi: ia tidak pernah menyentuh
    # uang, dan meminta NIK dari orang yang hanya ingin berkomentar adalah
    # mengumpulkan data pribadi tanpa alasan.
    user: User = Depends(require_role(Role.INVESTOR, Role.UMKM)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> KycSubmission:
    return await submit_kyc(session, user, body, clock)


@router.get("/api/v1/kyc/me", response_model=KycOut)
async def get_my_kyc_endpoint(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
) -> KycSubmission:
    pengajuan = await get_kyc(session, user.id)
    if pengajuan is None:
        raise NotFoundError(
            "kyc_belum_diajukan", "Anda belum pernah mengajukan verifikasi identitas."
        )
    return pengajuan

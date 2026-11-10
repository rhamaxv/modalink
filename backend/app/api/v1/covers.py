"""Foto sampul proposal dan campaign: unggah, baca, hapus.

Gambar dilayani dari endpoint ini, bukan dari berkas statis, karena bytenya
disimpan di database. Alasan penyimpanannya ada di app/models/cover.py.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, optional_user, require_role
from app.db.session import get_session
from app.domain.clock import Clock
from app.errors import ForbiddenError, NotFoundError, UnprocessableError
from app.models.cover import CoverImage
from app.models.user import Role, User
from app.services.campaign import get_campaign
from app.services.cover import (
    MAX_COVER_BYTES,
    ambil_cover,
    hapus_cover,
    simpan_cover,
)
from app.services.proposal import can_view, get_proposal

router = APIRouter(tags=["covers"])

# Dibaca sepotong-sepotong, bukan sekaligus lewat `await berkas.read()`.
# Membaca sekaligus berarti unggahan 500 MB tetap ditulis penuh ke berkas
# sementara lebih dulu, lalu baru ditolak -- penolakan yang sudah terlambat
# menghabiskan disk dan waktu server. Dengan potongan, pembacaan berhenti
# tepat setelah melewati batas.
UKURAN_POTONGAN = 64 * 1024


async def _baca_terbatas(berkas: UploadFile) -> bytes:
    potongan: list[bytes] = []
    terkumpul = 0
    while True:
        bagian = await berkas.read(UKURAN_POTONGAN)
        if not bagian:
            break
        terkumpul += len(bagian)
        if terkumpul > MAX_COVER_BYTES:
            raise UnprocessableError(
                "berkas_terlalu_besar",
                f"Ukuran foto maksimal {MAX_COVER_BYTES // 1024 // 1024} MB.",
            )
        potongan.append(bagian)
    return b"".join(potongan)


def _respons_gambar(cover: CoverImage) -> Response:
    return Response(
        content=cover.data,
        media_type=cover.content_type,
        headers={
            # Tipe hasil pemeriksaan byte, dan nosniff memastikan browser
            # tidak menebak tipe lain dari isinya sendiri. Keduanya bersama
            # yang menutup jalur "berkas diunggah sebagai gambar, dieksekusi
            # sebagai sesuatu yang lain".
            "X-Content-Type-Options": "nosniff",
            # inline, bukan attachment: ini memang gambar untuk ditampilkan.
            # Nama berkas sengaja tidak diteruskan dari unggahan.
            "Content-Disposition": "inline",
            # URL gambar sudah membawa kunci versi (?v=<epoch updated_at>),
            # jadi isinya aman di-cache lama: URL-nya ikut berubah begitu
            # sampulnya diganti.
            "Cache-Control": "public, max-age=604800, immutable",
        },
    )


# ---------------------------------------------------------------- proposal


async def _proposal_milik_umkm(
    proposal_id: UUID,
    user: User = Depends(require_role(Role.UMKM)),
    session: AsyncSession = Depends(get_session),
):
    proposal = await get_proposal(session, proposal_id)
    # 404, bukan 403: UMKM lain tidak boleh sekalian mengonfirmasi bahwa
    # proposal ini ada, pola yang sama dengan get_own_proposal_for_rescore.
    if proposal is None or proposal.umkm_id != user.id:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return proposal


@router.put(
    "/api/v1/proposals/{proposal_id}/cover",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def upload_proposal_cover_endpoint(
    berkas: UploadFile = File(..., alias="file"),
    proposal=Depends(_proposal_milik_umkm),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> None:
    """PUT, bukan POST: satu proposal punya paling banyak satu sampul, dan
    mengunggah ulang menimpa yang lama. Mengirim permintaan yang sama dua kali
    menghasilkan keadaan yang sama persis."""
    await simpan_cover(
        session, await _baca_terbatas(berkas), clock, proposal_id=proposal.id
    )


@router.delete(
    "/api/v1/proposals/{proposal_id}/cover",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_proposal_cover_endpoint(
    proposal=Depends(_proposal_milik_umkm),
    session: AsyncSession = Depends(get_session),
) -> None:
    await hapus_cover(session, proposal_id=proposal.id)


@router.get("/api/v1/proposals/{proposal_id}/cover")
async def get_proposal_cover_endpoint(
    proposal_id: UUID,
    user: User | None = Depends(optional_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """Mengikuti aturan keterlihatan proposalnya sendiri, bukan publik tanpa
    syarat: proposal yang masih `submitted` hanya boleh dilihat pemiliknya dan
    pemilik campaign, dan sampul yang tetap terbuka akan membocorkan bahwa
    proposal itu ada."""
    proposal = await get_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("sampul_tidak_ada", "Foto sampul tidak ditemukan.")
    campaign = await get_campaign(session, proposal.campaign_id)
    if campaign is None or not can_view(proposal, campaign, user):
        raise NotFoundError("sampul_tidak_ada", "Foto sampul tidak ditemukan.")
    cover = await ambil_cover(session, proposal_id=proposal_id)
    if cover is None:
        raise NotFoundError("sampul_tidak_ada", "Foto sampul tidak ditemukan.")
    return _respons_gambar(cover)


# ---------------------------------------------------------------- campaign


async def _campaign_milik_investor(
    campaign_id: UUID,
    user: User = Depends(require_role(Role.INVESTOR)),
    session: AsyncSession = Depends(get_session),
):
    campaign = await get_campaign(session, campaign_id)
    if campaign is None:
        raise NotFoundError("campaign_tidak_ada", "Campaign tidak ditemukan.")
    # 403, bukan 404, dan bedanya disengaja: daftar campaign memang publik
    # (10-api-contract.md:44), jadi keberadaannya bukan rahasia dan
    # menyamarkannya sebagai 404 justru menyesatkan pemiliknya sendiri.
    if campaign.investor_id != user.id:
        raise ForbiddenError(
            "bukan_pemilik_campaign", "Hanya pemilik campaign yang bisa mengubahnya."
        )
    return campaign


@router.put(
    "/api/v1/campaigns/{campaign_id}/cover",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def upload_campaign_cover_endpoint(
    berkas: UploadFile = File(..., alias="file"),
    campaign=Depends(_campaign_milik_investor),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> None:
    await simpan_cover(
        session, await _baca_terbatas(berkas), clock, campaign_id=campaign.id
    )


@router.delete(
    "/api/v1/campaigns/{campaign_id}/cover",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_campaign_cover_endpoint(
    campaign=Depends(_campaign_milik_investor),
    session: AsyncSession = Depends(get_session),
) -> None:
    await hapus_cover(session, campaign_id=campaign.id)


@router.get("/api/v1/campaigns/{campaign_id}/cover")
async def get_campaign_cover_endpoint(
    campaign_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    cover = await ambil_cover(session, campaign_id=campaign_id)
    if cover is None:
        raise NotFoundError("sampul_tidak_ada", "Foto sampul tidak ditemukan.")
    return _respons_gambar(cover)

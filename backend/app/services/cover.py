"""Unggah, baca, dan hapus foto sampul proposal atau campaign.

Aturan keamanan yang memandu seluruh berkas ini: **tipe berkas ditentukan dari
bytenya, bukan dari yang diakui pengunggah.** Header Content-Type pada bagian
multipart dipilih sepenuhnya oleh klien, jadi ia bukan pernyataan tentang isi
berkas, melainkan permintaan tentang cara isi itu nanti diperlakukan. Gambar
yang dilayani kembali dari origin yang sama dengan aplikasi, dengan tipe yang
ditentukan penyerang, adalah jalur XSS yang klasik.

SVG sengaja TIDAK termasuk format yang diterima meski ia gambar: berkas SVG
bisa memuat <script>, dan menyajikannya dari origin aplikasi berarti skrip itu
berjalan dengan hak yang sama dengan halaman produk ini.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.domain.clock import Clock
from app.errors import UnprocessableError
from app.models.cover import CoverImage

# 1,5 MB. Cukup untuk foto sampul yang tajam di lebar 1200px setelah dikompres
# browser, dan cukup kecil untuk tidak membuat tabel ini membengkak. Angka yang
# sama ditegakkan ulang oleh CHECK di database (lihat migrasi 8a4fb669b455).
MAX_COVER_BYTES = 1_572_864

# Dibaca sebanyak ini dulu untuk mengenali formatnya. 12 bait cukup untuk
# ketiga format: WebP baru bisa dipastikan di bait ke-8 sampai 11.
PANJANG_SIDIK = 12


def _kenali_tipe(data: bytes) -> str | None:
    """Tipe gambar dari sidik byte, atau None kalau bukan format yang diterima."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def simpan_cover(
    session: AsyncSession,
    data: bytes,
    clock: Clock,
    *,
    proposal_id: UUID | None = None,
    campaign_id: UUID | None = None,
) -> CoverImage:
    """Menyimpan atau MENIMPA sampul milik satu proposal atau satu campaign.

    Menimpa, bukan menumpuk: satu pemilik punya paling banyak satu sampul
    (unique constraint di models/cover.py), dan mengunggah ulang berarti
    mengganti yang lama, bukan meninggalkan dua baris yang salah satunya tidak
    pernah terbaca lagi.
    """
    if (proposal_id is None) == (campaign_id is None):
        # Bukan kesalahan pengguna, melainkan kesalahan pemanggil di dalam
        # kode ini sendiri, jadi ia bukan UnprocessableError.
        raise ValueError("Sampul harus milik tepat satu proposal atau satu campaign.")

    if not data:
        raise UnprocessableError("berkas_kosong", "Berkas yang diunggah kosong.")
    if len(data) > MAX_COVER_BYTES:
        raise UnprocessableError(
            "berkas_terlalu_besar",
            f"Ukuran foto maksimal {MAX_COVER_BYTES // 1024 // 1024} MB.",
        )

    tipe = _kenali_tipe(data[:PANJANG_SIDIK])
    if tipe is None:
        raise UnprocessableError(
            "format_tidak_didukung",
            "Foto harus berformat JPG, PNG, atau WebP.",
        )

    syarat = (
        CoverImage.proposal_id == proposal_id
        if proposal_id is not None
        else CoverImage.campaign_id == campaign_id
    )
    ada = await session.scalar(select(CoverImage).where(syarat))
    sekarang = clock.now()
    if ada is not None:
        ada.content_type = tipe
        ada.byte_size = len(data)
        ada.data = data
        ada.updated_at = sekarang
        session.add(ada)
        await session.flush()
        return ada

    baru = CoverImage(
        proposal_id=proposal_id,
        campaign_id=campaign_id,
        content_type=tipe,
        byte_size=len(data),
        data=data,
        updated_at=sekarang,
    )
    session.add(baru)
    await session.flush()
    return baru


async def ambil_cover(
    session: AsyncSession,
    *,
    proposal_id: UUID | None = None,
    campaign_id: UUID | None = None,
) -> CoverImage | None:
    syarat = (
        CoverImage.proposal_id == proposal_id
        if proposal_id is not None
        else CoverImage.campaign_id == campaign_id
    )
    return await session.scalar(select(CoverImage).where(syarat))


async def hapus_cover(
    session: AsyncSession,
    *,
    proposal_id: UUID | None = None,
    campaign_id: UUID | None = None,
) -> bool:
    ada = await ambil_cover(session, proposal_id=proposal_id, campaign_id=campaign_id)
    if ada is None:
        return False
    await session.delete(ada)
    await session.flush()
    return True


async def cover_versions(
    session: AsyncSession,
    *,
    proposal_ids: list[UUID] | None = None,
    campaign_ids: list[UUID] | None = None,
) -> dict[UUID, datetime]:
    """Waktu pembaruan sampul untuk sekumpulan pemilik, dalam SATU query.

    Dipanggil sekali per halaman daftar, bukan sekali per baris: menanyakan
    "punya sampul tidak" per proposal adalah pola N+1 yang sama yang pernah
    membuat GET /proposals mengirim 7,2 MB. Bytenya sendiri tidak ikut
    terbawa, hanya kolom waktunya.
    """
    if proposal_ids is not None:
        if not proposal_ids:
            return {}
        kueri = select(CoverImage.proposal_id, CoverImage.updated_at).where(
            col(CoverImage.proposal_id).in_(proposal_ids)
        )
    else:
        if not campaign_ids:
            return {}
        kueri = select(CoverImage.campaign_id, CoverImage.updated_at).where(
            col(CoverImage.campaign_id).in_(campaign_ids)
        )
    baris = (await session.execute(kueri)).all()
    return {pemilik: waktu for pemilik, waktu in baris if pemilik is not None}


def cover_updated_at_subquery(kolom: str):
    """Subquery `updated_at` sampul untuk di-JOIN ke daftar proposal/campaign.

    Dipakai supaya endpoint daftar tahu baris mana yang punya sampul TANPA
    satu query tambahan per baris: pola N+1 yang sama yang sudah pernah
    membuat GET /proposals mengirim 7,2 MB. Yang ikut terbawa hanya kolom
    waktunya, bukan bytenya.
    """
    return (
        select(
            col(getattr(CoverImage, kolom)).label("owner_id"),
            col(CoverImage.updated_at).label("cover_updated_at"),
        )
        .where(col(getattr(CoverImage, kolom)).is_not(None))
        .subquery()
    )


def versi_cache(updated_at: datetime | None) -> str | None:
    """Kunci cache untuk URL gambar.

    Tanpa ini, mengganti sampul tidak mengubah URL-nya sama sekali, dan
    browser maupun CDN akan terus menyajikan gambar lama sampai cachenya
    kedaluwarsa sendiri.
    """
    return None if updated_at is None else str(int(updated_at.timestamp()))

"""Orkestrasi verifikasi identitas dan rekening tujuan pencairan.

Verifikasinya SIMULASI. Lihat app/models/kyc.py untuk batasannya; modul ini
hanya menjalankan pemeriksaan bentuk di app/domain/identity.py lalu mencatat
hasilnya.
"""

import hashlib
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.domain.clock import Clock
from app.domain.identity import (
    IdentityError,
    empat_terakhir,
    periksa_nik,
    periksa_rekening,
)
from app.errors import ConflictError, ForbiddenError, UnprocessableError
from app.models.kyc import KycStatus, KycSubmission
from app.models.user import User
from app.schemas.kyc import KycIn


def _sidik_nik(nik: str) -> str:
    """sha256(NIK + pepper rahasia server).

    Pepper-nya `jwt_secret`, bukan konstanta yang ikut di repositori: tanpa
    itu, siapa pun yang memegang salinan database bisa menghitung ulang hash
    dari daftar NIK yang ia karang sendiri dan mencocokkannya satu per satu.
    Ruang NIK terlalu kecil (16 digit berpola) untuk tahan serangan semacam
    itu tanpa rahasia yang tidak ikut bocor bersama datanya.

    Bukan argon2 seperti password: nilai ini dibandingkan dalam query
    (mencari NIK yang sudah dipakai akun lain), jadi ia harus deterministik
    dan bisa diindeks. Password tidak pernah dicari begitu.
    """
    return hashlib.sha256(f"{nik}{settings.jwt_secret}".encode()).hexdigest()


async def get_kyc(session: AsyncSession, user_id: UUID) -> KycSubmission | None:
    return await session.scalar(
        select(KycSubmission).where(KycSubmission.user_id == user_id)
    )


async def is_verified(session: AsyncSession, user_id: UUID) -> bool:
    pengajuan = await get_kyc(session, user_id)
    return pengajuan is not None and pengajuan.status is KycStatus.VERIFIED


async def require_verified(session: AsyncSession, user: User, aksi: str) -> None:
    """Gerbang yang dipanggil sebelum tindakan yang menyentuh uang.

    403 dengan kalimat yang menyebut APA yang harus dilakukan, bukan sekadar
    menolak: pengguna yang ditolak tanpa diberi jalan keluar akan mengira
    produknya rusak.
    """
    if not await is_verified(session, user.id):
        raise ForbiddenError(
            "belum_terverifikasi",
            f"Verifikasi identitas dulu sebelum {aksi}. "
            "Buka halaman Verifikasi identitas di akun Anda.",
        )


async def submit_kyc(
    session: AsyncSession, user: User, body: KycIn, clock: Clock
) -> KycSubmission:
    """Mengajukan atau MENGGANTI verifikasi milik satu akun.

    Mengganti, bukan menumpuk: satu akun punya paling banyak satu pengajuan
    (unique constraint di models/kyc.py). Orang yang salah mengetik nomor
    rekening harus bisa memperbaikinya, dan riwayat pengajuan identitas bukan
    sesuatu yang berguna disimpan produk ini.
    """
    try:
        nik = periksa_nik(body.nik, hari_ini=clock.now().date())
        rekening = periksa_rekening(body.account_number)
    except IdentityError as exc:
        # 422, bukan 400: bentuknya yang tidak bisa diproses, dan pesannya
        # datang dari domain supaya ia menyebut aturan mana yang dilanggar.
        raise UnprocessableError("identitas_tidak_sah", str(exc)) from None

    sidik = _sidik_nik(nik)
    pemakai_lain = await session.scalar(
        select(KycSubmission).where(
            KycSubmission.nik_hash == sidik,
            KycSubmission.user_id != user.id,
        )
    )
    if pemakai_lain is not None:
        # 409: satu NIK satu akun. Tanpa ini, satu orang bisa membuat akun
        # sebanyak yang ia mau dan gerbang verifikasi tidak menahan apa pun.
        # Pesannya sengaja tidak menyebut akun mana yang memakainya.
        raise ConflictError(
            "nik_sudah_dipakai",
            "NIK ini sudah dipakai akun lain. Satu NIK hanya untuk satu akun.",
        )

    ada = await get_kyc(session, user.id)
    # Nilai awal lengkap untuk baris baru; seluruhnya ditimpa tepat di bawah.
    # SQLModel menuntut setiap kolom non-null disebut di konstruktor, dan
    # membiarkannya kosong hanya memindahkan kegagalan ke runtime.
    pengajuan = (
        ada
        if ada is not None
        else KycSubmission(
            user_id=user.id,
            full_name="",
            nik_hash="",
            nik_last4="",
            bank_code=body.bank_code,
            account_holder_name="",
            account_last4="",
            status=KycStatus.VERIFIED,
        )
    )

    # Ditulis satu per satu, bukan lewat dict yang di-splat: splat membuat
    # mypy kehilangan tipe tiap kolom dan satu kolom yang salah tipe lolos
    # sampai runtime.
    pengajuan.full_name = body.full_name
    pengajuan.nik_hash = sidik
    pengajuan.nik_last4 = empat_terakhir(nik)
    pengajuan.bank_code = body.bank_code
    pengajuan.account_holder_name = body.account_holder_name
    pengajuan.account_last4 = empat_terakhir(rekening)
    # Lolos seluruh pemeriksaan bentuk berarti verified. Tidak ada keadaan
    # menunggu: tidak ada verifikator manusia maupun pihak ketiga yang bisa
    # ditunggu di produk ini.
    pengajuan.status = KycStatus.VERIFIED
    pengajuan.rejection_reason = None
    pengajuan.submitted_at = clock.now()

    session.add(pengajuan)
    await session.flush()
    return pengajuan

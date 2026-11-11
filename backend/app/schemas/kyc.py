"""Skema request/response verifikasi identitas."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.models.kyc import BankCode, KycStatus

# strip_whitespace: nama yang disalin dari dokumen sering membawa spasi di
# ujungnya, dan menolaknya karena itu memindahkan beban ke pengguna untuk
# kesalahan yang bukan kesalahan.
NamaIdentitas = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=120)
]


class KycIn(BaseModel):
    full_name: NamaIdentitas
    # Diterima apa adanya lalu dinormalkan di domain/identity.py: pengguna
    # mengetik NIK dengan spasi atau tanda hubung lebih sering daripada
    # tidak. Batas panjangnya longgar di sini supaya pesan galat yang sampai
    # ke layar datang dari aturan NIK yang menjelaskan apa yang salah, bukan
    # dari batas bentuk payload yang generik.
    nik: Annotated[str, StringConstraints(min_length=1, max_length=32)]
    bank_code: BankCode
    account_holder_name: NamaIdentitas
    account_number: Annotated[str, StringConstraints(min_length=1, max_length=32)]


class KycOut(BaseModel):
    """Yang dikirim balik TIDAK pernah memuat NIK atau nomor rekening utuh.

    Keduanya tidak disimpan utuh sejak awal (lihat app/models/kyc.py), jadi
    bentuk ini bukan penyamaran di lapisan tampilan yang bisa dilangkahi:
    datanya memang tidak ada untuk dikirim.
    """

    model_config = {"from_attributes": True}

    status: KycStatus
    full_name: str
    nik_last4: str
    bank_code: BankCode
    account_holder_name: str
    account_last4: str
    rejection_reason: str | None
    submitted_at: datetime
    # Selalu True di produk ini, dan dikirim sebagai field, bukan hanya
    # ditulis di dokumen: antarmuka wajib menyebutnya di layar, dan field
    # yang harus dibaca lebih sulit diabaikan daripada paragraf di README.
    verifikasi_simulasi: bool = True


class KycStatusOut(BaseModel):
    """Dipakai layar yang hanya perlu tahu boleh atau tidak, bukan isinya."""

    sudah_terverifikasi: bool
    status: KycStatus | None = Field(
        default=None, description="None berarti belum pernah mengajukan."
    )

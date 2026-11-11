"""Verifikasi identitas dan rekening tujuan pencairan.

**Verifikasinya simulasi, dan itu disebut terus terang di setiap lapisan.**
Tidak ada pemeriksaan ke Dukcapil, tidak ada pencocokan wajah, dan tidak ada
konfirmasi ke bank mana pun. Yang diperiksa hanyalah BENTUK data: panjang dan
pola NIK, nama bank yang dikenal, dan panjang nomor rekening. Produk ini tidak
layak memegang uang sungguhan, dan modul ini tidak mengubah itu; ia
memperlihatkan di mana pemeriksaan sungguhan akan dipasang.

Dua keputusan penyimpanan yang disengaja, dan keduanya tentang data pribadi:

1. **NIK tidak pernah disimpan utuh.** Yang disimpan adalah sidik hash-nya
   (untuk mendeteksi satu NIK dipakai dua akun) dan empat digit terakhir
   (untuk ditampilkan kembali ke pemiliknya). Database yang bocor karena itu
   tidak membocorkan nomor identitas siapa pun.
2. **Nomor rekening juga tidak disimpan utuh**, dengan alasan yang sama. Tidak
   ada uang sungguhan yang dikirim ke mana pun, jadi nomor penuhnya memang
   tidak dibutuhkan sistem ini untuk berfungsi.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, Enum, ForeignKey, Uuid
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock


class KycStatus(StrEnum):
    # Tidak ada "pending" yang menggantung: pemeriksaan bentuk selesai
    # seketika, jadi satu pengajuan langsung berakhir di salah satu dari dua
    # keadaan ini. Keadaan menunggu baru masuk akal kalau ada verifikator
    # manusia atau pihak ketiga, dan keduanya tidak ada di sini.
    VERIFIED = "verified"
    REJECTED = "rejected"


class BankCode(StrEnum):
    """Bank yang dikenal sistem ini. Daftar tertutup, bukan teks bebas:
    nama bank yang diketik bebas tidak bisa dicocokkan dengan apa pun dan
    hanya memindahkan kesalahan ketik ke tempat yang lebih sulit diperbaiki.
    """

    BCA = "bca"
    BNI = "bni"
    BRI = "bri"
    MANDIRI = "mandiri"
    BSI = "bsi"
    CIMB = "cimb"
    PERMATA = "permata"
    DANAMON = "danamon"


class KycSubmission(SQLModel, table=True):
    __tablename__ = "kyc_submissions"
    __table_args__ = (
        # Empat digit terakhir, bukan lebih: kolom ini ada untuk ditampilkan
        # kembali ke pemiliknya ("NIK ...4521"), bukan untuk menyimpan
        # identitasnya.
        CheckConstraint("length(nik_last4) = 4", name="ck_kyc_nik_last4"),
        CheckConstraint("length(account_last4) = 4", name="ck_kyc_account_last4"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # unique: satu akun punya paling banyak satu pengajuan. Mengajukan ulang
    # menimpa yang lama, bukan menumpuk baris yang mana pun bisa terpilih.
    # ondelete CASCADE: pengajuan verifikasi tidak punya arti apa pun tanpa
    # akun pemiliknya, dan baris yatim di sini akan menahan penghapusan akun
    # lewat pelanggaran foreign key yang membingungkan.
    user_id: UUID = Field(
        sa_column=Column(
            Uuid,
            ForeignKey("users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        )
    )

    # Nama sesuai identitas, dan ia memang disimpan utuh: ia sudah tampil di
    # seluruh produk lewat User.name, jadi menyamarkannya di sini tidak
    # melindungi apa pun.
    full_name: str

    # sha256(NIK + pepper). Dipakai HANYA untuk mendeteksi satu NIK dipakai
    # lebih dari satu akun; ia tidak bisa dikembalikan jadi NIK.
    nik_hash: str = Field(index=True)
    nik_last4: str

    bank_code: BankCode = Field(
        sa_column=Column(
            Enum(
                BankCode,
                name="bank_code",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        )
    )
    account_holder_name: str
    account_last4: str

    status: KycStatus = Field(
        sa_column=Column(
            Enum(
                KycStatus,
                name="kyc_status",
                values_callable=lambda enum_cls: [e.value for e in enum_cls],
            ),
            nullable=False,
        )
    )
    # Diisi saat ditolak, supaya pengaju tahu apa yang harus diperbaiki.
    rejection_reason: str | None = Field(default=None, nullable=True)
    submitted_at: datetime = Field(default_factory=lambda: SystemClock().now())

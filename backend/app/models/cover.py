"""Foto sampul satu proposal atau satu campaign.

Disimpan di database, bukan sebagai berkas di disk. Keputusan ini dipilih
karena bentuk deploy project ini: docker-compose.prod.yml hanya punya satu
volume yang bertahan, yaitu `pgdata` milik Postgres. Menaruh sampul di disk
container berarti menambah volume kedua yang harus diingat saat deploy, dan
satu volume yang lupa di-mount membuat SETIAP sampul di situs jadi gambar
rusak di hadapan juri. Lewat Postgres, sampul ikut dalam volume dan cadangan
yang sudah ada.

Harganya nyata dan layak disebut: melayani gambar lewat aplikasi lebih lambat
daripada berkas statis, dan tabel ini akan tumbuh jauh lebih cepat daripada
tabel lain. Keduanya tertahan oleh batas ukuran di services/cover.py; pada
skala lomba ini pertukarannya menguntungkan.

Tabel terpisah, bukan kolom BYTEA di `proposals` dan `campaigns`: baris
proposal dibaca di hampir setiap endpoint, dan menaruh megabyte gambar di
dalamnya membuat setiap SELECT ikut menyeret bytes yang tidak diminta siapa
pun.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, Integer, LargeBinary
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock


class CoverImage(SQLModel, table=True):
    __tablename__ = "cover_images"
    __table_args__ = (
        # Tepat satu pemilik, dan ini ditegakkan database, bukan disiplin
        # pemanggil: baris tanpa pemilik tidak akan pernah terbaca lagi, dan
        # baris dengan dua pemilik membuat "sampul siapa ini" tidak punya
        # jawaban. XOR, bukan dua pemeriksaan terpisah.
        CheckConstraint(
            "(proposal_id IS NOT NULL) <> (campaign_id IS NOT NULL)",
            name="ck_cover_images_exactly_one_owner",
        ),
        # Batas ukuran diulang di sini, bukan hanya di services/cover.py:
        # seed, skrip, dan test bisa menulis baris tanpa pernah lewat service.
        CheckConstraint(
            "byte_size > 0 AND byte_size <= 1572864",
            name="ck_cover_images_byte_size",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # unique=True, bukan sekadar index: satu proposal punya paling banyak satu
    # sampul. Mengganti sampul berarti menimpa baris yang sama, bukan
    # menumpuk baris baru yang mana pun bisa terpilih.
    proposal_id: UUID | None = Field(
        default=None, foreign_key="proposals.id", unique=True, nullable=True
    )
    campaign_id: UUID | None = Field(
        default=None, foreign_key="campaigns.id", unique=True, nullable=True
    )
    # Tipe hasil PEMERIKSAAN BYTE, bukan yang diakui pengunggah. Lihat
    # services/cover.py: Content-Type dari klien tidak pernah dipercaya.
    content_type: str
    byte_size: int = Field(sa_column=Column(Integer, nullable=False))
    data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    # Dipakai dua hal sekaligus: menandai bahwa sampul ADA (lihat
    # schemas/proposal.py cover_updated_at), dan menjadi kunci cache di URL
    # gambar supaya sampul yang diganti tidak tertutup versi lama di browser.
    updated_at: datetime = Field(default_factory=lambda: SystemClock().now())

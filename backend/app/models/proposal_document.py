"""Dokumen proposal: satu berkas PDF per proposal, wajib ada.

Inilah isi proposal yang sebenarnya. Sebelum ini, rencana bisnis diketik UMKM
ke dalam tiga textarea (`business_profile`, `fund_usage_plan`,
`business_projection`) dan Gemini menilai teks itu. Bentuk tersebut salah dua
kali: UMKM sudah punya proposalnya sebagai dokumen dan harus mengetik ulang,
dan dokumen itu kehilangan tabel, rincian biaya, serta foto yang justru
bagian paling informatifnya.

Disimpan di database, bukan sebagai berkas di disk, dengan alasan yang sama
persis seperti foto sampul; penjelasan panjangnya ada di app/models/cover.py.

`extracted_text` bukan duplikasi malas dari `data`. Gemini membaca PDF-nya
sendiri secara native, jadi teks ini tidak dikirim ke model. Ia dipakai untuk
satu hal: memeriksa bahwa kutipan `evidence` pada red flag sungguh ada di
dokumen (lihat drop_hallucinated_evidence di app/ai/gemini_engine.py). Tanpa
kolom ini, server tidak punya apa pun untuk mencocokkan kutipan, dan UMKM
bisa ditolak dengan alasan yang dikarang model.

PDF hasil pindai tidak punya lapisan teks, jadi `extracted_text` akan kosong
untuk berkas semacam itu. Akibatnya disengaja dan diarahkan ke sisi aman:
tidak ada kutipan yang bisa diverifikasi, maka seluruh red flag dibuang.
Skornya tetap jalan, yang hilang hanya alasan bernada tuduhan yang tidak bisa
dibuktikan.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    ForeignKey,
    Integer,
    LargeBinary,
    Text,
    Uuid,
)
from sqlmodel import Field, SQLModel

from app.domain.clock import SystemClock

# 5 MB. Proposal usaha yang memuat foto produk dan tabel biaya lewat dari
# batas sampul (1,5 MB) dengan mudah, tapi 5 MB masih jauh di bawah batas
# permintaan Gemini dan masih masuk akal diunggah lewat jaringan seluler,
# yang memang cara sebagian besar UMKM mengakses layanan ini.
MAX_DOCUMENT_BYTES = 5_242_880


class ProposalDocument(SQLModel, table=True):
    __tablename__ = "proposal_documents"
    __table_args__ = (
        # Diulang di database, bukan hanya di services/document.py: seed,
        # skrip, dan test bisa menulis baris tanpa pernah lewat service.
        CheckConstraint(
            f"byte_size > 0 AND byte_size <= {MAX_DOCUMENT_BYTES}",
            name="ck_proposal_documents_byte_size",
        ),
        CheckConstraint("page_count > 0", name="ck_proposal_documents_page_count"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # unique=True, dan CASCADE: satu proposal punya tepat satu dokumen, dan
    # dokumen tanpa proposal tidak punya arti apa pun.
    proposal_id: UUID = Field(
        sa_column=Column(
            Uuid,
            ForeignKey("proposals.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        )
    )
    # Tipe hasil PEMERIKSAAN BYTE, bukan yang diakui pengunggah. Selalu
    # "application/pdf" hari ini; disimpan sebagai kolom, bukan dikonstanta,
    # supaya format kedua kelak tidak perlu migrasi data.
    content_type: str
    byte_size: int = Field(sa_column=Column(Integer, nullable=False))
    page_count: int = Field(sa_column=Column(Integer, nullable=False))
    data: bytes = Field(sa_column=Column(LargeBinary, nullable=False))
    extracted_text: str = Field(sa_column=Column(Text, nullable=False))
    # Nama asli yang diketik pengunggah, sudah dibersihkan. Dipakai hanya
    # sebagai label tautan unduh, tidak pernah untuk menentukan tipe berkas
    # maupun sebagai nama di disk.
    original_filename: str
    uploaded_at: datetime = Field(default_factory=lambda: SystemClock().now())

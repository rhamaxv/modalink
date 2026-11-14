"""Simpan, baca, dan periksa dokumen proposal.

Aturan yang memandu berkas ini sama dengan services/cover.py: **tipe berkas
ditentukan dari bytenya, bukan dari yang diakui pengunggah.** Content-Type
pada bagian multipart dipilih sepenuhnya oleh klien, jadi ia permintaan
tentang cara isi diperlakukan, bukan pernyataan tentang isinya.

Bedanya dengan sampul ada di apa yang terjadi setelah berkas diterima:
dokumen ini dikirim ke Gemini dan teksnya dipakai memverifikasi kutipan.
Karena itu di sini ada dua pemeriksaan yang tidak ada di sampul, yaitu jumlah
halaman dan keberhasilan parsing, dan keduanya terjadi sebelum satu byte pun
masuk database.
"""

import io
import re
from dataclasses import dataclass
from uuid import UUID

from pypdf import PdfReader
from pypdf.errors import PyPdfError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.clock import Clock
from app.errors import UnprocessableError
from app.models.proposal_document import MAX_DOCUMENT_BYTES, ProposalDocument

# Dua puluh halaman. Batas ini melindungi dua hal sekaligus: biaya pemanggilan
# Gemini, yang naik seiring jumlah halaman, dan kewarasan penilaian itu
# sendiri -- proposal UMKM yang jujur tidak pernah setebal itu, dan dokumen
# 300 halaman jauh lebih mungkin salah unggah daripada proposal sungguhan.
MAX_HALAMAN = 20

# %PDF- adalah satu-satunya pembuka yang sah. Versi setelahnya (1.4, 1.7, 2.0)
# sengaja tidak diperiksa: pypdf di bawah yang menentukan bisa dibaca atau
# tidak, dan menolak versi berdasarkan nomornya di sini akan menolak berkas
# yang sebenarnya terbaca baik-baik saja.
SIDIK_PDF = b"%PDF-"

# Nama berkas hanya dipakai sebagai label tautan unduh. Dibersihkan karena ia
# berasal dari pengunggah dan akan ditampilkan ke pembaca lain: pemisah jalur
# dan karakter kendali dibuang supaya ia tidak pernah bisa dibaca sebagai
# jalur, dan panjangnya dipotong supaya tidak merusak tata letak.
_KARAKTER_AMAN = re.compile(r"[^0-9A-Za-z._ ()\-]")
_TITIK_BERUNTUN = re.compile(r"\.{2,}")
PANJANG_NAMA_MAKS = 120


def bersihkan_nama(nama: str | None) -> str:
    bersih = _KARAKTER_AMAN.sub("", (nama or "").replace("/", " ").replace("\\", " "))
    # Titik beruntun dipadatkan jadi satu. Nama ini tidak pernah dipakai
    # sebagai jalur berkas, jadi ".." di dalamnya tidak bisa menembus
    # direktori mana pun; yang dicegah adalah nama seperti "../../etc/passwd"
    # tampil apa adanya di tautan unduh dan terbaca sebagai sesuatu yang
    # berhasil, padahal tidak.
    bersih = _TITIK_BERUNTUN.sub(".", bersih)
    bersih = bersih.strip(" .") or "proposal.pdf"
    if len(bersih) > PANJANG_NAMA_MAKS:
        bersih = bersih[:PANJANG_NAMA_MAKS]
    return bersih


@dataclass(frozen=True)
class PdfTerperiksa:
    """Hasil pemeriksaan satu berkas PDF.

    Dikembalikan sebagai nilai, bukan disimpan sebagai efek samping, supaya
    pemanggil bisa memeriksa lebih dulu lalu menulis belakangan tanpa
    mengurai berkas yang sama dua kali -- persis yang dibutuhkan
    submit_proposal, yang harus menolak PDF rusak sebelum baris proposal
    mana pun ditulis.
    """

    page_count: int
    text: str


def periksa_pdf(data: bytes) -> PdfTerperiksa:
    """Jumlah halaman dan teks yang bisa diekstrak, atau melempar.

    Mengembalikan teks kosong bukan kegagalan: PDF hasil pindai memang tidak
    punya lapisan teks. Yang gagal hanyalah berkas yang tidak bisa diurai
    sama sekali.
    """
    if not data:
        raise UnprocessableError("berkas_kosong", "Berkas yang diunggah kosong.")
    if len(data) > MAX_DOCUMENT_BYTES:
        raise UnprocessableError(
            "berkas_terlalu_besar",
            f"Ukuran dokumen maksimal {MAX_DOCUMENT_BYTES // 1024 // 1024} MB.",
        )
    if not data.startswith(SIDIK_PDF):
        raise UnprocessableError(
            "format_tidak_didukung",
            "Dokumen proposal harus berformat PDF.",
        )

    # PyPdfError, bukan PdfReadError: ia induk dari seluruh kelas error
    # pypdf (PdfStreamError, ParseError, EmptyFileError, dan seterusnya), dan
    # menangkap hanya satu turunannya berarti berkas rusak dengan cara lain
    # naik sebagai 500, bukan sebagai pesan yang bisa ditindaklanjuti
    # pengunggah.
    try:
        pembaca = PdfReader(io.BytesIO(data))
        halaman = pembaca.pages
        jumlah = len(halaman)
    except (PyPdfError, ValueError, OSError):
        # Satu pesan untuk semua kegagalan parsing, dan pesannya tidak
        # mengutip error pypdf: isinya menyebut offset byte dan nama objek
        # internal yang tidak berarti apa pun bagi UMKM yang mengunggah.
        raise UnprocessableError(
            "pdf_tidak_terbaca",
            "Dokumen PDF tidak bisa dibaca. Coba simpan ulang lalu unggah lagi.",
        ) from None

    if jumlah == 0:
        raise UnprocessableError(
            "pdf_tidak_terbaca",
            "Dokumen PDF tidak punya halaman sama sekali.",
        )
    if jumlah > MAX_HALAMAN:
        raise UnprocessableError(
            "pdf_terlalu_panjang",
            f"Dokumen proposal maksimal {MAX_HALAMAN} halaman.",
            detail={"page_count": jumlah, "max_pages": MAX_HALAMAN},
        )

    # PDF terenkripsi lolos PdfReader tapi semua halamannya kosong saat
    # dibaca. Ditangkap di sini, bukan dibiarkan jadi extracted_text kosong
    # yang tidak bisa dibedakan dari hasil pindai, karena yang ini memang
    # bisa diperbaiki pengunggah dan pantas diberi tahu caranya.
    if pembaca.is_encrypted:
        raise UnprocessableError(
            "pdf_terkunci",
            "Dokumen PDF terkunci sandi. Lepas sandinya lalu unggah lagi.",
        )

    potongan = []
    for satu in halaman:
        try:
            potongan.append(satu.extract_text() or "")
        except Exception:  # noqa: BLE001
            # Satu halaman yang gagal diekstrak tidak boleh menggagalkan
            # seluruh unggahan: Gemini tetap membaca PDF-nya sendiri, dan
            # teks ini hanya alat verifikasi kutipan. Halaman yang hilang
            # berarti kutipan dari halaman itu ikut terbuang, yang arahnya
            # aman.
            potongan.append("")
    return PdfTerperiksa(page_count=jumlah, text="\n".join(potongan).strip())


async def simpan_dokumen(
    session: AsyncSession,
    proposal_id: UUID,
    data: bytes,
    nama_berkas: str | None,
    clock: Clock,
    terperiksa: PdfTerperiksa | None = None,
) -> ProposalDocument:
    """Menyimpan atau MENIMPA dokumen milik satu proposal.

    `terperiksa` diisi pemanggil yang sudah menjalankan periksa_pdf sendiri;
    dibiarkan None, berkasnya diurai di sini.
    """
    hasil = terperiksa or periksa_pdf(data)
    jumlah_halaman, teks = hasil.page_count, hasil.text

    ada = await ambil_dokumen(session, proposal_id)
    sekarang = clock.now()
    if ada is not None:
        ada.content_type = "application/pdf"
        ada.byte_size = len(data)
        ada.page_count = jumlah_halaman
        ada.data = data
        ada.extracted_text = teks
        ada.original_filename = bersihkan_nama(nama_berkas)
        ada.uploaded_at = sekarang
        session.add(ada)
        await session.flush()
        return ada

    baru = ProposalDocument(
        proposal_id=proposal_id,
        content_type="application/pdf",
        byte_size=len(data),
        page_count=jumlah_halaman,
        data=data,
        extracted_text=teks,
        original_filename=bersihkan_nama(nama_berkas),
        uploaded_at=sekarang,
    )
    session.add(baru)
    await session.flush()
    return baru


async def ambil_dokumen(
    session: AsyncSession, proposal_id: UUID
) -> ProposalDocument | None:
    return await session.scalar(
        select(ProposalDocument).where(ProposalDocument.proposal_id == proposal_id)
    )

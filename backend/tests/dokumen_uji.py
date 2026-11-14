"""Pembuat baris ProposalDocument untuk test.

Modul biasa, bukan fixture, karena sebagian pemakainya bukan test maupun
fixture: test konkurensi memanggil fungsi penolong async biasa yang membuka
sesinya sendiri, dan fungsi semacam itu tidak bisa meminta fixture. conftest
mengekspornya kembali sebagai fixture `dokumen_untuk` untuk yang bisa.
"""

from app.models.proposal_document import ProposalDocument
from app.seed.pdf import buat_pdf
from app.services.document import periksa_pdf

# Panjangnya bukan hiasan. MockScoringEngine menilai kualitas data dari
# panjang teks dokumen, dan teks sependek satu kalimat menghasilkan total 56 --
# di bawah ambang 60 milik fixture campaign. Akibatnya proposal yang dipakai
# test lain diam-diam berstatus `rejected`, dan status itu dikecualikan dari
# partial unique index BR-13, sehingga test "proposal kedua ditolak" lulus
# karena alasan yang salah. Teks di bawah ini cukup untuk lolos ambang.
TEKS_BAWAAN = (
    "Usaha ini berjalan sejak 2021 dengan dua pekerja tetap dan omzet "
    "rata-rata Rp12 juta per bulan. Dana yang diminta dipakai untuk membeli "
    "mesin produksi, menambah stok bahan baku selama tiga bulan, dan "
    "memperbaiki etalase depan. Dengan peralatan baru, kapasitas harian naik "
    "sekitar separuh tanpa menambah tenaga kerja, dan omzet diproyeksikan "
    "mencapai Rp18 juta per bulan dalam enam bulan. Pembeli tetap sudah ada "
    "dan menyatakan bersedia menambah pesanan begitu kapasitasnya cukup."
)


def dokumen_untuk(proposal, teks: str = "") -> ProposalDocument:
    """Dokumen PDF untuk proposal yang disusun langsung oleh test.

    Wajib ada, bukan pelengkap: run_scoring menolak menilai proposal tanpa
    dokumen (app/services/scoring.py), jadi setiap test yang menjalankan
    mesin skoring harus punya baris ini.

    PDF-nya dibuat sungguhan lewat app/seed/pdf.py, bukan byte palsu
    bertanda `%PDF-`, dan teksnya diekstrak kembali lewat pypdf persis
    seperti unggahan nyata. Itu disengaja: penanda [[SCORE:n]] yang tidak
    selamat melewati perjalanan tulis-lalu-baca akan ketahuan di sini, bukan
    di produksi.
    """
    isi = buat_pdf(
        f"Proposal {proposal.business_name}",
        [("Uraian", teks or TEKS_BAWAAN)],
    )
    terperiksa = periksa_pdf(isi)
    return ProposalDocument(
        proposal_id=proposal.id,
        content_type="application/pdf",
        byte_size=len(isi),
        page_count=terperiksa.page_count,
        data=isi,
        extracted_text=terperiksa.text,
        original_filename="proposal-uji.pdf",
    )

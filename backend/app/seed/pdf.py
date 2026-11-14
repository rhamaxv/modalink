"""Penghasil PDF seadanya, hanya untuk data demo.

Ditulis tangan, bukan memakai pustaka PDF. Alasannya bukan selera: satu-satunya
pemakainya adalah `python -m app.seed`, dan menarik reportlab (beberapa
megabyte, beserta rantai dependency-nya) ke dalam image produksi demi enam
berkas contoh adalah harga yang tidak sebanding. Yang dihasilkan di sini
sengaja sesederhana mungkin -- satu font bawaan, teks kiri rata, tanpa
gambar -- karena itu memang cukup untuk dokumen contoh.

Batasannya harus disebut supaya tidak ada yang memakainya di luar seed:
tidak ada pembungkusan baris otomatis selain pemotongan kasar per karakter,
tidak ada karakter di luar latin-1, dan tidak ada tabel. Dokumen UMKM
sungguhan datang dari pengunggahnya sendiri dan tidak pernah lewat berkas ini.

Keluarannya sudah diverifikasi bisa dibaca dua pihak yang memang harus
membacanya: pypdf (untuk `extracted_text` di services/document.py) dan Gemini
(yang membaca PDF-nya secara native saat menilai).
"""

import zlib
from collections.abc import Sequence

# A4 dalam satuan titik PDF.
LEBAR = 595
TINGGI = 842

TEPI_KIRI = 50
TEPI_ATAS = 780
TEPI_BAWAH = 60
JARAK_BARIS = 15
UKURAN_FONT = 11

# Helvetica 11pt kira-kira 5,5 titik per karakter, dan lebar teks yang
# tersedia 495 titik. 88 karakter per baris memberi sedikit kelonggaran untuk
# huruf lebar seperti W dan M tanpa teks keluar dari halaman.
LEBAR_BARIS = 88
BARIS_PER_HALAMAN = (TEPI_ATAS - TEPI_BAWAH) // JARAK_BARIS


def _bungkus(teks: str, lebar: int = LEBAR_BARIS) -> list[str]:
    """Pembungkusan per kata. Kata yang sendirian lebih panjang dari satu
    baris dipotong paksa, bukan dibiarkan keluar halaman."""
    hasil: list[str] = []
    for paragraf in teks.split("\n"):
        if not paragraf.strip():
            hasil.append("")
            continue
        baris = ""
        for kata in paragraf.split():
            while len(kata) > lebar:
                if baris:
                    hasil.append(baris)
                    baris = ""
                hasil.append(kata[:lebar])
                kata = kata[lebar:]
            if not baris:
                baris = kata
            elif len(baris) + 1 + len(kata) <= lebar:
                baris = f"{baris} {kata}"
            else:
                hasil.append(baris)
                baris = kata
        hasil.append(baris)
    return hasil


def _aman(teks: str) -> str:
    """Ke latin-1, dengan tanda kurung dan garis miring di-escape.

    Kurung dan backslash adalah sintaks literal string di dalam aliran isi
    PDF; dibiarkan apa adanya, satu tanda kurung dalam teks Indonesia
    ("(spinner)") sudah cukup membuat seluruh berkas gagal diurai.
    """
    bersih = teks.encode("latin-1", errors="replace").decode("latin-1")
    return bersih.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _aliran_halaman(baris: Sequence[str]) -> bytes:
    bagian = [f"BT /F1 {UKURAN_FONT} Tf {TEPI_KIRI} {TEPI_ATAS} Td {JARAK_BARIS} TL"]
    bagian.extend(f"({_aman(b)}) Tj T*" for b in baris)
    bagian.append("ET")
    return zlib.compress("\n".join(bagian).encode("latin-1"))


def buat_pdf(judul: str, bagian: Sequence[tuple[str, str]]) -> bytes:
    """PDF dari judul dan daftar (subjudul, isi).

    Subjudulnya ditulis sebagai barisnya sendiri, bukan ditebalkan: hanya ada
    satu font di berkas ini, dan menebalkan butuh font kedua yang tidak
    menambah apa pun pada isi yang sedang diuji.
    """
    baris: list[str] = [judul.upper(), ""]
    for subjudul, isi in bagian:
        baris.append(subjudul)
        baris.extend(_bungkus(isi))
        baris.append("")

    halaman = [
        baris[i : i + BARIS_PER_HALAMAN]
        for i in range(0, len(baris), BARIS_PER_HALAMAN)
    ] or [[""]]

    # Nomor objek: 1 katalog, 2 pohon halaman, 3 font, lalu sepasang
    # (halaman, aliran isi) untuk tiap halaman.
    nomor_halaman = [4 + i * 2 for i in range(len(halaman))]
    objek: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [{}] /Count {} >>".format(
            " ".join(f"{n} 0 R" for n in nomor_halaman), len(halaman)
        ).encode("latin-1"),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for i, isi_halaman in enumerate(halaman):
        n = nomor_halaman[i]
        objek.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {LEBAR} {TINGGI}] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {n + 1} 0 R >>".encode(
                "latin-1"
            )
        )
        aliran = _aliran_halaman(isi_halaman)
        objek.append(
            f"<< /Length {len(aliran)} /Filter /FlateDecode >>\nstream\n".encode(
                "latin-1"
            )
            + aliran
            + b"\nendstream"
        )

    keluaran = bytearray(b"%PDF-1.4\n")
    posisi: list[int] = []
    for i, satu in enumerate(objek, 1):
        posisi.append(len(keluaran))
        keluaran += f"{i} 0 obj\n".encode("latin-1") + satu + b"\nendobj\n"

    awal_xref = len(keluaran)
    keluaran += f"xref\n0 {len(objek) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for p in posisi:
        keluaran += f"{p:010d} 00000 n \n".encode("latin-1")
    keluaran += (
        f"trailer\n<< /Size {len(objek) + 1} /Root 1 0 R >>\n"
        f"startxref\n{awal_xref}\n%%EOF\n"
    ).encode("latin-1")
    return bytes(keluaran)

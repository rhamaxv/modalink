"""Foto sampul proposal dan campaign: unggah, baca, ganti, hapus.

Yang paling penting di berkas ini adalah kelompok test terakhir: tipe berkas
ditentukan dari BYTE, bukan dari Content-Type yang diakui pengunggah. Header
itu dipilih sepenuhnya oleh klien, jadi mempercayainya berarti membiarkan
pengunggah memutuskan bagaimana isinya nanti diperlakukan browser.
"""

import pytest

# Berkas gambar terkecil yang sah untuk masing-masing format, dipakai sebagai
# muatan unggahan. Bukan gambar karangan: ketiganya memang bisa dibuka.
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c6300010000050001"
    "0d0a2db4"
    "0000000049454e44ae426082"
)
JPEG_AWAL = b"\xff\xd8\xff\xe0" + b"\x00" * 60
WEBP_AWAL = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 60


def berkas(data: bytes, nama: str = "sampul.png", tipe: str = "image/png"):
    return {"file": (nama, data, tipe)}


async def test_umkm_uploads_a_cover_and_anyone_can_read_it_back(
    client, listed_proposal, umkm_lain
):
    r = await client.put(
        f"/api/v1/proposals/{listed_proposal.id}/cover",
        files=berkas(PNG_1x1),
        headers=umkm_lain.headers,
    )
    assert r.status_code == 204

    # Tanpa token: sampul proposal yang sudah listed memang publik.
    gambar = await client.get(f"/api/v1/proposals/{listed_proposal.id}/cover")
    assert gambar.status_code == 200
    assert gambar.content == PNG_1x1
    assert gambar.headers["content-type"] == "image/png"
    # nosniff: tanpa ini browser boleh menebak tipe lain dari isinya sendiri,
    # dan tebakannya bisa berbeda dari yang sudah kita periksa.
    assert gambar.headers["x-content-type-options"] == "nosniff"
    assert gambar.headers["content-disposition"] == "inline"


async def test_uploading_twice_replaces_the_cover_instead_of_stacking_rows(
    client, listed_proposal, umkm_lain
):
    """Satu pemilik satu sampul (unique constraint di models/cover.py).
    Kalau unggahan kedua menambah baris, salah satunya tidak akan pernah
    terbaca lagi dan mana yang tampil jadi bergantung urutan query."""
    await client.put(
        f"/api/v1/proposals/{listed_proposal.id}/cover",
        files=berkas(PNG_1x1),
        headers=umkm_lain.headers,
    )
    r = await client.put(
        f"/api/v1/proposals/{listed_proposal.id}/cover",
        files=berkas(JPEG_AWAL, "sampul.jpg", "image/jpeg"),
        headers=umkm_lain.headers,
    )
    assert r.status_code == 204
    gambar = await client.get(f"/api/v1/proposals/{listed_proposal.id}/cover")
    assert gambar.content == JPEG_AWAL
    assert gambar.headers["content-type"] == "image/jpeg"


async def test_proposal_output_reports_whether_a_cover_exists(
    client, listed_proposal, umkm_lain
):
    """cover_updated_at adalah satu-satunya cara klien tahu harus merender
    gambar atau sampul cadangan. Tanpa field ini, setiap kartu akan memasang
    <img> ke URL yang mungkin 404."""
    sebelum = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert sebelum["cover_updated_at"] is None

    await client.put(
        f"/api/v1/proposals/{listed_proposal.id}/cover",
        files=berkas(PNG_1x1),
        headers=umkm_lain.headers,
    )
    sesudah = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert sesudah["cover_updated_at"] is not None


async def test_proposal_listing_reports_covers_without_a_query_per_row(
    client, listed_proposal, umkm_lain
):
    await client.put(
        f"/api/v1/proposals/{listed_proposal.id}/cover",
        files=berkas(PNG_1x1),
        headers=umkm_lain.headers,
    )
    body = (await client.get("/api/v1/proposals?page_size=50")).json()
    cocok = next(p for p in body["items"] if p["id"] == str(listed_proposal.id))
    assert cocok["cover_updated_at"] is not None


async def test_deleting_the_cover_makes_the_proposal_report_none_again(
    client, listed_proposal, umkm_lain
):
    await client.put(
        f"/api/v1/proposals/{listed_proposal.id}/cover",
        files=berkas(PNG_1x1),
        headers=umkm_lain.headers,
    )
    r = await client.delete(
        f"/api/v1/proposals/{listed_proposal.id}/cover", headers=umkm_lain.headers
    )
    assert r.status_code == 204
    detail = (await client.get(f"/api/v1/proposals/{listed_proposal.id}")).json()
    assert detail["cover_updated_at"] is None
    assert (
        await client.get(f"/api/v1/proposals/{listed_proposal.id}/cover")
    ).status_code == 404


async def test_another_umkm_cannot_upload_a_cover_to_someone_elses_proposal(
    client, listed_proposal, umkm
):
    """404, bukan 403: proposal berstatus submitted hanya boleh dilihat
    pemiliknya dan pemilik campaign, jadi membalas 403 di sini akan
    mengonfirmasi keberadaannya kepada UMKM lain."""
    # listed_proposal dimiliki umkm_lain (lihat tests/conftest.py), jadi
    # `umkm` di sini adalah UMKM lain yang mencoba menimpa sampul orang.
    r = await client.put(
        f"/api/v1/proposals/{listed_proposal.id}/cover",
        files=berkas(PNG_1x1),
        headers=umkm.headers,
    )
    assert r.status_code == 404


async def test_investor_uploads_a_campaign_cover_and_it_is_publicly_readable(
    client, campaign, investor
):
    r = await client.put(
        f"/api/v1/campaigns/{campaign.id}/cover",
        files=berkas(WEBP_AWAL, "sampul.webp", "image/webp"),
        headers=investor.headers,
    )
    assert r.status_code == 204
    gambar = await client.get(f"/api/v1/campaigns/{campaign.id}/cover")
    assert gambar.status_code == 200
    assert gambar.headers["content-type"] == "image/webp"

    daftar = (await client.get("/api/v1/campaigns?page_size=50")).json()
    cocok = next(c for c in daftar["items"] if c["id"] == str(campaign.id))
    assert cocok["cover_updated_at"] is not None


class TestTipeDitentukanDariByteBukanDariKlien:
    """Content-Type pada bagian multipart dipilih klien, jadi ia bukan
    pernyataan tentang isi berkas melainkan permintaan tentang cara isi itu
    diperlakukan. Gambar yang dilayani kembali dari origin yang sama dengan
    aplikasi, dengan tipe yang ditentukan penyerang, adalah jalur XSS klasik.
    """

    @pytest.mark.parametrize(
        "muatan,nama,tipe_diakui",
        [
            # Berkas HTML yang mengaku PNG. Diterima dan dilayani sebagai
            # text/html, ia berjalan sebagai halaman di origin aplikasi.
            (b"<html><script>alert(1)</script></html>", "x.png", "image/png"),
            # SVG sengaja tidak termasuk format yang diterima meski ia gambar:
            # SVG bisa memuat <script>.
            (
                b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>',
                "x.svg",
                "image/svg+xml",
            ),
            # Teks biasa yang mengaku JPEG.
            (b"bukan gambar sama sekali", "x.jpg", "image/jpeg"),
            # PDF: berkas sungguhan, format sungguhan, tetap bukan gambar.
            (b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n", "x.pdf", "image/png"),
        ],
    )
    async def test_rejects_a_file_whose_bytes_are_not_an_accepted_image(
        self, client, listed_proposal, umkm_lain, muatan, nama, tipe_diakui
    ):
        r = await client.put(
            f"/api/v1/proposals/{listed_proposal.id}/cover",
            files=berkas(muatan, nama, tipe_diakui),
            headers=umkm_lain.headers,
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "format_tidak_didukung"
        # Dan tidak ada yang tersimpan diam-diam.
        assert (
            await client.get(f"/api/v1/proposals/{listed_proposal.id}/cover")
        ).status_code == 404

    async def test_accepts_a_real_image_even_when_the_client_mislabels_it(
        self, client, listed_proposal, umkm_lain
    ):
        """Sisi sebaliknya, dan ia yang membuktikan pemeriksaannya memang
        melihat byte: PNG sungguhan yang diakui klien sebagai application/
        octet-stream tetap diterima, dan dilayani sebagai image/png."""
        r = await client.put(
            f"/api/v1/proposals/{listed_proposal.id}/cover",
            files=berkas(PNG_1x1, "tanpa-nama", "application/octet-stream"),
            headers=umkm_lain.headers,
        )
        assert r.status_code == 204
        gambar = await client.get(f"/api/v1/proposals/{listed_proposal.id}/cover")
        assert gambar.headers["content-type"] == "image/png"

    async def test_rejects_an_empty_file(self, client, listed_proposal, umkm_lain):
        r = await client.put(
            f"/api/v1/proposals/{listed_proposal.id}/cover",
            files=berkas(b"", "kosong.png"),
            headers=umkm_lain.headers,
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "berkas_kosong"

    async def test_rejects_a_file_past_the_size_limit(
        self, client, listed_proposal, umkm_lain
    ):
        """Batasnya ditegakkan server, dan pembacaannya berhenti begitu
        terlampaui: membaca seluruh unggahan dulu baru menolaknya berarti
        penyerang tetap bisa memaksa server menulis berkas sebesar apa pun ke
        disk sementara."""
        from app.services.cover import MAX_COVER_BYTES

        kebesaran = PNG_1x1 + b"\x00" * (MAX_COVER_BYTES + 1)
        r = await client.put(
            f"/api/v1/proposals/{listed_proposal.id}/cover",
            files=berkas(kebesaran),
            headers=umkm_lain.headers,
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "berkas_terlalu_besar"

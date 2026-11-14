"""Submit proposal: aturan bisnisnya, dan pemeriksaan dokumen yang wajib.

Seluruh berkas ini memakai fixture `kirim_proposal`, bukan client.post(json=)
langsung: pengajuan proposal berbentuk multipart sejak uraiannya pindah ke
PDF, dan mengeja bentuk permintaan itu di tiap test berarti perubahan kontrak
berikutnya harus disentuh belasan kali.
"""

import pytest

from app.seed.pdf import buat_pdf


async def test_umkm_can_submit_proposal(kirim_proposal, umkm, campaign):
    res = await kirim_proposal(campaign.id, headers=umkm.headers)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "submitted"
    assert data["scoring_status"] in {"pending", "processing", "done"}


async def test_submitted_document_is_readable_back(
    kirim_proposal, umkm, campaign, client
):
    """Dokumen yang diunggah harus bisa dibaca kembali apa adanya, bukan
    sekadar diterima: proposal yang dokumennya tidak bisa dibuka investor
    sama tidak bergunanya dengan proposal tanpa dokumen."""
    pdf = buat_pdf("Proposal Uji Baca", [("Uraian", "Kalimat penanda unik 48217.")])
    res = await kirim_proposal(campaign.id, headers=umkm.headers, pdf=pdf)
    assert res.status_code == 201

    unduh = await client.get(
        f"/api/v1/proposals/{res.json()['id']}/document", headers=umkm.headers
    )
    assert unduh.status_code == 200
    assert unduh.headers["content-type"].startswith("application/pdf")
    assert unduh.headers["x-content-type-options"] == "nosniff"
    assert unduh.content == pdf


# ------------------------------------------------------- dokumen wajib & sah


async def test_submit_without_a_document_is_rejected(
    client, umkm, campaign, body_proposal
):
    """Tanpa bagian `document` sama sekali. 422 dari FastAPI, bukan 201
    dengan proposal yang tidak punya isi."""
    import json

    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        data={"payload": json.dumps(body_proposal())},
    )
    assert res.status_code == 422


@pytest.mark.parametrize(
    ("isi", "kode"),
    [
        (b"", "berkas_kosong"),
        (b"\x89PNG\r\n\x1a\nbukan pdf sama sekali", "format_tidak_didukung"),
        # Diawali %PDF- supaya sidik bytenya lolos, tapi isinya bukan PDF:
        # inilah yang membedakan pemeriksaan sungguhan dari pemeriksaan
        # header belaka.
        (b"%PDF-1.4\nisi yang tidak bisa diurai sama sekali", "pdf_tidak_terbaca"),
    ],
)
async def test_invalid_documents_are_rejected_before_any_row_is_written(
    kirim_proposal, client, umkm, campaign, isi, kode
):
    res = await kirim_proposal(campaign.id, headers=umkm.headers, pdf=isi)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == kode

    # Tidak ada proposal yang tertinggal: penolakan dokumen terjadi sebelum
    # satu baris pun ditulis, bukan sesudahnya.
    milik = await client.get("/api/v1/proposals/mine", headers=umkm.headers)
    assert milik.json() == []


async def test_a_document_longer_than_the_page_cap_is_rejected(
    kirim_proposal, umkm, campaign
):
    """Batas halaman melindungi biaya pemanggilan Gemini, yang naik seiring
    jumlah halaman."""
    tebal = buat_pdf("Proposal Terlalu Tebal", [("Uraian", "x " * 45_000)])
    res = await kirim_proposal(campaign.id, headers=umkm.headers, pdf=tebal)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "pdf_terlalu_panjang"


async def test_uploaded_filename_is_sanitised_before_it_is_served_back(
    kirim_proposal, client, umkm, campaign
):
    """Nama berkas datang dari pengunggah dan ikut ke header
    Content-Disposition. Tanda kutip dan pemisah jalur di dalamnya harus
    sudah hilang sebelum sampai ke sana."""
    res = await kirim_proposal(
        campaign.id,
        headers=umkm.headers,
        nama_berkas='../../etc/pas"swd.pdf',
    )
    assert res.status_code == 201

    unduh = await client.get(
        f"/api/v1/proposals/{res.json()['id']}/document", headers=umkm.headers
    )
    disposisi = unduh.headers["content-disposition"]
    assert ".." not in disposisi
    assert "/" not in disposisi.split("filename=")[1]
    assert disposisi.count('"') == 2


# ------------------------------------------------------------ aturan bisnis


async def test_business_summary_under_30_characters_rejected(
    kirim_proposal, umkm, campaign
):
    res = await kirim_proposal(
        campaign.id, headers=umkm.headers, business_summary="x" * 29
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "payload_tidak_valid"


async def test_business_summary_exactly_30_characters_accepted(
    kirim_proposal, umkm, campaign
):
    """Batas tepat, bukan hanya satu di bawah dan satu jauh di atas:
    off-by-one di validator lolos tanpa kasus ini."""
    res = await kirim_proposal(
        campaign.id, headers=umkm.headers, business_summary="x" * 30
    )
    assert res.status_code == 201


async def test_business_summary_over_500_characters_rejected(
    kirim_proposal, umkm, campaign
):
    """Batas atasnya kecil dengan sengaja: field yang muat satu halaman akan
    dipakai sebagai satu halaman, dan proposal kembali terbelah antara
    formulir dan dokumen."""
    res = await kirim_proposal(
        campaign.id, headers=umkm.headers, business_summary="x" * 501
    )
    assert res.status_code == 422


async def test_br11_funds_exceeding_campaign_target_rejected(
    kirim_proposal, umkm, campaign
):
    res = await kirim_proposal(
        campaign.id,
        headers=umkm.headers,
        requested_amount=campaign.target_amount + 1,
        milestones=[
            {
                "seq": 1,
                "title": "a",
                "description": "x" * 20,
                "amount": campaign.target_amount + 1,
            }
        ],
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "dana_melebihi_target_campaign"


async def test_br14_milestone_amount_mismatch_rejected_with_difference(
    kirim_proposal, umkm, campaign
):
    res = await kirim_proposal(
        campaign.id,
        headers=umkm.headers,
        milestones=[
            {"seq": 1, "title": "a", "description": "x" * 20, "amount": 5_000_000},
            {"seq": 2, "title": "b", "description": "x" * 20, "amount": 4_000_000},
        ],
    )
    assert res.status_code == 422
    assert "Rp1.000.000" in res.json()["error"]["message"]


async def test_br12_funds_below_minimum_rejected(kirim_proposal, umkm, campaign):
    res = await kirim_proposal(
        campaign.id,
        headers=umkm.headers,
        requested_amount=400_000,
        milestones=[
            {"seq": 1, "title": "a", "description": "x" * 20, "amount": 200_000},
            {"seq": 2, "title": "b", "description": "x" * 20, "amount": 200_000},
        ],
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "dana_di_bawah_minimum"


async def test_br13_second_proposal_to_same_campaign_rejected_409(
    kirim_proposal, umkm, campaign
):
    await kirim_proposal(campaign.id, headers=umkm.headers)
    res = await kirim_proposal(campaign.id, headers=umkm.headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "proposal_aktif_sudah_ada"


async def test_br17_campaign_past_apply_deadline_rejects(
    kirim_proposal, umkm, campaign_kedaluwarsa
):
    res = await kirim_proposal(campaign_kedaluwarsa.id, headers=umkm.headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "pengajuan_ditutup"


async def test_t3_more_than_30_milestones_rejected(kirim_proposal, umkm, campaign):
    """Review keamanan: 50.000 item milestone lolos tanpa batas atas sebelum
    ini. 30 tahap jauh di atas rencana pendanaan bertahap mana pun yang
    wajar (seed data terpanjang hanya dua tahap)."""
    banyak = [
        {"seq": i, "title": f"Tahap {i}", "description": "x" * 20, "amount": 100_000}
        for i in range(1, 32)
    ]
    res = await kirim_proposal(
        campaign.id,
        headers=umkm.headers,
        requested_amount=31 * 100_000,
        milestones=banyak,
    )
    assert res.status_code == 422


async def test_malformed_payload_json_is_rejected_as_a_product_error(
    client, umkm, campaign, dokumen_proposal
):
    """Bagian `payload` diurai sendiri oleh endpoint, bukan oleh FastAPI,
    jadi JSON rusak harus tetap keluar dalam bentuk error produk ini dan
    bukan sebagai 500."""
    res = await client.post(
        f"/api/v1/campaigns/{campaign.id}/proposals",
        headers=umkm.headers,
        data={"payload": "{bukan json"},
        files={"document": ("p.pdf", dokumen_proposal(), "application/pdf")},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "payload_tidak_valid"


async def test_br18_no_endpoint_to_update_proposal(app):
    rute = {
        (m, r.path)
        for r in app.routes
        if getattr(r, "methods", None)
        for m in r.methods
    }
    assert ("PATCH", "/api/v1/proposals/{proposal_id}") not in rute
    assert ("PUT", "/api/v1/proposals/{proposal_id}") not in rute

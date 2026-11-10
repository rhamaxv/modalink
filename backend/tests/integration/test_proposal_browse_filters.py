"""Query `sector`, `campaign_id`, dan `sort` di GET /proposals, dan `sector`
plus paginasi di GET /campaigns (10-api-contract.md baris 44 dan 55).

Ketiganya sudah tertulis di kontrak sejak awal tapi tidak pernah ada di
implementasi: endpoint hanya mengenal `page`. Halaman jelajah karena itu
tidak punya cara apa pun menyempitkan daftar, dan begitu proposal melewati
satu halaman, sisanya praktis tidak terjangkau.
"""

from datetime import timedelta

import pytest

from app.domain.clock import SystemClock
from app.models.campaign import Campaign, CampaignStatus, Sector
from app.models.proposal import Proposal, ProposalStatus, ScoringStatus
from app.models.user import Role


async def _campaign(db, investor, sector: Sector, judul: str) -> Campaign:
    mulai = SystemClock().now()
    c = Campaign(
        investor_id=investor.user.id,
        title=judul,
        description="Mendanai usaha skala rumahan." * 3,
        sector=sector,
        target_amount=50_000_000,
        apply_deadline=mulai + timedelta(days=7),
        funding_deadline=mulai + timedelta(days=21),
        score_threshold=60,
        status=CampaignStatus.OPEN,
        created_at=mulai,
    )
    db.add(c)
    await db.flush()
    return c


async def _listed(db, buat_akun, campaign: Campaign, nama: str, nominal: int):
    """Proposal yang sudah listed, ditulis langsung tanpa menjalankan mesin
    skoring: yang diuji di berkas ini adalah penyaringan dan pengurutan
    daftar, bukan jalur scoring yang sudah punya testnya sendiri."""
    akun = await buat_akun(db, f"{nama}@filter-teruji.id", Role.UMKM)
    p = Proposal(
        campaign_id=campaign.id,
        umkm_id=akun.user.id,
        business_name=nama,
        business_profile="x" * 110,
        fund_usage_plan="x" * 110,
        business_projection="x" * 60,
        requested_amount=nominal,
        status=ProposalStatus.LISTED,
        scoring_status=ScoringStatus.DONE,
    )
    db.add(p)
    await db.flush()
    return p


@pytest.fixture
async def pasar(db, investor, buat_akun):
    """Dua campaign di dua sektor berbeda, masing-masing berisi proposal
    dengan nominal yang berbeda-beda."""
    kuliner = await _campaign(db, investor, Sector.KULINER, "Modal warung kopi")
    kerajinan = await _campaign(db, investor, Sector.KERAJINAN, "Modal batik tulis")
    return {
        "kuliner": kuliner,
        "kerajinan": kerajinan,
        "kopi": await _listed(db, buat_akun, kuliner, "Kopi Senja", 30_000_000),
        "soto": await _listed(db, buat_akun, kuliner, "Soto Pagi", 10_000_000),
        "batik": await _listed(db, buat_akun, kerajinan, "Batik Lereng", 20_000_000),
    }


# Hanya nama milik fixture `pasar` yang diperhatikan, dan hitungan global
# tidak pernah diassert.
#
# Test di repo ini berjalan di database yang dipakai bersama (lihat
# tests/conftest.py: isolasinya transaksi per test, bukan database kosong per
# test), jadi assert seperti `total == 1` lulus hanya selama tidak ada baris
# lain yang kebetulan cocok. Dua test pernah gagal persis begitu di project
# ini dan sempat salah didiagnosis sebagai kontaminasi.
NAMA_PASAR = {"Kopi Senja", "Soto Pagi", "Batik Lereng"}


async def _nama(client, kueri: str = "") -> list[str]:
    body = (await client.get(f"/api/v1/proposals{kueri}")).json()
    return [
        p["business_name"] for p in body["items"] if p["business_name"] in NAMA_PASAR
    ]


async def _total(client, kueri: str = "") -> int:
    return (await client.get(f"/api/v1/proposals{kueri}")).json()["total"]


async def test_sector_filters_proposals_through_their_campaign(client, pasar):
    """Sektor adalah sifat campaign, bukan kolom di proposal: filternya harus
    tetap bekerja lewat JOIN tanpa menyalin kolom ke tabel proposal."""
    assert await _nama(client, "?sector=kerajinan&page_size=50") == ["Batik Lereng"]


async def test_sector_filter_also_narrows_the_reported_total(client, pasar):
    """Total yang menyaring lebih longgar dari barisnya adalah cara paginasi
    menjanjikan halaman berikutnya yang isinya kosong.

    Dibandingkan terhadap total tanpa filter, bukan terhadap angka tetap:
    yang harus benar adalah totalnya IKUT menyempit, bukan nilainya persis.
    """
    tanpa_filter = await _total(client)
    dengan_filter = await _total(client, "?sector=kerajinan")
    assert dengan_filter < tanpa_filter
    body = (await client.get("/api/v1/proposals?sector=kerajinan")).json()
    assert len(body["items"]) == body["total"] or body["total"] > len(body["items"])
    assert all(p["business_name"] != "Kopi Senja" for p in body["items"])


async def test_campaign_id_filters_to_one_campaign(client, pasar):
    hasil = await _nama(client, f"?campaign_id={pasar['kuliner'].id}&page_size=50")
    assert sorted(hasil) == ["Kopi Senja", "Soto Pagi"]


async def test_sort_amount_desc_orders_by_requested_amount(client, pasar):
    """Urutan relatif di antara tiga proposal fixture, bukan daftar persis:
    proposal lain di database bersama boleh menyelip di antaranya tanpa
    membuat pengurutan jadi salah."""
    assert await _nama(client, "?sort=amount_desc&page_size=50") == [
        "Kopi Senja",
        "Batik Lereng",
        "Soto Pagi",
    ]


async def test_sort_amount_asc_is_the_exact_reverse(client, pasar):
    assert await _nama(client, "?sort=amount_asc&page_size=50") == [
        "Soto Pagi",
        "Batik Lereng",
        "Kopi Senja",
    ]


async def test_default_sort_is_newest_first(client, pasar):
    """Tanpa `sort`, urutan harus sama persis dengan sebelum query ini ada:
    proposal terbaru lebih dulu. Menambah parameter tidak boleh diam-diam
    mengubah apa yang dilihat pengunjung yang tidak memintanya."""
    assert await _nama(client, "?page_size=50") == await _nama(
        client, "?sort=newest&page_size=50"
    )


async def test_unknown_sort_value_is_rejected_instead_of_silently_ignored(
    client, pasar
):
    """422, bukan jatuh ke urutan default: daftar yang diam-diam mengabaikan
    permintaan urutan berbohong tentang apa yang ditampilkannya."""
    assert (await client.get("/api/v1/proposals?sort=paling_keren")).status_code == 422


async def test_unknown_sector_value_is_rejected(client, pasar):
    assert (await client.get("/api/v1/proposals?sector=kriptografi")).status_code == 422


async def test_filters_compose_with_each_other(client, pasar):
    hasil = await _nama(client, "?sector=kuliner&sort=amount_asc&page_size=50")
    assert hasil == ["Soto Pagi", "Kopi Senja"]


async def test_filters_survive_pagination_without_losing_or_repeating_rows(
    client, pasar
):
    """Satu baris per halaman, tiga halaman: tidak ada nama yang hilang dan
    tidak ada yang muncul dua kali. Ini yang dijaga tie-break id di ORDER BY.
    """
    total = await _total(client, "?sort=amount_desc")
    terkumpul: list[str] = []
    semua: list[str] = []
    for halaman in range(1, total + 1):
        body = (
            await client.get(
                f"/api/v1/proposals?sort=amount_desc&page={halaman}&page_size=1"
            )
        ).json()
        nama = [p["business_name"] for p in body["items"]]
        semua += nama
        terkumpul += [n for n in nama if n in NAMA_PASAR]
    assert terkumpul == ["Kopi Senja", "Batik Lereng", "Soto Pagi"]
    assert len(semua) == len(set(semua)), "ada baris yang muncul di dua halaman"


async def test_campaign_listing_reports_a_total_alongside_its_page(client, pasar):
    """GET /campaigns dulu mengirim SELURUH campaign open ke setiap pengunjung
    tanpa parameter paginasi sama sekali, walau kontrak menyebut `page`."""
    body = (await client.get("/api/v1/campaigns?page_size=1")).json()
    assert len(body["items"]) == 1
    assert body["total"] >= 2, "fixture pasar membuat dua campaign"
    assert body["total"] > len(body["items"]), "total harus melampaui satu halaman"
    assert body["page"] == 1
    assert body["page_size"] == 1


async def test_campaign_listing_filters_by_sector(client, pasar):
    body = (await client.get("/api/v1/campaigns?sector=kerajinan")).json()
    judul = [c["title"] for c in body["items"]]
    assert "Modal batik tulis" in judul
    assert "Modal warung kopi" not in judul, (
        "campaign kuliner tidak boleh lolos filter kerajinan"
    )
    assert all(c["sector"] == "kerajinan" for c in body["items"])


async def test_campaign_page_size_is_capped_by_the_server(client, pasar):
    """Batas atas ditegakkan server, bukan diserahkan ke kesopanan klien:
    page_size=100000 sama buruknya dengan tidak ada paginasi sama sekali."""
    assert (await client.get("/api/v1/campaigns?page_size=100000")).status_code == 422

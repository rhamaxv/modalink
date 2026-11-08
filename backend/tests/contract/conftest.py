"""Fixture dan gerbang skip untuk test kontrak Gemini (dipanggil `make test-live`).

Dataclass draft di sini sengaja lepas dari app.models: test kontrak tidak
boleh butuh Postgres, hanya butuh objek yang punya field yang dibaca
GeminiEngine (lihat ProposalLike/CampaignLike di app/ai/engine.py).
"""

from dataclasses import dataclass

import pytest

from app.ai.gemini_engine import GeminiEngine
from app.config import settings


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Test bertanda `live` di-skip kecuali dipilih eksplisit lewat -m live.

    `make test-live` memanggil `pytest tests/contract -m live`, yang mengisi
    config.option.markexpr, sehingga hook ini tidak menyentuh apa-apa. Tanpa
    -m eksplisit (misal `pytest` biasa yang ikut mengoleksi direktori ini),
    seluruh test di sini di-skip, supaya jaringan tidak pernah tersentuh
    tanpa diminta secara sadar.
    """
    if config.option.markexpr:
        return
    skip_live = pytest.mark.skip(reason="live: hanya jalan lewat `make test-live`")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@dataclass
class ProposalKontrak:
    business_name: str
    business_profile: str
    fund_usage_plan: str
    business_projection: str
    requested_amount: int


@dataclass
class CampaignKontrak:
    title: str
    sector: str
    target_amount: int
    description: str


@pytest.fixture
def campaign_draft() -> CampaignKontrak:
    return CampaignKontrak(
        title="Modal warung kopi Jakarta Timur",
        sector="kuliner",
        target_amount=50_000_000,
        description="Mendanai ekspansi warung kopi skala rumahan di Jakarta Timur.",
    )


@pytest.fixture
def proposal_bagus() -> ProposalKontrak:
    return ProposalKontrak(
        business_name="Warung Kopi Mbak Sri",
        business_profile=(
            "Warung kopi rumahan di Jakarta Timur, berjalan 3 tahun, 2 pekerja "
            "tetap, omzet rata-rata Rp12 juta per bulan, melayani pelanggan "
            "tetap kantor di sekitar lokasi usaha."
        ),
        fund_usage_plan=(
            "Rp6 juta untuk mesin kopi semi-otomatis, Rp3 juta untuk bahan baku "
            "biji dan susu selama tiga bulan, dan Rp1 juta untuk memperbaiki "
            "etalase depan yang sudah lapuk."
        ),
        business_projection=(
            "Omzet diperkirakan naik ke Rp18 juta per bulan dalam 6 bulan "
            "setelah mesin baru dipakai, didukung kenaikan kapasitas seduh "
            "harian dari 40 ke 70 cangkir per hari."
        ),
        requested_amount=10_000_000,
    )


@pytest.fixture
def proposal_biasa() -> ProposalKontrak:
    """Isian lengkap secara panjang tapi umum, tanpa angka spesifik: harus
    dinilai lebih rendah dari proposal_bagus, lebih tinggi dari proposal_red_flag."""
    return ProposalKontrak(
        business_name="Kedai Kopi Sederhana",
        business_profile=(
            "Usaha kopi kecil yang sudah berjalan beberapa tahun di daerah "
            "perkotaan, melayani pelanggan sekitar dengan cukup baik setiap "
            "harinya tanpa kendala berarti."
        ),
        fund_usage_plan=(
            "Dana akan dipakai untuk kebutuhan operasional usaha sehari-hari "
            "dan sedikit perbaikan fasilitas yang diperlukan ke depannya."
        ),
        business_projection=(
            "Usaha diperkirakan akan terus berjalan dan berkembang secara "
            "wajar seiring waktu dengan dukungan dana tambahan ini."
        ),
        requested_amount=10_000_000,
    )


@pytest.fixture
def proposal_red_flag() -> ProposalKontrak:
    """Angka proyeksi bertentangan dengan skala usaha di profil: harus
    memicu red flag critical (projeksi_tidak_realistis / angka_tidak_konsisten)."""
    return ProposalKontrak(
        business_name="Warung Kopi Mini",
        business_profile=(
            "Warung kopi rumahan kecil di gang sempit, baru buka 2 bulan, "
            "dikelola sendiri tanpa pekerja, omzet rata-rata Rp1,5 juta per "
            "bulan dari pelanggan tetangga sekitar rumah."
        ),
        fund_usage_plan=(
            "Rp8 juta untuk mesin kopi semi-otomatis dan Rp2 juta untuk "
            "renovasi kecil etalase."
        ),
        business_projection=(
            "Omzet diperkirakan melonjak menjadi Rp900 juta per hari dalam "
            "waktu satu bulan setelah mesin baru dipasang, karena permintaan "
            "diperkirakan meningkat drastis dari seluruh kota."
        ),
        requested_amount=10_000_000,
    )


@pytest.fixture
def gemini_engine() -> GeminiEngine:
    return GeminiEngine.from_settings(settings)

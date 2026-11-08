"""Fixture proposal/campaign yang belum tersimpan, dipakai test engine skoring.

Dataclass tersendiri, bukan model Proposal/Campaign dari app.models: proposal
sungguhan belum punya kolom sector (lihat 04-feature-umkm.md, sector hanya ada
di campaign), sementara MockScoringEngine di fase ini menilai kecocokan
sektor. Unit test tidak boleh butuh Postgres, jadi draft di sini sengaja tidak
disentuh ke database sama sekali.
"""

from dataclasses import dataclass

import pytest

from app.models.campaign import Sector


@dataclass
class ProposalDraft:
    business_name: str
    business_profile: str
    fund_usage_plan: str
    business_projection: str
    sector: Sector


@dataclass
class CampaignDraft:
    sector: Sector


@pytest.fixture
def campaign_draft() -> CampaignDraft:
    return CampaignDraft(sector=Sector.KULINER)


@pytest.fixture
def proposal_draft() -> ProposalDraft:
    return ProposalDraft(
        business_name="Warung Kopi Mbak Sri",
        business_profile=(
            "Warung kopi rumahan di Jakarta Timur, berjalan 3 tahun, 2 pekerja, "
            "omzet rata-rata Rp12 juta per bulan, melayani pelanggan tetap "
            "kantor di sekitar lokasi usaha."
        ),
        fund_usage_plan=(
            "Rp6 juta untuk mesin kopi semi-otomatis, Rp3 juta untuk bahan "
            "baku biji dan susu selama tiga bulan, dan Rp1 juta untuk "
            "memperbaiki etalase depan yang sudah lapuk."
        ),
        business_projection=(
            "Omzet diperkirakan naik ke Rp18 juta per bulan dalam 6 bulan "
            "setelah mesin baru dipakai, didukung kenaikan kapasitas seduh "
            "harian."
        ),
        sector=Sector.KULINER,
    )


@pytest.fixture
def proposal_draft_tipis() -> ProposalDraft:
    """Lawan proposal_draft: isian pendek dan sektor tidak cocok dengan
    campaign_draft, dipakai membuktikan mock tidak memberi skor acak."""
    return ProposalDraft(
        business_name="Warung Tipis",
        business_profile="Warung kecil.",
        fund_usage_plan="Buat modal.",
        business_projection="Naik.",
        sector=Sector.TEKNOLOGI,
    )

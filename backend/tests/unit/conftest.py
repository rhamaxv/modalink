"""Fixture proposal/campaign yang belum tersimpan, dipakai test engine skoring.

Dataclass tersendiri, bukan model Proposal/Campaign dari app.models: sengaja
dibuat ringan agar unit test tidak butuh Postgres sama sekali. Field yang
disertakan di sini dibatasi pada yang benar-benar dibaca MockScoringEngine
(lihat ProposalLike/CampaignLike di app/ai/engine.py, C-25).
"""

from dataclasses import dataclass

import pytest


@dataclass
class ProposalDraft:
    business_name: str
    business_profile: str
    fund_usage_plan: str
    business_projection: str
    requested_amount: int


@dataclass
class CampaignDraft:
    target_amount: int


@pytest.fixture
def campaign_draft() -> CampaignDraft:
    return CampaignDraft(target_amount=50_000_000)


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
        requested_amount=10_000_000,
    )


@pytest.fixture
def proposal_draft_tipis() -> ProposalDraft:
    """Lawan proposal_draft: isian pendek, dipakai membuktikan mock tidak
    memberi skor acak. requested_amount sama dengan proposal_draft supaya
    bedanya cuma kelengkapan isian, bukan porsi dana."""
    return ProposalDraft(
        business_name="Warung Tipis",
        business_profile="Warung kecil.",
        fund_usage_plan="Buat modal.",
        business_projection="Naik.",
        requested_amount=10_000_000,
    )

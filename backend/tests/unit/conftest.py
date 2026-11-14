"""Fixture proposal/campaign/dokumen yang belum tersimpan, dipakai test engine
skoring.

Dataclass tersendiri, bukan model Proposal/Campaign dari app.models: sengaja
dibuat ringan agar unit test tidak butuh Postgres sama sekali. Field yang
disertakan di sini dibatasi pada yang benar-benar dibaca engine skoring
(lihat ProposalLike/CampaignLike/DocumentLike/MilestoneLike di
app/ai/engine.py, C-25).

`DocumentDraft.data` boleh byte sembarang pada test mock: MockScoringEngine
tidak pernah menyentuhnya, ia hanya membaca `extracted_text`. Test GeminiEngine
yang memang mengirim bytenya memakai PDF sungguhan.
"""

from dataclasses import dataclass

import pytest


@dataclass
class ProposalDraft:
    business_name: str
    business_summary: str
    requested_amount: int


@dataclass
class DocumentDraft:
    extracted_text: str
    data: bytes = b"%PDF-1.4 bukan PDF sungguhan"


@dataclass
class MilestoneDraft:
    seq: int
    title: str
    amount: int


@dataclass
class CampaignDraft:
    target_amount: int
    title: str = "Modal Usaha Kuliner Rumahan"
    sector: str = "kuliner"
    description: str = "Pendanaan untuk usaha kuliner skala rumahan."


@pytest.fixture
def campaign_draft() -> CampaignDraft:
    return CampaignDraft(target_amount=50_000_000)


@pytest.fixture
def proposal_draft() -> ProposalDraft:
    return ProposalDraft(
        business_name="Warung Kopi Mbak Sri",
        business_summary=(
            "Warung kopi rumahan di Jakarta Timur, berjalan 3 tahun, 2 pekerja, "
            "omzet rata-rata Rp12 juta per bulan."
        ),
        requested_amount=10_000_000,
    )


@pytest.fixture
def proposal_draft_tipis() -> ProposalDraft:
    """Lawan proposal_draft. requested_amount sama supaya bedanya cuma isi
    dokumen, bukan porsi dana."""
    return ProposalDraft(
        business_name="Warung Tipis",
        business_summary="Warung kecil yang ingin menambah modal usaha.",
        requested_amount=10_000_000,
    )


@pytest.fixture
def document_draft() -> DocumentDraft:
    return DocumentDraft(
        extracted_text=(
            "Warung kopi rumahan di Jakarta Timur, berjalan 3 tahun, 2 pekerja, "
            "omzet rata-rata Rp12 juta per bulan, melayani pelanggan tetap "
            "kantor di sekitar lokasi usaha. Rp6 juta untuk mesin kopi "
            "semi-otomatis, Rp3 juta untuk bahan baku biji dan susu selama tiga "
            "bulan, dan Rp1 juta untuk memperbaiki etalase depan yang sudah "
            "lapuk. Omzet diperkirakan naik ke Rp18 juta per bulan dalam 6 bulan "
            "setelah mesin baru dipakai, didukung kenaikan kapasitas seduh "
            "harian."
        )
    )


@pytest.fixture
def document_draft_tipis() -> DocumentDraft:
    return DocumentDraft(extracted_text="Warung kecil. Buat modal. Naik.")


@pytest.fixture
def milestones_draft() -> list[MilestoneDraft]:
    return [
        MilestoneDraft(seq=1, title="Beli mesin kopi", amount=6_000_000),
        MilestoneDraft(seq=2, title="Bahan baku tiga bulan", amount=4_000_000),
    ]

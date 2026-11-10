"""Skema request/response untuk proposal dan rencana milestonenya (BR-10 sampai BR-18)."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.domain.transitions import PLEDGE_LOCKED_PROPOSAL_STATUSES
from app.domain.transitions import ProposalStatus as DomainProposalStatus
from app.models.campaign import Sector
from app.models.proposal import MilestoneStatus, ProposalStatus, ScoringStatus
from app.schemas.milestone import MilestoneReportOut


class ProposalSort(StrEnum):
    """Nilai sah untuk query `sort` di `GET /proposals` (10-api-contract.md:55).

    Enum, bukan string bebas: nilai yang tidak dikenal harus ditolak 422 di
    tepi, bukan diam-diam jatuh ke urutan default. Urutan default yang
    tersamar adalah cara halaman daftar berbohong tentang apa yang
    ditampilkannya.

    Empat nilai ini semuanya bisa dijawab dari data yang memang ada. Tidak
    ada "paling mendesak" atau "paling populer" di sini: proposal tidak punya
    tenggatnya sendiri (tenggat ada di campaign) dan tidak ada penghitung
    kunjungan, jadi mengurutkan dengan nama semacam itu berarti mengarang
    peringkat.
    """

    NEWEST = "newest"
    AMOUNT_DESC = "amount_desc"
    AMOUNT_ASC = "amount_asc"
    MOST_FUNDED = "most_funded"


class MilestoneIn(BaseModel):
    seq: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1)
    # Tidak dibatasi gt=0 di sini: nol dan negatif sengaja dibiarkan lolos ke
    # validate_milestone_plan (BR-16) supaya pesannya tetap pesan domain yang
    # menyebut selisih, bukan error bentuk payload yang generik.
    amount: int = Field(strict=True)


class ProposalIn(BaseModel):
    # Panjang sesuai form di 04-feature-umkm.md. Batas atas (review
    # keamanan: 5 MB lolos tanpa batas atas sebelum ini) dipilih longgar --
    # 5.000 karakter kira-kira satu-dua halaman, jauh lebih panjang dari
    # rencana bisnis UMKM mana pun yang wajar -- dan dipagari lagi di
    # database lewat CHECK (migrasi fase ini), bukan hanya di sini, karena
    # fixture test dan kode lain bisa menyusun Proposal langsung tanpa
    # pernah lewat ProposalIn.
    business_name: str = Field(min_length=3, max_length=120)
    business_profile: Annotated[str, Field(min_length=100, max_length=5_000)]
    # strict=True: tanpa itu Pydantic membulatkan nominal pecahan diam-diam.
    requested_amount: int = Field(strict=True, gt=0)
    fund_usage_plan: Annotated[str, Field(min_length=100, max_length=5_000)]
    business_projection: Annotated[str, Field(min_length=50, max_length=3_000)]
    # max_length=30 (jumlah tahap, bukan panjang teks): diulang sebagai
    # MAKSIMAL_MILESTONE di domain/milestone_plan.py untuk pemanggil yang
    # tidak lewat skema ini sama sekali (review keamanan: 50.000 item lolos
    # tanpa batas atas sebelum ini).
    milestones: Annotated[list[MilestoneIn], Field(max_length=30)]


def _tampilkan_lead_investor_id(
    status: ProposalStatus, lead_investor_id: UUID | None
) -> UUID | None:
    """10-api-contract.md:106-107: identitas investor (termasuk lead
    investor) tidak boleh terlihat sebelum proposal `funded` -- lead
    investor sendirian yang mengendalikan pencairan, dan melihat siapa
    unggul sebelum posisi settle cukup untuk sengaja menyaingi nominalnya
    (review keamanan). `PLEDGE_LOCKED_PROPOSAL_STATUSES` (domain/transitions.py)
    dipakai sebagai definisi "sudah settle", bukan {FUNDED, COMPLETED} yang
    dieja tangan di sini juga -- status hilir baru dari FUNDED otomatis ikut
    terbuka tanpa menyentuh berkas ini lagi, sama seperti alasannya dipakai
    di cancel_pledge (services/pledge.py)."""
    if DomainProposalStatus(status.value) in PLEDGE_LOCKED_PROPOSAL_STATUSES:
        return lead_investor_id
    return None


class ProposalOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    campaign_id: UUID
    umkm_id: UUID
    business_name: str
    business_profile: str
    fund_usage_plan: str
    business_projection: str
    requested_amount: int
    # BR-51, D-03: selalu dijumlahkan dari ledger (services/ledger.py), tidak
    # pernah disimpan sebagai kolom. Task 1: tanpa ini halaman proposal
    # publik (dibuka pengunjung tanpa akun, termasuk juri lewat tautan
    # bersama) tidak punya satu pun sumber progres funding, karena
    # GET /proposals/{id}/pledges mewajibkan investor atau pemilik.
    collected_amount: int
    status: ProposalStatus
    scoring_status: ScoringStatus
    lead_investor_id: UUID | None
    funded_at: datetime | None
    # None berarti proposal ini belum punya foto sampul. Bukan boolean
    # "punya sampul": waktunya sekaligus menjadi kunci cache pada URL gambar,
    # sehingga sampul yang diganti tidak tertutup versi lama di browser.
    cover_updated_at: datetime | None = None
    # Sektor campaign yang menaungi proposal ini. None hanya pada bentuk
    # keluaran yang belum mengambilnya (lihat services/proposal.py).
    sector: Sector | None = None
    created_at: datetime

    @model_validator(mode="after")
    def _redaksi_lead_investor(self) -> "ProposalOut":
        self.lead_investor_id = _tampilkan_lead_investor_id(
            self.status, self.lead_investor_id
        )
        return self


class ProposalListItemOut(BaseModel):
    """Proyeksi ringkas untuk GET /proposals (Task 4, publik, dipanggil
    landing page): tanpa business_profile/fund_usage_plan/business_projection.
    Review keamanan mengukur 7.2 MB untuk dua belas proposal seeded karena
    ketiga field itu ikut terbawa verbatim di endpoint daftar; rencana bisnis
    lengkap milik GET /proposals/{id}, bukan daftar."""

    model_config = {"from_attributes": True}

    id: UUID
    campaign_id: UUID
    umkm_id: UUID
    business_name: str
    # Cuplikan, bukan field penuh: kartu proposal di daftar memang menampilkan
    # ringkasan usaha, dan tanpa field ini kartunya kehilangan deskripsinya.
    # Dipotong di server supaya respons daftar tidak kembali membesar seiring
    # panjang rencana bisnis, yang justru alasan ketiga field panjang dibuang.
    business_profile_excerpt: str
    requested_amount: int
    collected_amount: int
    status: ProposalStatus
    scoring_status: ScoringStatus
    lead_investor_id: UUID | None
    funded_at: datetime | None
    # None berarti proposal ini belum punya foto sampul. Bukan boolean
    # "punya sampul": waktunya sekaligus menjadi kunci cache pada URL gambar,
    # sehingga sampul yang diganti tidak tertutup versi lama di browser.
    cover_updated_at: datetime | None = None
    # Sektor campaign yang menaungi proposal ini. None hanya pada bentuk
    # keluaran yang belum mengambilnya (lihat services/proposal.py).
    sector: Sector | None = None
    created_at: datetime

    @model_validator(mode="after")
    def _redaksi_lead_investor(self) -> "ProposalListItemOut":
        self.lead_investor_id = _tampilkan_lead_investor_id(
            self.status, self.lead_investor_id
        )
        return self


class ProposalListOut(BaseModel):
    """Bentuk paginasi GET /proposals (Task 4, perluasan kontrak di luar
    10-api-contract.md -- kontrak tidak menyebut paginasi sama sekali).
    `total` dihitung dari seluruh baris publik, bukan panjang `items`,
    supaya klien tahu ada halaman berikutnya tanpa menghitung sendiri."""

    items: list[ProposalListItemOut]
    total: int
    page: int
    page_size: int


class MilestoneOut(BaseModel):
    """GET /proposals/{id}/milestones (10-api-contract.md:73).

    `latest_report` adalah laporan **terbaru berdasarkan waktu dibuat**, bukan
    laporan terakhir yang bukan `rejected`: setelah sebuah laporan ditolak,
    revisinya ditulis sebagai baris baru (BR-46, lihat
    test_br46_rejected_report_kept_and_revision_is_new_row), dan baris lama
    tetap tersimpan apa adanya. Menyaring `rejected` di sini akan membuat
    pembaca endpoint ini melihat status basi -- laporan `pending` lama yang
    sudah ditolak dan digantikan, atau `None` di tengah jendela antara
    penolakan dan revisi berikutnya, padahal ada laporan `rejected` yang
    sebenarnya nyata dan perlu ditindaklanjuti UMKM. Semantik ini sama
    dengan `get_latest_report()` di services/milestone.py, yang dipakai
    approve_milestone dan reject_milestone untuk alasan yang sama."""

    model_config = {"from_attributes": True}

    id: UUID
    seq: int
    title: str
    description: str
    amount: int
    status: MilestoneStatus
    latest_report: MilestoneReportOut | None


class MilestoneListOut(BaseModel):
    items: list[MilestoneOut]


class ProposalWithSignalsOut(ProposalOut):
    """ProposalOut ditambah sinyal komunitas dan AI yang dipakai mengurutkan
    daftar proposal investor (10-api-contract.md: skor lalu vote lalu waktu
    submit). `total_score` 0 untuk proposal yang belum pernah dinilai,
    `vote_count` 0 untuk yang belum pernah divote -- keduanya hasil
    coalesce di query, bukan nilai yang pernah ditulis ke kolom manapun.
    """

    total_score: int
    vote_count: int


class ProposalWithSignalsListOut(BaseModel):
    items: list[ProposalWithSignalsOut]

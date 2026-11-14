"""Data seed demo untuk Modalink (Fase 13 Task 1, 10-api-contract.md:97).

`POST /api/v1/internal/seed` (terdaftar hanya saat ENV=dev, BR-63) dan
`python -m app.seed` (app/seed/__main__.py) keduanya memanggil
`seed_demo_data()` di bawah ini, bukan menyalin logikanya. Yang pertama
dipakai test lokal; yang kedua dipakai pemilik project sekali di server
produksi lewat `docker compose exec backend python -m app.seed`, karena
endpoint internal itu sendiri tidak pernah terdaftar di sana (lihat
peringatan di `.claude/plan/phase-13-submission.md`).

Akun demo di bawah ini publik dengan sengaja: repositori ini publik saat
submission, dan kredensial berikut hanya berlaku untuk akun contoh di
deployment demo, bukan akun sungguhan siapa pun. Password sama untuk
seluruh akun demo (`DEMO_PASSWORD`), pola yang sengaja dibuat mencolok
supaya siapa pun yang membacanya langsung tahu ini bukan kredensial
sungguhan. Domain emailnya (`.test`) dicadangkan IANA/RFC 2606 khusus untuk
pengujian dan tidak pernah bisa resolve ke domain nyata -- sinyal tambahan
di atas label "(Demo)" pada setiap nama.

Idempoten lewat satu pengecekan di depan: `seed_demo_data` hanya meng-commit
lewat pemanggilnya (endpoint atau __main__.py) kalau SELURUH langkah di
bawah berhasil tanpa exception, jadi investor pertama (`SEED_SENTINEL_EMAIL`)
ada di database hanya kalau seluruh proses sebelumnya pernah tuntas. Kalau ia
sudah ada, fungsi ini berhenti di baris itu saja tanpa menulis apa pun lagi,
bukan memeriksa setiap tabel satu per satu.

Enam proposal di bawah sengaja dibuat berbeda kualitas (lihat
app/ai/mock_engine.py untuk cara penanda [[SCORE:n]] dan [[RED_FLAG:level]]
dibaca): dua lolos dengan skor tinggi, satu pas di atas ambang, satu
ditolak karena skor rendah, dan satu ditolak karena red flag kritis
meski skornya sendiri tinggi -- supaya juri melihat AI membedakan kualitas,
bukan enam baris yang kebetulan semuanya mirip.
"""

import itertools
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.ai.mock_engine import MockScoringEngine
from app.domain.clock import Clock, SystemClock
from app.models.campaign import Campaign, Sector
from app.models.kyc import BankCode
from app.models.ledger import LedgerEntry
from app.models.pledge import Pledge
from app.models.proposal import Proposal, ProposalMilestone
from app.models.user import Role, User
from app.schemas.auth import RegisterIn
from app.schemas.campaign import CampaignIn
from app.schemas.kyc import KycIn
from app.schemas.proposal import MilestoneIn, ProposalIn
from app.seed.pdf import buat_pdf
from app.services.auth import register_user
from app.services.campaign import create_campaign
from app.services.community import create_comment, toggle_vote
from app.services.kyc import submit_kyc
from app.services.milestone import approve_milestone
from app.services.pledge import create_pledge, get_locked_proposal
from app.services.proposal import submit_proposal
from app.services.scoring import run_scoring

# Satu password untuk seluruh akun demo: lihat docstring modul ini soal
# alasannya sengaja identik dan mencolok, bukan disamarkan jadi kuat tapi acak.
DEMO_PASSWORD = "Demo#Modalink2026"

DEMO_EMAIL_DOMAIN = "demo.example.com"
SEED_SENTINEL_EMAIL = f"investor1@{DEMO_EMAIL_DOMAIN}"

# Dipakai test untuk menyaring baris yang benar-benar milik seed ini saja,
# bukan menghitung seluruh tabel: tests/integration/test_concurrent_approve.py
# sengaja commit sungguhan di luar savepoint (butuh koneksi konkuren nyata)
# dan baris itu bertahan di database test antar-run, jadi hitungan mentah per
# tabel tidak boleh dipakai untuk memastikan "seed ini membuat enam proposal".
SEEDED_BUSINESS_NAMES = (
    "Warung Kopi Mbak Sri",
    "Kerajinan Rotan Pak Dedi",
    "Katering Bu Yanti",
    "Bengkel Las Mas Tono",
    "Toko Kelontong Bu Imah",
    "Peternakan Lele Instan",
)
SEEDED_CAMPAIGN_TITLES = (
    "Modal Usaha Kuliner Rumahan Tahap 1",
    "Modal Usaha Mikro Tahap Kedua",
)

_ENGINE = MockScoringEngine()

# Ditempelkan ke setiap ringkasan DAN ke bagian terakhir setiap PDF, terpisah
# dari penanda mock engine di `proyeksi` (lihat _ProposalSpec di bawah): data
# buatan tidak apa-apa selama disebut apa adanya. Di dua tempat karena
# keduanya dibaca orang yang berbeda -- ringkasan terlihat di kartu daftar
# tanpa membuka apa pun, dokumen terlihat oleh yang sungguh membacanya.
_DISCLAIMER = (
    "Profil usaha ini adalah data contoh untuk demonstrasi Logicodix 2026, "
    "bukan usaha sungguhan."
)


@dataclass(frozen=True, slots=True)
class SeedResult:
    """Ringkasan hasil `seed_demo_data`, dipakai endpoint dan CLI untuk melapor."""

    sudah_pernah_disemai: bool
    jumlah_user: int
    jumlah_campaign: int
    jumlah_proposal: int
    jumlah_pledge: int
    jumlah_ledger_entry: int


async def _count(session: AsyncSession, model: type) -> int:
    return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def _summarize(session: AsyncSession, *, sudah_pernah: bool) -> SeedResult:
    return SeedResult(
        sudah_pernah_disemai=sudah_pernah,
        jumlah_user=await _count(session, User),
        jumlah_campaign=await _count(session, Campaign),
        jumlah_proposal=await _count(session, Proposal),
        jumlah_pledge=await _count(session, Pledge),
        jumlah_ledger_entry=await _count(session, LedgerEntry),
    )


# Nomor urut NIK demo. Satu NIK hanya boleh dipakai satu akun, jadi tiap
# akun demo butuh nomornya sendiri. Disusun agar lolos aturan bentuk di
# domain/identity.py: kode wilayah 320101, lahir 1 Januari 1990.
_URUT_NIK_DEMO = itertools.count(1)


async def _create_user(
    session: AsyncSession, email: str, name: str, role: Role, clock: Clock
) -> User:
    user = await register_user(
        session, RegisterIn(email=email, password=DEMO_PASSWORD, name=name, role=role)
    )
    # Investor dan UMKM demo ikut diverifikasi identitasnya, karena keduanya
    # TIDAK BISA menyentuh uang tanpa itu (gerbang di api/v1/proposals.py dan
    # api/v1/pledges.py). Tanpa langkah ini, juri yang masuk dengan akun demo
    # menemukan setiap tombol pendanaan menolaknya, dan demonstrasinya
    # berhenti di situ.
    #
    # Lewat submit_kyc sungguhan, bukan baris yang ditulis langsung ke tabel:
    # seluruh aturan bentuk ikut berlaku pada data demo, sama seperti data
    # mana pun.
    if role in {Role.INVESTOR, Role.UMKM}:
        urut = next(_URUT_NIK_DEMO)
        await submit_kyc(
            session,
            user,
            KycIn(
                full_name=name,
                nik=f"320101010190{urut:04d}",
                bank_code=BankCode.BCA,
                account_holder_name=name,
                account_number=f"12345{urut:05d}",
            ),
            clock,
        )
    return user


@dataclass(frozen=True, slots=True)
class _MilestoneSpec:
    title: str
    description: str
    amount: int


@dataclass(frozen=True, slots=True)
class _ProposalSpec:
    """Isi satu proposal demo.

    Ketiga bagian naratif (`profil_usaha`, `rencana_dana`, `proyeksi`) bukan
    lagi kolom di tabel proposals: ia dirangkai menjadi berkas PDF yang
    diunggah bersama proposalnya, karena itulah bentuk proposal sekarang.
    Dulu ketiganya kolom tersendiri, dan nama field di sini sengaja ikut
    berubah supaya tidak ada yang mengira kolom itu masih ada.

    `proyeksi` membawa penanda mock engine (lihat docstring modul) supaya
    skornya persis dan tidak berubah antar-pemutaran demo. Penanda itu ikut
    tercetak ke dalam PDF, dan MockScoringEngine membacanya dari teks yang
    diekstrak kembali dari berkas itu -- jalur yang sama persis dengan
    dokumen sungguhan.
    """

    owner: User
    business_name: str
    ringkasan: str
    profil_usaha: str
    rencana_dana: str
    proyeksi: str
    requested_amount: int
    milestones: Sequence[_MilestoneSpec]


async def _submit_and_score(
    session: AsyncSession, campaign: Campaign, spec: _ProposalSpec, clock: Clock
) -> Proposal:
    body = ProposalIn(
        business_name=spec.business_name,
        business_summary=f"{spec.ringkasan} {_DISCLAIMER}",
        requested_amount=spec.requested_amount,
        milestones=[
            MilestoneIn(
                seq=i + 1, title=m.title, description=m.description, amount=m.amount
            )
            for i, m in enumerate(spec.milestones)
        ],
    )
    dokumen = buat_pdf(
        f"Proposal Usaha {spec.business_name}",
        [
            ("Profil Usaha", spec.profil_usaha),
            ("Rencana Penggunaan Dana", spec.rencana_dana),
            ("Proyeksi Usaha", spec.proyeksi),
            ("Catatan", _DISCLAIMER),
        ],
    )
    proposal = await submit_proposal(
        session,
        spec.owner,
        campaign,
        body,
        dokumen,
        f"proposal-{spec.business_name.lower().replace(' ', '-')}.pdf",
        clock,
    )
    # Lewat orkestrasi sungguhan (run_scoring), bukan status yang
    # ditulis langsung: data demo harus tunduk pada aturan yang sama dengan
    # data produksi (BR-73), termasuk ScoringResult yang tercatat di baliknya.
    await run_scoring(session, proposal.id, _ENGINE, clock)
    await session.refresh(proposal)
    return proposal


def _proposal_specs(
    umkm1: User, umkm2: User, umkm3: User, umkm4: User
) -> tuple[list[_ProposalSpec], list[_ProposalSpec]]:
    """Enam proposal, dipisah per campaign tujuannya. Dua UMKM (umkm1, umkm2)
    masing-masing mengajukan proposal di kedua campaign: tidak melanggar BR-13
    (satu proposal aktif per UMKM per campaign) karena keduanya proposal itu
    ada di campaign yang berbeda, bukan campaign yang sama."""
    campaign1 = [
        _ProposalSpec(
            owner=umkm1,
            business_name="Warung Kopi Mbak Sri",
            ringkasan=(
                "Kedai kopi rumahan di Condongcatur, Sleman, tiga tahun "
                "berjalan, mencari modal untuk renovasi gerobak dan mesin "
                "seduh."
            ),
            profil_usaha=(
                "Warung Kopi Mbak Sri adalah kedai kopi rumahan di kawasan "
                "Condongcatur, Sleman, yang sudah berjalan selama tiga tahun "
                "dengan pelanggan tetap dari mahasiswa dan pekerja kantoran di "
                "sekitar kampus. Menu andalan adalah kopi susu gula aren dan "
                "camilan tradisional buatan sendiri."
            ),
            rencana_dana=(
                "Dana akan dipakai untuk merenovasi gerobak jualan agar lebih "
                "kokoh dan tahan cuaca, menambah satu mesin seduh espresso "
                "sederhana, serta membeli stok biji kopi dan gula aren untuk "
                "tiga bulan operasional pertama."
            ),
            proyeksi=(
                "Dengan peralatan baru dan jam buka yang lebih panjang, warung "
                "menargetkan kenaikan transaksi harian dari sekitar 60 menjadi "
                "90 cangkir dalam enam bulan ke depan. [[SCORE:82]]"
            ),
            requested_amount=15_000_000,
            milestones=[
                _MilestoneSpec(
                    "Renovasi gerobak dan peralatan seduh",
                    "Perbaikan gerobak jualan dan pembelian mesin seduh sederhana.",
                    7_000_000,
                ),
                _MilestoneSpec(
                    "Modal operasional tiga bulan",
                    "Pembelian stok biji kopi, gula aren, dan kemasan untuk "
                    "operasional tiga bulan.",
                    8_000_000,
                ),
            ],
        ),
        _ProposalSpec(
            owner=umkm2,
            business_name="Kerajinan Rotan Pak Dedi",
            ringkasan=(
                "Perajin rotan di Cirebon yang mengerjakan pesanan furnitur dan "
                "anyaman, mencari modal untuk bahan baku dan alat."
            ),
            profil_usaha=(
                "Kerajinan Rotan Pak Dedi memproduksi kursi dan keranjang "
                "anyaman rotan di sebuah bengkel kecil di pinggiran Cirebon, "
                "dikerjakan oleh empat pengrajin tetap. Produk dijual ke toko "
                "furnitur lokal dan lewat pesanan langsung dari tetangga "
                "sekitar."
            ),
            rencana_dana=(
                "Dana dipakai untuk membeli bahan rotan dan rangka kayu dalam "
                "jumlah lebih besar, serta menyewa tambahan tenaga kerja "
                "musiman untuk mempercepat produksi batch pertama pesanan "
                "besar."
            ),
            proyeksi=(
                "Dengan bahan baku yang cukup, bengkel ini menargetkan "
                "penyelesaian satu batch 40 unit kursi dalam dua bulan, "
                "dibanding kemampuan saat ini yang hanya 15 unit per bulan. "
                "[[SCORE:71]]"
            ),
            requested_amount=20_000_000,
            milestones=[
                _MilestoneSpec(
                    "Pembelian bahan rotan dan rangka",
                    "Pembelian bahan baku rotan dan rangka kayu untuk batch "
                    "produksi pertama.",
                    9_000_000,
                ),
                _MilestoneSpec(
                    "Produksi dan pengemasan batch pertama",
                    "Upah tenaga kerja musiman dan bahan pengemasan untuk "
                    "batch pertama.",
                    11_000_000,
                ),
            ],
        ),
        _ProposalSpec(
            owner=umkm3,
            business_name="Katering Bu Yanti",
            ringkasan=(
                "Katering rumahan untuk kantor dan acara keluarga di Semarang, "
                "mencari modal untuk peralatan dapur dan armada antar."
            ),
            profil_usaha=(
                "Katering Bu Yanti melayani pesanan nasi kotak dan tumpeng "
                "untuk acara kantor dan hajatan kecil di wilayah Bekasi, "
                "dengan dapur produksi di rumah sendiri dan dua karyawan "
                "tetap. Usaha ini sudah berjalan lebih dari lima tahun."
            ),
            rencana_dana=(
                "Dana dipakai membeli peralatan dapur berkapasitas lebih "
                "besar, menambah stok bahan baku untuk menerima pesanan dalam "
                "jumlah lebih banyak, serta menambah satu armada motor untuk "
                "pengantaran."
            ),
            proyeksi=(
                "Dengan peralatan dan armada tambahan, katering ini "
                "menargetkan kenaikan kapasitas pesanan dari 50 menjadi 120 "
                "kotak per hari untuk acara besar dalam waktu empat bulan. "
                "[[SCORE:66]]"
            ),
            requested_amount=30_000_000,
            milestones=[
                _MilestoneSpec(
                    "Peralatan dapur katering",
                    "Pembelian panci besar, kompor tambahan, dan rak penyimpanan.",
                    10_000_000,
                ),
                _MilestoneSpec(
                    "Bahan baku katering bulan pertama",
                    "Stok bahan baku untuk operasional bulan pertama dengan "
                    "kapasitas baru.",
                    10_000_000,
                ),
                _MilestoneSpec(
                    "Perluasan armada pengantaran",
                    "Pembelian satu unit motor untuk pengantaran pesanan.",
                    10_000_000,
                ),
            ],
        ),
        _ProposalSpec(
            owner=umkm4,
            business_name="Bengkel Las Mas Tono",
            ringkasan=(
                "Bengkel las pagar dan teralis di pinggiran Surabaya, "
                "dijalankan pemiliknya sendiri, mencari modal untuk mesin dan "
                "bahan."
            ),
            profil_usaha=(
                "Bengkel Las Mas Tono mengerjakan pagar, teralis, dan pesanan "
                "las custom untuk rumah tangga di kawasan pinggiran Surabaya. "
                "Bengkel ini dijalankan sendiri oleh pemiliknya dibantu satu "
                "asisten paruh waktu."
            ),
            rencana_dana=(
                "Dana dipakai untuk membeli mesin las dan alat potong besi "
                "yang lebih baik, serta menambah stok besi dan bahan baku "
                "agar bisa menerima pesanan dalam jumlah lebih banyak "
                "sekaligus."
            ),
            proyeksi=(
                "Dengan mesin yang lebih baik, waktu pengerjaan satu pesanan "
                "pagar rumah menurun dari lima hari menjadi tiga hari, "
                "memungkinkan lebih banyak pesanan diterima dalam sebulan. "
                "[[SCORE:61]]"
            ),
            requested_amount=12_000_000,
            milestones=[
                _MilestoneSpec(
                    "Mesin las dan alat potong",
                    "Pembelian mesin las baru dan alat potong besi.",
                    6_000_000,
                ),
                _MilestoneSpec(
                    "Stok besi dan bahan baku",
                    "Pembelian stok besi dan bahan baku pendukung lainnya.",
                    6_000_000,
                ),
            ],
        ),
    ]
    campaign2 = [
        _ProposalSpec(
            owner=umkm1,
            business_name="Toko Kelontong Bu Imah",
            ringkasan=(
                "Toko kelontong di permukiman padat Bekasi, mencari modal untuk "
                "menambah stok dan rak penyimpanan."
            ),
            profil_usaha=(
                "Toko Kelontong Bu Imah menjual sembako dan kebutuhan harian "
                "di sebuah kios kecil pinggir jalan kampung di Tasikmalaya. "
                "Toko ini baru berjalan beberapa bulan dan belum punya "
                "pencatatan keuangan yang rapi."
            ),
            rencana_dana=(
                "Dana rencananya dipakai untuk menambah rak dan etalase toko, "
                "serta menambah stok sembako awal agar barang dagangan tidak "
                "cepat kosong saat pembeli ramai."
            ),
            proyeksi=(
                "Belum ada perkiraan kenaikan penjualan yang jelas karena "
                "toko ini masih sangat baru dan pemiliknya belum pernah "
                "membuat proyeksi usaha sebelumnya. [[SCORE:48]]"
            ),
            requested_amount=8_000_000,
            milestones=[
                _MilestoneSpec(
                    "Rak dan etalase toko",
                    "Pembelian rak dan etalase tambahan untuk toko.",
                    4_000_000,
                ),
                _MilestoneSpec(
                    "Stok awal sembako", "Pembelian stok sembako awal.", 4_000_000
                ),
            ],
        ),
        _ProposalSpec(
            owner=umkm2,
            business_name="Peternakan Lele Instan",
            ringkasan=(
                "Usaha budidaya lele yang baru dirintis, mencari modal untuk "
                "kolam terpal dan bibit tahap pertama."
            ),
            profil_usaha=(
                "Peternakan Lele Instan mengelola delapan kolam terpal di "
                "pinggiran Kediri untuk membesarkan lele konsumsi, dengan "
                "hasil panen dijual ke pengepul dan warung pecel lele di "
                "sekitar kota. Usaha ini sudah berjalan dua tahun dengan "
                "hasil panen yang stabil setiap siklusnya."
            ),
            rencana_dana=(
                "Dana akan dipakai untuk membangun empat kolam terpal "
                "tambahan di lahan yang sudah tersedia, membeli bibit lele "
                "dalam jumlah besar untuk seluruh kolam baru dan kolam lama "
                "secara bersamaan, serta menyediakan pakan selama enam bulan "
                "penuh tanpa henti supaya seluruh kolam bisa langsung "
                "berproduksi tanpa menunggu siklus panen kolam lama selesai "
                "lebih dulu, termasuk perbaikan saluran air dan pompa "
                "sirkulasi agar kualitas air tetap terjaga sepanjang masa "
                "pembesaran."
            ),
            proyeksi=(
                "Dengan penambahan kolam ini, peternakan menargetkan hasil "
                "panen naik sepuluh kali lipat dalam tiga bulan dan setiap "
                "kolam dijanjikan selalu berhasil panen penuh tanpa kematian "
                "bibit sama sekali, baik pada musim kemarau maupun musim "
                "hujan, serta menjamin harga jual akan naik tiga kali lipat "
                "dalam waktu yang sama tanpa risiko penurunan permintaan dari "
                "pengepul maupun warung pecel lele langganan selama ini, "
                "sebuah proyeksi yang jauh di luar kewajaran siklus budidaya "
                "lele pada umumnya. [[RED_FLAG:critical]]"
            ),
            requested_amount=25_000_000,
            milestones=[
                _MilestoneSpec(
                    "Pembangunan kolam terpal tambahan",
                    "Pembangunan empat kolam terpal baru di lahan yang sudah tersedia.",
                    12_000_000,
                ),
                _MilestoneSpec(
                    "Bibit lele dan pakan enam bulan",
                    "Pembelian bibit lele dan pakan untuk enam bulan pembesaran.",
                    13_000_000,
                ),
            ],
        ),
    ]
    return campaign1, campaign2


async def seed_demo_data(
    session: AsyncSession, clock: Clock | None = None
) -> SeedResult:
    """Mengisi database dengan 3 investor, 4 UMKM, 2 campaign, dan 6 proposal
    dengan kualitas berbeda (10-api-contract.md:97).

    Tidak pernah menulis ledger atau status secara langsung: setiap pledge dan
    pencairan lewat `create_pledge`/`approve_milestone` sungguhan, supaya data
    demo tunduk pada invarian yang sama dengan data produksi (R2, R2b).
    """
    clock = clock or SystemClock()

    if await session.scalar(select(User).where(User.email == SEED_SENTINEL_EMAIL)):
        return await _summarize(session, sudah_pernah=True)

    investor1 = await _create_user(
        session, SEED_SENTINEL_EMAIL, "Hendra Wijaya (Demo)", Role.INVESTOR, clock
    )
    investor2 = await _create_user(
        session,
        f"investor2@{DEMO_EMAIL_DOMAIN}",
        "Maria Angelina (Demo)",
        Role.INVESTOR,
        clock,
    )
    investor3 = await _create_user(
        session,
        f"investor3@{DEMO_EMAIL_DOMAIN}",
        "Fajar Nugroho (Demo)",
        Role.INVESTOR,
        clock,
    )
    umkm1 = await _create_user(
        session, f"umkm1@{DEMO_EMAIL_DOMAIN}", "Dian Permata (Demo)", Role.UMKM, clock
    )
    umkm2 = await _create_user(
        session, f"umkm2@{DEMO_EMAIL_DOMAIN}", "Agus Setiawan (Demo)", Role.UMKM, clock
    )
    umkm3 = await _create_user(
        session, f"umkm3@{DEMO_EMAIL_DOMAIN}", "Eka Nurhayati (Demo)", Role.UMKM, clock
    )
    umkm4 = await _create_user(
        session,
        f"umkm4@{DEMO_EMAIL_DOMAIN}",
        "Bambang Prasetyo (Demo)",
        Role.UMKM,
        clock,
    )
    # Dua akun komunitas, dan keduanya memang dipakai di bawah untuk memberi
    # dukungan dan komentar.
    #
    # Sebelum ini seed tidak membuat satu pun akun komunitas, vote, maupun
    # komentar, sehingga juri yang membuka demo melihat SELURUH fitur
    # komunitas (05-feature-komunitas.md) dalam keadaan kosong: setiap
    # proposal tertulis "0 dukungan" dan "Belum ada yang berkomentar".
    # Mendaftar sendiri memang memperlihatkan alur pendaftaran, tapi ia tidak
    # mengisi layar yang sedang dinilai, dan pendaftaran sendiri dibatasi 5
    # per menit per IP.
    warga1 = await _create_user(
        session,
        f"warga1@{DEMO_EMAIL_DOMAIN}",
        "Nadia Safitri (Demo)",
        Role.COMMUNITY,
        clock,
    )
    warga2 = await _create_user(
        session,
        f"warga2@{DEMO_EMAIL_DOMAIN}",
        "Yoga Kurniawan (Demo)",
        Role.COMMUNITY,
        clock,
    )

    sekarang = clock.now()
    campaign1 = await create_campaign(
        session,
        investor1,
        CampaignIn(
            title="Modal Usaha Kuliner Rumahan Tahap 1",
            description=(
                "Campaign demo untuk mendanai usaha kuliner dan kerajinan "
                "rumahan skala mikro yang sudah berjalan namun butuh modal "
                "tambahan untuk tahap berikutnya. Seluruh proposal pada "
                "campaign ini adalah data contoh untuk Logicodix 2026, bukan "
                "transaksi sungguhan."
            ),
            sector=Sector.KULINER,
            target_amount=60_000_000,
            apply_deadline=sekarang + timedelta(days=45),
            funding_deadline=sekarang + timedelta(days=90),
            score_threshold=60,
        ),
        clock,
    )
    campaign2 = await create_campaign(
        session,
        investor2,
        CampaignIn(
            title="Modal Usaha Mikro Tahap Kedua",
            description=(
                "Campaign demo tahap kedua untuk usaha ritel dan peternakan "
                "skala rumahan. Seluruh proposal pada campaign ini adalah "
                "data contoh untuk Logicodix 2026, bukan transaksi "
                "sungguhan."
            ),
            sector=Sector.RITEL,
            target_amount=40_000_000,
            apply_deadline=sekarang + timedelta(days=45),
            funding_deadline=sekarang + timedelta(days=90),
            score_threshold=60,
        ),
        clock,
    )

    # Urutan sama dengan daftar di _proposal_specs: warung kopi,
    # kerajinan rotan, katering, bengkel las.
    spesifikasi_c1, spesifikasi_c2 = _proposal_specs(umkm1, umkm2, umkm3, umkm4)
    _, proposal_rotan, proposal_katering, _ = [
        await _submit_and_score(session, campaign1, spec, clock)
        for spec in spesifikasi_c1
    ]
    for spec in spesifikasi_c2:
        await _submit_and_score(session, campaign2, spec, clock)

    # P2 "Kerajinan Rotan Pak Dedi": satu pledge yang sengaja tidak menutup
    # seluruh dana (BR-20..BR-24), supaya proposal ini tetap partially_funded
    # dan juri bisa melanjutkan pledge-nya sendiri secara live saat demo.
    proposal_rotan = await get_locked_proposal(session, proposal_rotan.id)
    await create_pledge(session, investor3, proposal_rotan, 8_000_000, clock)

    # P3 "Katering Bu Yanti": dua investor menutup dana secara bersama-sama
    # (patungan) tepat pas (D-11/D-12), lalu lead investor (pledge terbesar)
    # menyetujui milestone pertama sehingga statusnya tetap funded dengan
    # satu tahap sudah cair, bukan proposal yang belum tersentuh sama sekali.
    proposal_katering = await get_locked_proposal(session, proposal_katering.id)
    await create_pledge(session, investor2, proposal_katering, 18_000_000, clock)
    proposal_katering = await get_locked_proposal(session, proposal_katering.id)
    await create_pledge(session, investor3, proposal_katering, 12_000_000, clock)

    milestone_pertama = await session.scalar(
        select(ProposalMilestone).where(
            ProposalMilestone.proposal_id == proposal_katering.id,
            ProposalMilestone.seq == 1,
        )
    )
    assert milestone_pertama is not None  # dijamin submit_proposal di atas
    await approve_milestone(session, milestone_pertama, investor2, clock)

    # Dukungan dan komentar komunitas. Hanya pada proposal yang memang sudah
    # terbuka untuk publik (BR-30..BR-34 lewat toggle_vote/create_comment,
    # bukan baris yang ditulis langsung ke tabel): proposal yang ditolak atau
    # masih dinilai tidak boleh punya keduanya.
    for warga in (warga1, warga2):
        await toggle_vote(session, warga, proposal_rotan)
    await toggle_vote(session, warga1, proposal_katering)

    await create_comment(
        session,
        warga1,
        proposal_rotan,
        "Anyaman rotannya rapi dan tahan lama. Kalau kapasitas produksinya "
        "naik, saya yakin permintaan dari luar kota bisa dilayani. (Komentar "
        "contoh untuk demonstrasi Logicodix 2026.)",
        clock,
    )
    await create_comment(
        session,
        warga2,
        proposal_rotan,
        "Sudah beberapa kali pesan di sini dan hasilnya konsisten. Semoga "
        "pendanaannya segera penuh. (Komentar contoh untuk demonstrasi "
        "Logicodix 2026.)",
        clock,
    )
    await create_comment(
        session,
        warga1,
        proposal_katering,
        "Rasa masakannya stabil untuk pesanan besar, itu yang paling sulit "
        "dijaga katering rumahan. (Komentar contoh untuk demonstrasi "
        "Logicodix 2026.)",
        clock,
    )

    return await _summarize(session, sudah_pernah=False)

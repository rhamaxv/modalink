"""Pledge, pembatalannya, dan penulis tunggal status funding (D-05).

`create_pledge` dan `cancel_pledge` selalu menerima proposal yang sudah
dikunci lewat `get_locked_proposal` (RF-1): tanpa itu dua pledge nyaris
bersamaan sama-sama membaca sisa dana yang sama dan sama-sama lolos.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.clock import Clock
from app.domain.funding import compute_funding_status, remaining_amount
from app.domain.lead_investor import PledgeRingkas, pick_lead_investor
from app.domain.money import format_rupiah
from app.domain.transitions import PLEDGE_LOCKED_PROPOSAL_STATUSES
from app.domain.transitions import ProposalEvent as DomainProposalEvent
from app.domain.transitions import ProposalStatus as DomainProposalStatus
from app.errors import ConflictError, NotFoundError, UnprocessableError
from app.models.campaign import Campaign
from app.models.ledger import EntryType
from app.models.pledge import Pledge, PledgeStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.user import User
from app.schemas.pledge import MIN_PLEDGE_AMOUNT
from app.services.ledger import catat_entri, total_terkumpul_proposal
from app.services.status import advance_proposal

# BR-20: hanya proposal pada status ini yang boleh menerima pledge baru.
FUNDABLE_PROPOSAL_STATUSES = {ProposalStatus.LISTED, ProposalStatus.PARTIALLY_FUNDED}

# compute_funding_status (app/domain/funding.py) mengembalikan status TARGET
# hasil hitungan murni dari jumlah dan waktu, bukan event -- ia tidak tahu
# apa-apa soal status proposal SAAT INI. recompute_funding_status di bawah
# menerjemahkannya balik jadi event supaya tetap bisa lewat advance_proposal
# (lihat penjelasan panjang di badan fungsi). Hanya empat target yang pernah
# dihasilkan compute_funding_status: REJECTED, SUBMITTED, dan COMPLETED bukan
# bagian dari hitungan ini sama sekali.
_FUNDING_EVENT_FOR: dict[DomainProposalStatus, DomainProposalEvent] = {
    DomainProposalStatus.LISTED: DomainProposalEvent.PLEDGE_KOSONG,
    DomainProposalStatus.PARTIALLY_FUNDED: DomainProposalEvent.PLEDGE_SEBAGIAN,
    DomainProposalStatus.FUNDED: DomainProposalEvent.PLEDGE_PENUH,
    DomainProposalStatus.FAILED: DomainProposalEvent.DEADLINE_LEWAT,
}


async def get_locked_proposal(session: AsyncSession, proposal_id: UUID) -> Proposal:
    """Mengunci baris proposal sampai transaksi selesai (RF-1, RF-4, RF-5).

    Setiap operasi yang membaca lalu menulis uang pada satu proposal wajib
    lewat sini, bukan `session.get(Proposal, ...)`. Tanpa `FOR UPDATE`, dua
    request bersamaan sama-sama membaca sisa yang sama lalu sama-sama lolos
    (lihat tests/unit/test_proposal_lock_guard.py dan test_rf1_* di
    tests/integration/test_pledge_concurrency.py).
    """
    proposal = await session.scalar(
        select(Proposal).where(Proposal.id == proposal_id).with_for_update()
    )
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return proposal


async def get_pledge(session: AsyncSession, pledge_id: UUID) -> Pledge | None:
    """Pledge tunggal lewat PK, dipakai dependency kepemilikan di api/deps.py.

    Bukan Proposal, jadi tidak kena pagar tests/unit/test_proposal_lock_guard.py:
    pledge tidak pernah dikunci sendiri, locking selalu lewat baris proposal
    induknya di get_locked_proposal.
    """
    return await session.get(Pledge, pledge_id)


async def create_pledge(
    session: AsyncSession,
    investor: User,
    proposal: Proposal,
    amount: int,
    clock: Clock,
) -> Pledge:
    """Mencatat pledge baru dan menghitung ulang status funding (BR-20 sampai
    BR-24, BR-27, D-11, D-12). `proposal` wajib hasil `get_locked_proposal`."""
    if amount < MIN_PLEDGE_AMOUNT:
        # BR-27: schemas/pledge.py sudah menolak ini di 422 lewat PledgeIn,
        # tapi itu hanya menjaga pintu HTTP. Pemanggil lain (test, job batch,
        # service lain yang menyusun Pledge tanpa lewat router) bisa
        # melewatinya sama sekali. CLAUDE.md aturan 1 melarang aturan uang
        # hanya benar di satu pintu, jadi diulang di sini.
        raise UnprocessableError(
            "pledge_di_bawah_minimum",
            f"Pledge minimal {format_rupiah(MIN_PLEDGE_AMOUNT)}.",
            detail={"minimal_amount": MIN_PLEDGE_AMOUNT},
        )

    if proposal.status not in FUNDABLE_PROPOSAL_STATUSES:
        # Brief task ini hanya menyebut pemeriksaan sisa dana (D-11); tanpa
        # pagar ini, proposal submitted yang belum lolos scoring bisa
        # langsung melompat ke partially_funded lewat recompute_funding_status
        # di bawah, melanggar BR-20.
        remaining = remaining_amount(
            await total_terkumpul_proposal(session, proposal.id),
            proposal.requested_amount,
        )
        raise ConflictError(
            "proposal_belum_bisa_didanai",
            "Proposal ini belum bisa menerima pledge.",
            detail={
                "current_status": proposal.status.value,
                "remaining_amount": remaining,
            },
        )

    # BR-61/BR-62: funding_deadline campaign bisa saja sudah lewat padahal
    # proposal.status masih LISTED/PARTIALLY_FUNDED di baris ini -- evaluasi
    # lazy penuh belum ada (Fase 09), dan satu-satunya tempat yang pernah
    # menghitung ulang status terhadap deadline adalah recompute_funding_status
    # di bawah, SETELAH pledge baru ditulis. Menerima pledge dulu lalu
    # memaksa-refund-nya balik lewat recompute bukan "menolak": itu membuat
    # entri pledge_in yang hidup sepersekian detik sebelum ikut direfund, dan
    # investor tetap menerima 201 untuk pledge yang sebenarnya gagal (review
    # f06-b Finding 1). Dicek eksplisit di sini supaya tidak ada satu baris
    # pun ditulis untuk pledge yang pasti akan dibatalkan sendiri.
    campaign = await session.get(Campaign, proposal.campaign_id)
    if campaign is None:
        raise RuntimeError(
            f"Proposal {proposal.id} merujuk campaign yang tidak ada: "
            f"{proposal.campaign_id}."
        )
    if clock.now() >= campaign.funding_deadline:
        raise ConflictError(
            "pendanaan_sudah_ditutup",
            "Periode pendanaan proposal ini sudah berakhir sebelum pledge ini masuk.",
            detail={"current_status": ProposalStatus.FAILED.value},
        )

    remaining = remaining_amount(
        await total_terkumpul_proposal(session, proposal.id), proposal.requested_amount
    )
    if amount > remaining:
        raise ConflictError(
            "pledge_melebihi_sisa",
            f"Pledge melebihi sisa dana yang dibutuhkan, sisa {format_rupiah(remaining)}.",
            detail={"remaining_amount": remaining},
        )

    pledge = Pledge(
        proposal_id=proposal.id,
        investor_id=investor.id,
        amount=amount,
        status=PledgeStatus.ACTIVE,
        created_at=clock.now(),
    )
    session.add(pledge)
    await session.flush()

    await catat_entri(
        session,
        proposal.id,
        EntryType.PLEDGE_IN,
        amount,
        idempotency_key=f"pledge:{pledge.id}",
        clock=clock,
        ref_type="pledge",
        ref_id=pledge.id,
        actor_id=investor.id,
    )
    await recompute_funding_status(session, proposal, clock)
    return pledge


async def cancel_pledge(
    session: AsyncSession, proposal: Proposal, pledge: Pledge, clock: Clock
) -> Pledge:
    """Membatalkan pledge: mencatat refund, bukan menghapus (BR-25, BR-26).
    `proposal` wajib hasil `get_locked_proposal` dan harus proposal pemilik
    `pledge` (pemanggil yang menjamin pasangan ini benar).

    `pledge` sendiri dibaca di luar lock proposal (api/deps.py `get_own_pledge`
    memanggil `get_pledge`, bukan `get_locked_proposal`), jadi pengecekan
    `pledge.status is not ACTIVE` di bawah membaca snapshot yang bisa basi:
    dua pembatalan hampir bersamaan pada pledge yang sama bisa-bisa keduanya
    lolos pengecekan itu. Yang sebenarnya menutup balapan itu bukan lock
    baris proposal -- pledge memang tidak pernah dikunci sendiri -- melainkan
    idempotency_key `refund:{pledge.id}` di `catat_entri`: kalau keduanya
    lolos, keduanya sama-sama mencoba INSERT ledger dengan kunci yang sama,
    dan yang kedua kalah lewat unique constraint, bukan lewat baris Python
    ini. Window ini sudah dicoba dipaksa lewat forced interleaving 0.4 detik
    dan gagal direproduksi, justru karena pagar idempotensi itu yang menahan
    (review f06-b Finding 1)."""
    # BR-25, review Finding 1: menolak hanya status FUNDED secara harfiah
    # lolos begitu proposal maju ke completed (T-09 ada SETELAH funded, dan
    # tidak pernah tertutup kembali). PLEDGE_LOCKED_PROPOSAL_STATUSES adalah
    # closure dari PROPOSAL_MAP mulai dari FUNDED, bukan {FUNDED, COMPLETED}
    # yang dieja tangan, supaya status baru yang ditambahkan sebagai hilir
    # dari FUNDED otomatis ikut terkunci tanpa menyentuh baris ini lagi.
    if DomainProposalStatus(proposal.status.value) in PLEDGE_LOCKED_PROPOSAL_STATUSES:
        raise ConflictError(
            "proposal_sudah_funded",
            "Pledge tidak bisa dibatalkan karena proposal sudah funded.",
            detail={"current_status": proposal.status.value},
        )
    if pledge.status is not PledgeStatus.ACTIVE:
        raise ConflictError(
            "pledge_sudah_batal",
            "Pledge ini sudah dibatalkan sebelumnya.",
        )

    # Assignment langsung, bukan lewat domain/transitions.py: PledgeStatus
    # bukan satu dari empat mesin status terpusat (proposal, milestone,
    # laporan, campaign), hanya status dua nilai tanpa matriks transisi.
    pledge.status = PledgeStatus.CANCELLED
    session.add(pledge)
    await session.flush()

    await catat_entri(
        session,
        proposal.id,
        EntryType.REFUND_OUT,
        pledge.amount,
        idempotency_key=f"refund:{pledge.id}",
        clock=clock,
        ref_type="pledge",
        ref_id=pledge.id,
        actor_id=pledge.investor_id,
    )
    await recompute_funding_status(session, proposal, clock)
    return pledge


async def recompute_funding_status(
    session: AsyncSession, proposal: Proposal, clock: Clock
) -> None:
    """Satu-satunya penulis status funding yang didorong pledge: `listed`,
    `partially_funded`, `funded`, dan `failed` lewat deadline (D-05, BR-62).

    Bukan satu-satunya penulis `proposal.status` secara keseluruhan: T-01
    (`submitted` -> `listed` saat scoring lolos, lihat
    `services/scoring.py:_majukan_proposal`) adalah pelistingan awal, bukan
    akibat pledge, dan sengaja tidak lewat sini. Service yang mengubah pledge
    wajib memanggil fungsi ini di transaksi yang sama. Regression test R2b
    yang menegakkannya.

    Kalau hasilnya `failed`, BR-62 mewajibkan SELURUH pledge aktif yang masih
    tersisa ikut dibatalkan dengan `refund_out` di transaksi yang sama, bukan
    hanya pledge yang memicu pemanggilan ini. Alasannya: create_pledge
    menolak pledge baru begitu deadline lewat (lihat pengecekan di atas),
    tapi cancel_pledge tidak bisa ikut menolak pembatalan yang sah milik
    investor lain -- kalau proposal ini berubah jadi `failed` gara-gara satu
    pembatalan, pledge investor lain yang masih aktif tidak boleh
    ditinggalkan tanpa refund_out hanya karena bukan dia yang membatalkan.
    Direproduksi persis begini oleh review f06-b Finding 1: batalkan satu
    pledge setelah funding_deadline lewat sementara pledge investor lain
    masih aktif, proposal jadi `failed`, dan pledge investor lain itu tetap
    `active` selamanya tanpa satu pun entri lawan. Menunggu evaluasi lazy
    penuh (Fase 09, yang belum ada) bukan pilihan di sini: fungsi inilah
    satu-satunya titik tulis yang melihat transisi ke `failed` terjadi
    sekarang, lewat jalur yang sudah ada.
    """
    aktif = (
        await session.scalars(
            select(Pledge).where(
                Pledge.proposal_id == proposal.id,
                Pledge.status == PledgeStatus.ACTIVE,
            )
        )
    ).all()

    campaign = await session.get(Campaign, proposal.campaign_id)
    if campaign is None:
        # Praktis mustahil: proposal.campaign_id adalah foreign key yang
        # menjamin keberadaannya. Dianggap sebagai pelanggaran invarian, bukan
        # kondisi yang perlu diterjemahkan jadi DomainError, karena tidak ada
        # pemanggil yang bisa memulihkan diri darinya.
        raise RuntimeError(
            f"Proposal {proposal.id} merujuk campaign yang tidak ada: "
            f"{proposal.campaign_id}."
        )

    total = sum(p.amount for p in aktif)

    baru = compute_funding_status(
        total, proposal.requested_amount, clock.now(), campaign.funding_deadline
    )
    # Dulu baris ini adalah `proposal.status = ProposalStatus(baru.value)`
    # langsung (review Finding 1b). compute_funding_status murni menghitung
    # dari jumlah dan waktu -- ia tidak tahu, dan tidak BISA tahu, status
    # proposal ini SEKARANG. Begitu proposal sudah completed dan seluruh
    # pledge-nya dibatalkan satu-satu (lewat jalur yang semestinya sudah
    # ditolak BR-25 di cancel_pledge di atas), total jadi 0 dan fungsi ini
    # menghitung "listed", yang lalu ditimpa langsung ke kolom status tanpa
    # pernah bertanya pada PROPOSAL_MAP apakah completed->listed itu sah.
    # Jawabannya tidak, tapi assignment langsung tidak pernah bertanya.
    #
    # Rute lewat advance_proposal, bukan menambah pengecualian status
    # terminal di sini: PROPOSAL_MAP sudah satu-satunya sumber kebenaran
    # transisi (D-04), dan dari FUNDED atau COMPLETED tidak ada satu pun
    # event pledge yang terdaftar di sana. advance_proposal akan melempar
    # IllegalTransition kalau baris ini pernah dipanggil saat status sudah
    # terkunci -- dibiarkan menjalar, bukan diredam, karena pemanggil yang
    # sah (create_pledge lewat FUNDABLE_PROPOSAL_STATUSES, cancel_pledge
    # lewat PLEDGE_LOCKED_PROPOSAL_STATUSES) seharusnya sudah menutup jalan
    # ke sini sebelum fungsi ini pernah dipanggil; kalau masih sampai sini,
    # itu pelanggaran invarian yang harus meledak, bukan status yang salah
    # dan diam-diam tersimpan.
    baru_model = ProposalStatus(baru.value)
    if baru_model != proposal.status:
        advance_proposal(proposal, _FUNDING_EVENT_FOR[baru])

    if proposal.status is ProposalStatus.FAILED:
        for p in aktif:
            p.status = PledgeStatus.CANCELLED
            session.add(p)
            await catat_entri(
                session,
                proposal.id,
                EntryType.REFUND_OUT,
                p.amount,
                idempotency_key=f"refund:{p.id}",
                clock=clock,
                ref_type="pledge",
                ref_id=p.id,
                actor_id=p.investor_id,
            )
        aktif = []  # sudah seluruhnya direfund; lead investor jadi None di bawah

    proposal.lead_investor_id = pick_lead_investor(
        [PledgeRingkas(p.investor_id, p.amount, p.created_at) for p in aktif]
    )
    if proposal.status is ProposalStatus.FUNDED and proposal.funded_at is None:
        proposal.funded_at = clock.now()
    await session.flush()


@dataclass(frozen=True, slots=True)
class PledgeAktifDenganLeadMarker:
    """Bentuk siap-serialisasi untuk GET /proposals/{id}/pledges
    (10-api-contract.md:67). Bukan Pledge langsung: SQLModel menolak atribut
    bebas (lihat ProposalWithPledge di tests/conftest.py untuk alasan yang
    sama), dan is_lead_investor bukan kolom tabel sama sekali, hanya
    perbandingan terhadap proposal.lead_investor_id yang satu-satunya
    penulisnya recompute_funding_status di atas.

    `investor_id` None sebelum proposal `funded` (10-api-contract.md:106-107,
    Task 2 review keamanan): endpoint ini terbuka untuk investor manapun,
    bukan hanya yang sudah pledge, dan lead investor sendirian yang
    mengendalikan pencairan begitu posisi settle -- melihat siapa unggul dan
    berapa nominalnya sebelum itu cukup untuk sengaja menyaingi pledge-nya.
    `amount` dan `is_lead_investor` tetap tampil apa adanya: keduanya
    informasi publik yang sah (bilah progres, penanda lead), bukan
    identitas."""

    id: UUID
    proposal_id: UUID
    investor_id: UUID | None
    amount: int
    status: PledgeStatus
    created_at: datetime
    is_lead_investor: bool


async def daftar_pledge_aktif(
    session: AsyncSession, proposal: Proposal
) -> list[PledgeAktifDenganLeadMarker]:
    """Hanya pledge aktif (BR-20 sampai BR-26, 10-api-contract.md:67): yang
    sudah dibatalkan tidak pernah muncul di sini, beda dari riwayat penuh."""
    aktif = (
        await session.scalars(
            select(Pledge)
            .where(
                Pledge.proposal_id == proposal.id,
                Pledge.status == PledgeStatus.ACTIVE,
            )
            .order_by(desc("created_at"), desc("id"))
        )
    ).all()
    # PLEDGE_LOCKED_PROPOSAL_STATUSES (bukan {FUNDED} yang dieja tangan):
    # closure yang sama persis dipakai cancel_pledge di atas untuk "posisi
    # sudah settle", jadi status hilir baru dari FUNDED otomatis ikut
    # membuka identitas tanpa menyentuh baris ini lagi.
    identitas_boleh_tampil = (
        DomainProposalStatus(proposal.status.value) in PLEDGE_LOCKED_PROPOSAL_STATUSES
    )
    return [
        PledgeAktifDenganLeadMarker(
            id=p.id,
            proposal_id=p.proposal_id,
            investor_id=p.investor_id if identitas_boleh_tampil else None,
            amount=p.amount,
            status=p.status,
            created_at=p.created_at,
            is_lead_investor=p.investor_id == proposal.lead_investor_id,
        )
        for p in aktif
    ]

"""Evaluasi kedaluwarsa pendanaan secara lazy, dan refund simulasinya (D-06, BR-61, BR-62).

Tidak ada scheduler: transisi ke `failed` dihitung saat proposal (atau daftar
proposal milik sebuah campaign) dibaca, bukan oleh job terjadwal. Pola yang
sama dipakai `ambil_campaign_detail` di services/campaign.py untuk
`apply_deadline` (T-41); modul ini melakukan hal yang sama untuk
`funding_deadline`, ditambah refund yang BR-62 wajibkan begitu transisi ke
`failed` terjadi.
"""

from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.domain.clock import Clock
from app.domain.transitions import ProposalEvent
from app.models.campaign import Campaign
from app.models.ledger import EntryType
from app.models.pledge import Pledge, PledgeStatus
from app.models.proposal import Proposal, ProposalStatus
from app.services.ledger import catat_entri
from app.services.pledge import get_locked_proposal
from app.services.status import advance_proposal

AKTIF = {ProposalStatus.LISTED, ProposalStatus.PARTIALLY_FUNDED}

# FAILED ikut diperiksa, dan ini bukan kehati-hatian berlebihan. Pledge bisa
# masuk atau dibatalkan tepat setelah funding_deadline lewat; recompute_funding_status
# langsung menulis failed, dan pledge aktifnya tertinggal tanpa refund_out kalau
# jalur itu sendiri gagal menuntaskannya (lihat juga catatan di
# services/pledge.py:recompute_funding_status). Kalau fungsi ini menyaring
# status saja lewat AKTIF, proposal yang sudah failed semacam itu dilewati
# selamanya dan uang investor lain tidak pernah kembali (BR-62).
PERLU_REKONSILIASI = AKTIF | {ProposalStatus.FAILED}


async def evaluasi_kedaluwarsa(
    session: AsyncSession, proposal: Proposal, clock: Clock
) -> None:
    """Dipanggil di awal setiap pembacaan proposal, baik satu proposal maupun
    daftar (D-06, BR-61).

    Idempoten: kunci idempotensi refund_out berasal dari pledge
    (`refund:{pledge_id}`), jadi pembacaan berulang terhadap proposal yang
    sudah selesai direkonsiliasi tidak menghasilkan entri ganda -- begitu
    seluruh pledge aktifnya sudah `cancelled`, baris `aktif` di bawah kosong
    dan badan loop tidak pernah berjalan lagi.
    """
    if proposal.status not in PERLU_REKONSILIASI:
        return

    campaign = await session.get(Campaign, proposal.campaign_id)
    if campaign is None or clock.now() < campaign.funding_deadline:
        return

    if proposal.status is ProposalStatus.FAILED:
        # Review keamanan, hal yang murah: begitu proposal FAILED, himpunan
        # pledge aktifnya hanya bisa menyusut, tidak pernah bertambah lagi --
        # create_pledge menolak proposal FAILED (FUNDABLE_PROPOSAL_STATUSES),
        # dan satu-satunya arah pledge adalah ACTIVE -> CANCELLED, tidak
        # pernah sebaliknya. Jadi "nol pledge aktif sekarang" pada proposal
        # FAILED tidak akan pernah menjadi bukan-nol di pembacaan berikutnya,
        # dan baris ini aman melewati FOR UPDATE sama sekali tanpa kehilangan
        # satu pun rekonsiliasi yang BR-62 wajibkan: tidak ada apa pun yang
        # perlu direkonsiliasi. Tanpa ini, setiap GET daftar publik mengambil
        # lock dan flush untuk setiap proposal FAILED yang sudah lama tuntas.
        ada_pledge_aktif = await session.scalar(
            select(func.count())
            .select_from(Pledge)
            .where(
                Pledge.proposal_id == proposal.id, Pledge.status == PledgeStatus.ACTIVE
            )
        )
        if not ada_pledge_aktif:
            return

    # Pemeriksaan pertama di atas memakai `proposal` yang bisa saja belum
    # terkunci (pemanggil di router hanya membacanya lewat ambil_proposal()).
    # Baris di bawah ini mengunci baris yang sama lalu membaca ulang
    # statusnya: kalau transaksi lain (request pledge/cancel yang hampir
    # bersamaan) sudah mengubahnya di antara pemeriksaan pertama dan baris
    # ini, keputusan harus dibuat dari keadaan terbaru, bukan dari snapshot
    # yang sudah basi.
    terkunci = await get_locked_proposal(session, proposal.id)
    if terkunci.status not in PERLU_REKONSILIASI:
        return  # transaksi lain sudah mengurusnya sebelum baris ini terkunci

    aktif = (
        await session.scalars(
            select(Pledge).where(
                Pledge.proposal_id == terkunci.id,
                Pledge.status == PledgeStatus.ACTIVE,
            )
        )
    ).all()
    for p in aktif:
        p.status = PledgeStatus.CANCELLED
        await catat_entri(
            session,
            terkunci.id,
            EntryType.REFUND_OUT,
            p.amount,
            idempotency_key=f"refund:{p.id}",
            clock=clock,
            ref_type="pledge",
            ref_id=p.id,
            actor_id=p.investor_id,
        )

    if terkunci.status in AKTIF:
        # Belum pernah ditulis failed lewat jalur mana pun (kasus normal:
        # listed/partially_funded yang baru sekarang melewati deadline).
        # Proposal yang sudah failed sebelum baris ini (kasus BR-62 di atas)
        # tidak butuh transisi lagi, hanya pledge yang tertinggal.
        advance_proposal(terkunci, ProposalEvent.DEADLINE_LEWAT)
    await session.flush()


async def evaluasi_kedaluwarsa_banyak(
    session: AsyncSession, proposals: Sequence[Proposal], clock: Clock
) -> None:
    """Merekonsiliasi kedaluwarsa untuk satu HALAMAN daftar publik anonim
    (`daftar_proposal_publik`, `daftar_proposal_campaign`) -- review
    keamanan Finding 1.

    Locking per proposal lewat `evaluasi_kedaluwarsa` di atas sudah benar
    dan perlu (BR-62 wajib mengunci baris sebelum menulis refund). Yang
    salah bukan locking itu sendiri, melainkan URUTANNYA: daftar_proposal_publik
    menampilkan proposal created_at DESC lalu id DESC, daftar_proposal_campaign
    menampilkan total_score DESC lalu vote_count DESC lalu created_at lalu id.
    Dua proposal kedaluwarsa yang sama bisa muncul berurutan terbalik di dua
    daftar itu, dan dua request anonim bersamaan yang masing-masing mengunci
    sesuai urutan TAMPIL-nya lalu saling mengunci berlawanan arah -- Postgres
    mendeteksi siklus tunggu itu sebagai `40P01 deadlock detected` dan
    mengabort salah satunya, yang bocor ke pemanggil sebagai 500 (terukur:
    12 dari 24 request anonim bersamaan gagal sebelum perbaikan ini, lihat
    tests/integration/test_expiry_listing_deadlock.py).

    Perbaikannya memisahkan urutan TAMPIL dari urutan KUNCI. Fungsi ini
    menyaring dulu proposal mana yang benar-benar butuh rekonsiliasi (murni
    baca status di memori, tanpa query atau lock tambahan -- proposal yang
    sudah lolos dari evaluasi sebelumnya tidak disentuh sama sekali), lalu
    mengunci SISANYA dalam urutan primary key menaik, bukan urutan tampil
    endpoint yang memanggilnya. Apa pun endpoint pemanggilnya dan apa pun
    urutan tampilnya, dua transaksi yang hendak merekonsiliasi proposal yang
    sama akan selalu mencoba mengunci dalam urutan menaik yang sama persis.
    Urutan locking yang sama tidak pernah membentuk siklus tunggu, jadi
    tidak ada lagi apa pun untuk dideteksi Postgres sebagai deadlock --
    transaksi kedua hanya menunggu baris yang sama selesai dipakai transaksi
    pertama, lalu lanjut, persis seperti dua request berurutan.
    """
    kandidat = sorted(
        (p for p in proposals if p.status in PERLU_REKONSILIASI), key=lambda p: p.id
    )
    for p in kandidat:
        await evaluasi_kedaluwarsa(session, p, clock)

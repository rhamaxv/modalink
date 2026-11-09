"""Evaluasi kedaluwarsa pendanaan secara lazy, dan refund simulasinya (D-06, BR-61, BR-62).

Tidak ada scheduler: transisi ke `failed` dihitung saat proposal (atau daftar
proposal milik sebuah campaign) dibaca, bukan oleh job terjadwal. Pola yang
sama dipakai `ambil_campaign_detail` di services/campaign.py untuk
`apply_deadline` (T-41); modul ini melakukan hal yang sama untuk
`funding_deadline`, ditambah refund yang BR-62 wajibkan begitu transisi ke
`failed` terjadi.
"""

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

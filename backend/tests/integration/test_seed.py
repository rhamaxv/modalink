"""POST /internal/seed: data demo jujur dan idempoten (Fase 13 Task 1,
10-api-contract.md:97).

Setiap test di sini memanggil endpoint HTTP, bukan `seed_demo_data` langsung,
supaya jalur yang diuji sama persis dengan jalur yang dipakai test lokal
sungguhan: endpoint internal hanya membungkus fungsi itu (lihat
app/seed/demo.py), bukan menyalin logikanya.

Pemilihan baris di bawah selalu disaring lewat `SEEDED_BUSINESS_NAMES` /
`DEMO_EMAIL_DOMAIN`, bukan `select(Model)` mentah: tests/integration/
test_concurrent_approve.py sengaja commit sungguhan di luar savepoint (butuh
koneksi konkuren nyata untuk menguji penguncian baris), dan baris itu
bertahan di database test antar-run test suite. Menghitung seluruh tabel di
sini akan rapuh terhadap residu itu, bukan menguji seed-nya sendiri.
"""

from typing import Any

from sqlalchemy import desc, func, select

from app.models.campaign import Campaign
from app.models.ledger import EntryType, LedgerEntry
from app.models.pledge import Pledge
from app.models.proposal import Proposal, ProposalMilestone, ProposalStatus
from app.models.scoring import ScoringResult
from app.models.user import Role, User
from app.seed.demo import DEMO_EMAIL_DOMAIN, SEEDED_BUSINESS_NAMES
from app.services.ledger import hitung_saldo, total_terkumpul


async def _jumlah_baris(db, model: type) -> int:
    return await db.scalar(select(func.count()).select_from(model))


async def _proposal_seed(db) -> list[Proposal]:
    hasil = await db.scalars(
        select(Proposal).where(Proposal.business_name.in_(SEEDED_BUSINESS_NAMES))
    )
    return list(hasil)


async def test_seed_creates_three_investors_four_umkm_two_campaigns_and_six_proposals(
    client, db
):
    res = await client.post("/api/v1/internal/seed")
    assert res.status_code == 200

    investor = (
        await db.scalars(
            select(User).where(
                User.role == Role.INVESTOR,
                User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"),
            )
        )
    ).all()
    umkm = (
        await db.scalars(
            select(User).where(
                User.role == Role.UMKM, User.email.like(f"%@{DEMO_EMAIL_DOMAIN}")
            )
        )
    ).all()
    assert len(investor) == 3
    assert len(umkm) == 4

    campaign = (
        await db.scalars(
            select(Campaign).where(Campaign.investor_id.in_([u.id for u in investor]))
        )
    ).all()
    assert len(campaign) == 2

    proposal = await _proposal_seed(db)
    assert len(proposal) == 6


async def test_seed_covers_listed_partially_funded_funded_and_rejected_statuses(
    client, db
):
    await client.post("/api/v1/internal/seed")
    status_terpakai = {p.status for p in await _proposal_seed(db)}
    assert status_terpakai == {
        ProposalStatus.LISTED,
        ProposalStatus.PARTIALLY_FUNDED,
        ProposalStatus.FUNDED,
        ProposalStatus.REJECTED,
    }


async def test_seed_rejects_one_proposal_for_low_score_and_one_for_critical_red_flag(
    client, db
):
    """Dua proposal ditolak karena alasan berbeda (lihat tabel di
    app/seed/demo.py): satu karena skornya di bawah ambang, satu karena red
    flag kritis meski skornya sendiri tinggi -- dua jalur penolakan yang
    berbeda, bukan satu jalur yang kebetulan terjadi dua kali."""
    await client.post("/api/v1/internal/seed")
    ditolak = [
        p for p in await _proposal_seed(db) if p.status is ProposalStatus.REJECTED
    ]
    assert len(ditolak) == 2

    hasil_terbaru = {
        p.id: (
            await db.scalars(
                select(ScoringResult)
                .where(ScoringResult.proposal_id == p.id)
                .order_by(desc("created_at"))
                .limit(1)
            )
        ).first()
        for p in ditolak
    }
    total_scores = sorted(h.total_score for h in hasil_terbaru.values())
    red_flag_levels = [
        {f["severity"] for f in h.red_flags} for h in hasil_terbaru.values()
    ]
    assert total_scores[0] < 60  # ditolak murni karena skor di bawah ambang
    assert {"critical"} in red_flag_levels  # ditolak karena red flag, bukan skor


async def test_seed_uses_mock_engine_so_every_score_is_deterministic(client, db):
    await client.post("/api/v1/internal/seed")
    proposal_ids = [p.id for p in await _proposal_seed(db)]
    hasil = (
        await db.scalars(
            select(ScoringResult).where(ScoringResult.proposal_id.in_(proposal_ids))
        )
    ).all()
    assert len(hasil) == 6
    assert all(h.engine_name == "mock" for h in hasil)


async def test_seed_leaves_one_proposal_partially_funded_for_live_pledging(client, db):
    """Kerajinan Rotan Pak Dedi sengaja disisakan belum penuh (D-11/D-12),
    supaya juri bisa melanjutkan pledge-nya sendiri secara live saat demo,
    bukan hanya melihat data yang sudah selesai semuanya."""
    await client.post("/api/v1/internal/seed")
    proposal = await db.scalar(
        select(Proposal).where(Proposal.business_name == "Kerajinan Rotan Pak Dedi")
    )
    assert proposal is not None
    assert proposal.status is ProposalStatus.PARTIALLY_FUNDED

    entri = (
        await db.scalars(
            select(LedgerEntry).where(LedgerEntry.proposal_id == proposal.id)
        )
    ).all()
    terkumpul = total_terkumpul(entri)
    assert 0 < terkumpul < proposal.requested_amount


async def test_seed_disburses_the_first_milestone_of_the_funded_proposal(client, db):
    await client.post("/api/v1/internal/seed")
    proposal = await db.scalar(
        select(Proposal).where(Proposal.business_name == "Katering Bu Yanti")
    )
    assert proposal is not None
    assert proposal.status is ProposalStatus.FUNDED
    assert proposal.lead_investor_id is not None

    milestones = (
        await db.scalars(
            select(ProposalMilestone)
            .where(ProposalMilestone.proposal_id == proposal.id)
            .order_by(ProposalMilestone.seq)
        )
    ).all()
    assert milestones[0].status.value == "disbursed"
    assert all(m.status.value == "pending" for m in milestones[1:])


async def test_seed_milestone_amounts_sum_to_each_proposals_requested_amount(
    client, db
):
    """BR-14: seed tidak kebal dari aturan ini, sama seperti proposal UMKM
    sungguhan -- kalau seed melanggarnya, submit_proposal yang dipakainya
    sendiri sudah akan menolaknya lebih dulu (lihat test di bawah soal
    pelanggaran yang sebenarnya tidak mungkin lolos)."""
    await client.post("/api/v1/internal/seed")
    for p in await _proposal_seed(db):
        total_milestone = await db.scalar(
            select(func.coalesce(func.sum(ProposalMilestone.amount), 0)).where(
                ProposalMilestone.proposal_id == p.id
            )
        )
        assert total_milestone == p.requested_amount, p.business_name


async def test_seed_ledger_invariants_hold_for_every_seeded_proposal(client, db):
    """Menjalankan invarian R2 terhadap data seed (ledger-invariants skill):
    seed yang melanggarnya adalah cara tercepat membuat demo gagal di depan
    juri."""
    await client.post("/api/v1/internal/seed")
    for p in await _proposal_seed(db):
        entri = (
            await db.scalars(select(LedgerEntry).where(LedgerEntry.proposal_id == p.id))
        ).all()
        assert all(e.amount > 0 for e in entri)
        disbursed = sum(
            e.amount for e in entri if e.entry_type is EntryType.DISBURSEMENT_OUT
        )
        assert disbursed <= total_terkumpul(entri)
        assert hitung_saldo(entri) >= 0
        assert total_terkumpul(entri) <= p.requested_amount
        kunci = [e.idempotency_key for e in entri]
        assert len(kunci) == len(set(kunci))


async def test_seed_labels_every_proposal_as_example_data_in_its_profile(client, db):
    """Data buatan tidak apa-apa selama disebut apa adanya (brief Fase 13
    Task 1): setiap business_profile seed membawa label ini, bukan hanya
    dipercaya bahwa frontend akan menandainya."""
    await client.post("/api/v1/internal/seed")
    for p in await _proposal_seed(db):
        assert "data contoh" in p.business_profile


async def test_seed_pledges_go_through_the_real_pledge_service(client, db):
    """Pledge seed tidak ditulis langsung ke tabel: setiap baris di
    `pledges` harus punya entri `pledge_in` berpasangan di `ledger_entries`
    dengan idempotency_key `pledge:{pledge_id}`, bentuk yang hanya dihasilkan
    `create_pledge` (services/pledge.py), bukan INSERT manual."""
    await client.post("/api/v1/internal/seed")
    proposal_ids = [p.id for p in await _proposal_seed(db)]
    pledges = (
        await db.scalars(select(Pledge).where(Pledge.proposal_id.in_(proposal_ids)))
    ).all()
    assert len(pledges) == 3  # 1 di proposal partially_funded, 2 di proposal funded
    for pledge in pledges:
        entri = await db.scalar(
            select(LedgerEntry).where(
                LedgerEntry.idempotency_key == f"pledge:{pledge.id}"
            )
        )
        assert entri is not None
        assert entri.amount == pledge.amount


async def test_seed_is_idempotent_second_call_leaves_row_counts_unchanged(client, db):
    """Bukan sekadar 'tidak melempar exception': menghitung baris di setiap
    tabel yang disentuh seed sebelum dan sesudah panggilan kedua, supaya seed
    yang diam-diam menduplikasi datanya pasti tertangkap di sini. Delta
    sebelum/sesudah, bukan angka mutlak, sehingga robust terhadap residu
    test lain (lihat docstring modul): residu itu ikut ke kedua hitungan
    secara sama, jadi selisihnya tetap nol kalau seed benar-benar idempoten.
    """
    tabel: list[type] = [
        User,
        Campaign,
        Proposal,
        ProposalMilestone,
        Pledge,
        LedgerEntry,
        ScoringResult,
    ]

    res_pertama = await client.post("/api/v1/internal/seed")
    assert res_pertama.status_code == 200
    assert res_pertama.json()["sudah_pernah_disemai"] is False
    jumlah_sebelum = {m: await _jumlah_baris(db, m) for m in tabel}

    res_kedua = await client.post("/api/v1/internal/seed")
    assert res_kedua.status_code == 200
    assert res_kedua.json()["sudah_pernah_disemai"] is True
    jumlah_sesudah = {m: await _jumlah_baris(db, m) for m in tabel}

    assert jumlah_sebelum == jumlah_sesudah
    for m, n in jumlah_sebelum.items():
        assert n > 0, f"{m.__name__} seharusnya tidak kosong setelah seed pertama"


async def test_br63_seed_endpoint_not_registered_when_env_prod(monkeypatch: Any):
    """BR-63 ditegakkan secara struktural, sama seperti
    test_br63_tick_endpoint_not_registered_when_env_prod di
    test_clock_tick.py: endpointnya tidak sekadar mengembalikan 404,
    melainkan tidak pernah didaftarkan ke app.routes. Ini satu-satunya alasan
    peringatan di `.claude/plan/phase-13-submission.md` ada: deployment yang
    dilihat juri (ENV=prod) tidak bisa disemai lewat endpoint ini sama
    sekali, jadi `python -m app.seed` wajib ada sebagai jalan lain."""
    from app.config import settings
    from app.main import create_app

    def _semua_path(routes: list[Any]) -> set[str]:
        hasil: set[str] = set()
        for route in routes:
            path = getattr(route, "path", None)
            if path is not None:
                hasil.add(path)
            sub_router = getattr(route, "original_router", None)
            if sub_router is not None:
                hasil |= _semua_path(getattr(sub_router, "routes", []))
        return hasil

    monkeypatch.setattr(settings, "env", "prod")
    assert "/api/v1/internal/seed" not in _semua_path(create_app().routes)

    monkeypatch.setattr(settings, "env", "dev")
    assert "/api/v1/internal/seed" in _semua_path(create_app().routes)

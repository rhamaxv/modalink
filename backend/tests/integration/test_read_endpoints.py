"""Empat endpoint baca yang dipakai frontend tapi tidak dimiliki task mana
pun (10-api-contract.md baris 57, 67, 73, 96)."""

from uuid import uuid4

from app.models.proposal import (
    MilestoneStatus,
    Proposal,
    ProposalMilestone,
    ProposalStatus,
)
from app.services.pledge import cancel_pledge, create_pledge, get_locked_proposal


async def test_br_mine_returns_only_current_umkm_own_proposals(
    client, db, campaign, umkm, umkm_lain, buat_proposal
):
    """Dua UMKM berbeda, masing-masing punya proposal sendiri: satu UMKM
    tidak boleh melihat proposal milik UMKM lain lewat endpoint ini."""
    milik_umkm = await buat_proposal(ProposalStatus.LISTED)

    milik_umkm_lain = Proposal(
        campaign_id=campaign.id,
        umkm_id=umkm_lain.user.id,
        business_name="Warung Kopi Tetangga",
        business_profile="x" * 100,
        fund_usage_plan="x" * 100,
        business_projection="x" * 50,
        requested_amount=8_000_000,
        status=ProposalStatus.LISTED,
    )
    db.add(milik_umkm_lain)
    await db.flush()

    res = await client.get("/api/v1/proposals/mine", headers=umkm.headers)
    assert res.status_code == 200
    ids = {p["id"] for p in res.json()}
    assert str(milik_umkm.id) in ids
    assert str(milik_umkm_lain.id) not in ids


async def test_br_mine_rejected_for_investor_role(client, investor):
    res = await client.get("/api/v1/proposals/mine", headers=investor.headers)
    assert res.status_code == 403


async def test_br67_pledges_list_hides_cancelled_pledge(
    client, db, investor, investor_lain, listed_proposal, clock
):
    """Panjang daftar yang diperiksa, bukan hanya status pledge yang
    dibatalkan: daftar berisi SELURUH riwayat akan tetap punya status
    'cancelled' yang benar tapi panjangnya salah."""
    proposal = await get_locked_proposal(db, listed_proposal.id)
    aktif = await create_pledge(db, investor.user, proposal, 3_000_000, clock)
    proposal2 = await get_locked_proposal(db, listed_proposal.id)
    dibatalkan = await create_pledge(
        db, investor_lain.user, proposal2, 2_000_000, clock
    )
    proposal3 = await get_locked_proposal(db, listed_proposal.id)
    await cancel_pledge(db, proposal3, dibatalkan, clock)

    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/pledges", headers=investor.headers
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(aktif.id)


async def test_br67_lead_investor_marker_moves_after_largest_cancelled(
    client, db, investor, investor_lain, listed_proposal, clock
):
    proposal = await get_locked_proposal(db, listed_proposal.id)
    kecil = await create_pledge(db, investor_lain.user, proposal, 2_000_000, clock)
    proposal2 = await get_locked_proposal(db, listed_proposal.id)
    besar = await create_pledge(db, investor.user, proposal2, 5_000_000, clock)

    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/pledges", headers=investor.headers
    )
    oleh_id = {p["id"]: p for p in res.json()["items"]}
    assert oleh_id[str(besar.id)]["is_lead_investor"] is True
    assert oleh_id[str(kecil.id)]["is_lead_investor"] is False

    proposal3 = await get_locked_proposal(db, listed_proposal.id)
    await cancel_pledge(db, proposal3, besar, clock)

    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/pledges", headers=investor.headers
    )
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == str(kecil.id)
    assert items[0]["is_lead_investor"] is True


async def test_br67_pledges_list_hides_investor_identity_before_funded(
    client, db, investor, investor_lain, listed_proposal, clock
):
    """10-api-contract.md:106-107: endpoint ini terbuka untuk investor
    manapun (bukan hanya pemilik campaign), tapi sebelum proposal ini
    `funded` tidak boleh ada satu pun `investor_id` yang terbaca -- review
    keamanan menemukan investor yang belum pledge apa pun bisa membaca UUID
    dan nominal pasti investor lain pada proposal `partially_funded`, cukup
    untuk sengaja menyaingi pledge lead investor sebelum posisinya settle.
    `investor_lain` dipilih sebagai pembaca justru karena dia TIDAK pledge
    apa pun di sini: kalau test ini memakai akun yang pledge sendiri,
    lolosnya bisa jadi karena ia membaca pledge-nya sendiri, bukan karena
    redaksinya benar-benar bekerja untuk pledge milik orang lain."""
    proposal = await get_locked_proposal(db, listed_proposal.id)
    pledge = await create_pledge(db, investor.user, proposal, 3_000_000, clock)
    await db.refresh(listed_proposal)
    assert listed_proposal.status is ProposalStatus.PARTIALLY_FUNDED

    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/pledges",
        headers=investor_lain.headers,
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["investor_id"] is None
    # Bukan identitas: amount dan is_lead_investor tetap informasi publik
    # yang sah (bilah progres, penanda lead), dan harus tetap tampil.
    assert items[0]["amount"] == 3_000_000
    assert items[0]["is_lead_investor"] is True
    assert items[0]["id"] == str(pledge.id)


async def test_br67_pledges_list_reveals_investor_identity_once_funded(
    client, db, investor, listed_proposal, clock
):
    """Pelengkap wajib test di atas (lihat skill testing-and-regression:
    'pagar yang tidak pernah terbukti bisa merah mungkin tidak memagari apa
    pun'): tanpa test ini, redaksi di atas bisa saja menyembunyikan
    investor_id SELAMANYA karena bug, bukan karena aturannya memang begitu."""
    proposal = await get_locked_proposal(db, listed_proposal.id)
    pledge = await create_pledge(
        db, investor.user, proposal, listed_proposal.requested_amount, clock
    )
    await db.refresh(listed_proposal)
    assert listed_proposal.status is ProposalStatus.FUNDED

    res = await client.get(
        f"/api/v1/proposals/{listed_proposal.id}/pledges", headers=investor.headers
    )
    assert res.status_code == 200
    items = res.json()["items"]
    assert items[0]["investor_id"] == str(investor.user.id)
    assert items[0]["id"] == str(pledge.id)


async def test_milestones_visible_for_public_proposal_and_404_for_private_non_owner(
    client, db, listed_proposal, submitted_proposal, umkm, umkm_lain
):
    """`listed_proposal` publik (boleh_melihat selalu True untuk status itu),
    `submitted_proposal` tidak publik dan dimiliki `umkm` (bukan `umkm_lain`):
    GET milestones mewarisi persis aturan akses GET /proposals/{id}."""
    # listed_proposal sudah membawa dua milestone dari fixture-nya (BR-14,
    # jumlahnya persis requested_amount), jadi menambah seq=1 di sini akan
    # menabrak uq_milestone_proposal_seq. submitted_proposal tidak punya
    # milestone sama sekali, jadi hanya ia yang perlu dibuatkan.
    db.add(
        ProposalMilestone(
            proposal_id=submitted_proposal.id,
            seq=1,
            title="Beli mesin",
            description="x" * 20,
            amount=submitted_proposal.requested_amount,
            status=MilestoneStatus.PENDING,
        )
    )
    await db.flush()

    res_publik = await client.get(f"/api/v1/proposals/{listed_proposal.id}/milestones")
    assert res_publik.status_code == 200
    assert len(res_publik.json()["items"]) == 2

    res_anon = await client.get(f"/api/v1/proposals/{submitted_proposal.id}/milestones")
    assert res_anon.status_code == 404

    res_bukan_pemilik = await client.get(
        f"/api/v1/proposals/{submitted_proposal.id}/milestones",
        headers=umkm_lain.headers,
    )
    assert res_bukan_pemilik.status_code == 404

    res_pemilik = await client.get(
        f"/api/v1/proposals/{submitted_proposal.id}/milestones", headers=umkm.headers
    )
    assert res_pemilik.status_code == 200
    assert res_pemilik.json()["items"][0]["status"] == "pending"


async def test_milestone_list_latest_report_is_none_before_any_report(
    client, funded_proposal
):
    """m1 cair tanpa laporan (D-13): tidak ada baris milestone_reports untuk
    milestone itu sama sekali, bukan hanya belum di-review."""
    m1 = funded_proposal.milestones[0]
    res = await client.get(f"/api/v1/proposals/{funded_proposal.id}/milestones")
    items = {i["id"]: i for i in res.json()["items"]}
    assert items[str(m1.id)]["latest_report"] is None


async def test_milestone_list_includes_latest_report(client, milestone_reported):
    """`milestone_reported` (conftest.py) sudah punya laporan `pending` untuk
    m2: endpoint daftar milestone harus mengikutsertakannya, bukan hanya
    status milestone-nya."""
    res = await client.get(
        f"/api/v1/proposals/{milestone_reported.proposal_id}/milestones"
    )
    items = {i["id"]: i for i in res.json()["items"]}
    laporan = items[str(milestone_reported.id)]["latest_report"]
    assert laporan is not None
    assert laporan["review_status"] == "pending"


async def test_br46_milestone_list_latest_report_is_newest_not_the_rejected_one(
    client, db, umkm_lain, investor, funded_proposal
):
    """Setelah revisi, laporan terbaru (baris paling baru, BR-46) yang
    dikembalikan, bukan laporan `rejected` yang digantikannya."""
    m1, m2 = funded_proposal.milestones
    await client.post(f"/api/v1/milestones/{m1.id}/approve", headers=investor.headers)

    res_laporan_pertama = await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json={"narrative": "x" * 60},
    )
    id_laporan_pertama = res_laporan_pertama.json()["id"]

    res = await client.get(f"/api/v1/proposals/{funded_proposal.id}/milestones")
    items = {i["id"]: i for i in res.json()["items"]}
    assert items[str(m2.id)]["latest_report"]["id"] == id_laporan_pertama

    await client.post(
        f"/api/v1/milestones/{m2.id}/reject",
        headers=investor.headers,
        json={"note": "Bukti belum lengkap, perlu dilengkapi dahulu."},
    )

    res_setelah_tolak = await client.get(
        f"/api/v1/proposals/{funded_proposal.id}/milestones"
    )
    laporan_setelah_tolak = {i["id"]: i for i in res_setelah_tolak.json()["items"]}[
        str(m2.id)
    ]["latest_report"]
    assert laporan_setelah_tolak["id"] == id_laporan_pertama
    assert laporan_setelah_tolak["review_status"] == "rejected"

    res_revisi = await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json={"narrative": "Revisi: bukti terlampir." + "x" * 40},
    )
    id_laporan_revisi = res_revisi.json()["id"]
    assert id_laporan_revisi != id_laporan_pertama

    res_setelah_revisi = await client.get(
        f"/api/v1/proposals/{funded_proposal.id}/milestones"
    )
    laporan_terbaru = {i["id"]: i for i in res_setelah_revisi.json()["items"]}[
        str(m2.id)
    ]["latest_report"]
    assert laporan_terbaru["id"] == id_laporan_revisi
    assert laporan_terbaru["review_status"] == "pending"


async def test_internal_ledger_balance_matches_manual_sum_of_returned_entries(
    client, db, investor, investor_lain, listed_proposal, clock
):
    """Dua angka dihitung dengan cara berbeda dibandingkan: `balance` dari
    respons endpoint lawan penjumlahan manual atas `entries` yang sama
    persis respons itu, bukan angka yang dihitung ulang dari fixture."""
    proposal = await get_locked_proposal(db, listed_proposal.id)
    await create_pledge(db, investor.user, proposal, 4_000_000, clock)
    proposal2 = await get_locked_proposal(db, listed_proposal.id)
    dibatalkan = await create_pledge(
        db, investor_lain.user, proposal2, 1_000_000, clock
    )
    proposal3 = await get_locked_proposal(db, listed_proposal.id)
    await cancel_pledge(db, proposal3, dibatalkan, clock)

    res = await client.get(f"/api/v1/internal/ledger/{listed_proposal.id}")
    assert res.status_code == 200
    body = res.json()
    manual = sum(
        e["amount"] if e["entry_type"] == "pledge_in" else -e["amount"]
        for e in body["entries"]
    )
    assert manual == body["balance"]
    # pledge_in 4_000_000 + pledge_in 1_000_000 + refund_out 1_000_000 = 4_000_000.
    # Dihitung di sini dari nominal yang dikirim, bukan dibaca balik dari
    # body["balance"] sendiri, supaya assert di atas tidak jadi satu-satunya
    # pemeriksaan (tautologi "x == x" kalau implementasi salah dengan cara
    # yang konsisten di kedua sisi).
    assert body["balance"] == 4_000_000


async def test_internal_ledger_unknown_proposal_returns_404(client):
    """code diperiksa, bukan hanya status: endpoint yang belum terdaftar
    sama sekali juga membalas 404, tapi lewat error handler routing generik
    (code 'kesalahan_permintaan'), bukan lewat NotFoundError domain ini."""
    hantu = uuid4()
    res = await client.get(f"/api/v1/internal/ledger/{hantu}")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "proposal_tidak_ada"


async def test_t2_proposal_detail_hides_lead_investor_before_funded(
    client, db, investor, listed_proposal, clock
):
    """10-api-contract.md:106-107 lewat ProposalOut.lead_investor_id, bukan
    hanya lewat GET .../pledges: recompute_funding_status (services/pledge.py)
    menulis lead_investor_id begitu ada pledge aktif, apa pun status
    proposal-nya sekarang -- kolomnya SUDAH terisi di database saat proposal
    ini masih listed/partially_funded, jadi kalau redaksinya tidak benar-benar
    jalan, test ini akan merah, bukan hijau karena kolomnya kosong."""
    proposal = await get_locked_proposal(db, listed_proposal.id)
    await create_pledge(db, investor.user, proposal, 3_000_000, clock)
    await db.refresh(listed_proposal)
    assert listed_proposal.lead_investor_id == investor.user.id  # terisi di DB

    res = await client.get(f"/api/v1/proposals/{listed_proposal.id}")
    assert res.status_code == 200
    assert res.json()["lead_investor_id"] is None


async def test_t2_proposal_detail_reveals_lead_investor_once_funded(
    client, db, investor, listed_proposal, clock
):
    proposal = await get_locked_proposal(db, listed_proposal.id)
    await create_pledge(
        db, investor.user, proposal, listed_proposal.requested_amount, clock
    )

    res = await client.get(f"/api/v1/proposals/{listed_proposal.id}")
    assert res.status_code == 200
    assert res.json()["lead_investor_id"] == str(investor.user.id)


async def test_t1_public_proposal_detail_includes_collected_amount(
    client, db, investor, listed_proposal, clock
):
    """Task 1: pengunjung tanpa akun tidak punya cara lain melihat progres
    funding -- GET /proposals/{id}/pledges mewajibkan investor atau pemilik
    (api/deps.py `ambil_proposal_untuk_daftar_pledge`). collected_amount
    harus muncul tanpa header Authorization apa pun."""
    proposal = await get_locked_proposal(db, listed_proposal.id)
    await create_pledge(db, investor.user, proposal, 3_000_000, clock)

    res = await client.get(f"/api/v1/proposals/{listed_proposal.id}")
    assert res.status_code == 200
    assert res.json()["collected_amount"] == 3_000_000


async def test_t1_public_proposal_list_includes_collected_amount(
    client, db, investor, investor_lain, listed_proposal, clock
):
    """collected_amount di daftar publik harus dijumlahkan dari ledger
    sungguhan (pledge_in dikurangi refund_out), bukan sekadar hadir sebagai
    angka apa pun: membatalkan satu pledge harus mengurangi angkanya."""
    proposal = await get_locked_proposal(db, listed_proposal.id)
    await create_pledge(db, investor.user, proposal, 3_000_000, clock)
    proposal2 = await get_locked_proposal(db, listed_proposal.id)
    dibatalkan = await create_pledge(
        db, investor_lain.user, proposal2, 2_000_000, clock
    )
    proposal3 = await get_locked_proposal(db, listed_proposal.id)
    await cancel_pledge(db, proposal3, dibatalkan, clock)

    res = await client.get("/api/v1/proposals")
    assert res.status_code == 200
    item = next(p for p in res.json()["items"] if p["id"] == str(listed_proposal.id))
    assert item["collected_amount"] == 3_000_000
    # Task 4: proyeksi daftar tidak membawa tiga field teks panjang.
    assert "business_profile" not in item
    assert "fund_usage_plan" not in item
    assert "business_projection" not in item


async def test_t1_proposal_list_collected_amount_has_no_n_plus_1(
    db, campaign, buat_akun, clock
):
    """Review keamanan: GET /proposals mengembalikan 7.2 MB untuk dua belas
    proposal seeded, dan bilah progres publik (Task 1) tidak boleh menambah
    satu query ledger per baris di atas itu. Dibuktikan lewat jumlah SELECT
    sungguhan yang dieksekusi connection ini, dibandingkan antara satu
    proposal publik dan enam: kalau collected_amount dihitung satu-satu
    lewat `total_terkumpul_proposal` di dalam loop (N+1), selisihnya akan
    bertambah mengikuti jumlah proposal baru, bukan tetap."""
    from sqlalchemy import event

    from app.models.proposal import Proposal
    from app.models.user import Role
    from app.services.proposal import daftar_proposal_publik

    def _proposal(i: int, umkm_id) -> Proposal:
        return Proposal(
            campaign_id=campaign.id,
            umkm_id=umkm_id,
            business_name=f"Warung uji N+1 {i}",
            business_profile="x" * 110,
            fund_usage_plan="x" * 110,
            business_projection="x" * 60,
            requested_amount=10_000_000,
            status=ProposalStatus.LISTED,
        )

    satu = await buat_akun(db, "t1-n-plus-1-satu@contoh.id", Role.UMKM)
    db.add(_proposal(0, satu.user.id))
    await db.flush()

    async def _hitung_query() -> int:
        conn = await db.connection()
        jumlah = 0

        def _tambah(*_args, **_kwargs):
            nonlocal jumlah
            jumlah += 1

        event.listen(conn.sync_connection, "before_cursor_execute", _tambah)
        try:
            await daftar_proposal_publik(db, clock, page=1, page_size=20)
        finally:
            event.remove(conn.sync_connection, "before_cursor_execute", _tambah)
        return jumlah

    query_dengan_satu = await _hitung_query()

    for i in range(1, 6):
        akun = await buat_akun(db, f"t1-n-plus-1-{i}@contoh.id", Role.UMKM)
        db.add(_proposal(i, akun.user.id))
    await db.flush()

    query_dengan_enam = await _hitung_query()

    # Selisih tetap kecil (bukan +5, satu per proposal baru) membuktikan
    # collected_amount tidak dihitung satu-satu dalam loop.
    assert query_dengan_enam - query_dengan_satu <= 1


async def test_t4_proposal_list_pagination_shape_and_server_enforced_max(
    client, db, campaign, buat_akun
):
    """Task 4: GET /proposals mengembalikan 7.2 MB untuk dua belas proposal
    seeded karena tidak ada batas atas sama sekali. page_size harus diklem
    server, bukan sekadar default klien yang sopan -- klien yang minta
    page_size besar harus ditolak, bukan dilayani."""
    from app.models.proposal import Proposal
    from app.models.user import Role

    for i in range(3):
        akun = await buat_akun(db, f"t4-pagination-{i}@contoh.id", Role.UMKM)
        db.add(
            Proposal(
                campaign_id=campaign.id,
                umkm_id=akun.user.id,
                business_name=f"Warung uji paginasi {i}",
                business_profile="x" * 110,
                fund_usage_plan="x" * 110,
                business_projection="x" * 60,
                requested_amount=10_000_000,
                status=ProposalStatus.LISTED,
            )
        )
    await db.flush()

    res = await client.get("/api/v1/proposals", params={"page": 1, "page_size": 2})
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] >= 3

    res_halaman_dua = await client.get(
        "/api/v1/proposals", params={"page": 2, "page_size": 2}
    )
    halaman_dua = {p["id"] for p in res_halaman_dua.json()["items"]}
    halaman_satu = {p["id"] for p in body["items"]}
    assert halaman_dua.isdisjoint(halaman_satu)

    res_terlalu_besar = await client.get(
        "/api/v1/proposals", params={"page_size": 10_000}
    )
    assert res_terlalu_besar.status_code == 422

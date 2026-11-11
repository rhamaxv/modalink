"""R3: alur penuh dari campaign dibuat sampai proposal `completed`, lewat
jalur HTTP sungguhan ujung ke ujung (bukan panggilan service), supaya rantai
endpoint yang sesungguhnya dipakai pengguna benar-benar tersambung, bukan
hanya tiap potongannya diuji sendiri-sendiri.

Dua investor dipakai untuk pendanaan, bukan satu: satu pledge saja tidak
membuktikan apa pun soal patungan (co-funding) atau pemilihan lead investor
(BR-23), dua bagian inti dari model pendanaan Modalink. `FrozenClock` dipakai
seperti fixture lain di conftest.py, tapi jam tidak pernah dimajukan di sini:
R3 sengaja tetap di dalam seluruh deadline (apply_deadline dan
funding_deadline campaign) karena yang diuji adalah jalur sukses, bukan
kedaluwarsa -- itu cakupan R4.
"""

import itertools

from app.models.ledger import EntryType

AMOUNT_MILESTONE_1 = 5_000_000
AMOUNT_MILESTONE_2 = 5_000_000
REQUESTED_AMOUNT = AMOUNT_MILESTONE_1 + AMOUNT_MILESTONE_2


# Satu NIK hanya boleh dipakai satu akun, jadi tiap pendaftaran butuh nomor
# urut sendiri. Kode wilayahnya (327102) berbeda dari yang dipakai seed demo
# maupun fixture di conftest, karena ketiganya bisa hidup berdampingan di
# database test yang sama.
_URUT_NIK = itertools.count(1)


async def _daftar(client, email: str, role: str) -> dict:
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "rahasia123", "name": email, "role": role},
    )
    assert res.status_code == 201, res.text
    user_id = res.json()["id"]

    masuk = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "rahasia123"}
    )
    assert masuk.status_code == 200, masuk.text
    token = masuk.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verifikasi identitas lewat endpoint sungguhan, bukan baris yang
    # ditulis langsung ke tabel: investor dan UMKM tidak bisa menyentuh uang
    # tanpa itu, dan jalur R3 ini memang harus menjalankan produk apa adanya.
    if role in {"investor", "umkm"}:
        urut = next(_URUT_NIK)
        kyc = await client.post(
            "/api/v1/kyc",
            headers=headers,
            json={
                "full_name": "Peserta Uji R3",
                "nik": f"327102010190{urut:04d}",
                "bank_code": "bca",
                "account_holder_name": "Peserta Uji R3",
                "account_number": "1234567890",
            },
        )
        assert kyc.status_code == 200, kyc.text

    return {"user_id": user_id, "headers": headers}


async def _buat_campaign(client, investor: dict, mulai, title: str) -> dict:
    res = await client.post(
        "/api/v1/campaigns",
        headers=investor["headers"],
        json={
            "title": title,
            "description": "Mendanai warung kopi skala rumahan." * 2,
            "sector": "kuliner",
            "target_amount": 50_000_000,
            "apply_deadline": mulai.replace(year=mulai.year + 1).isoformat(),
            "funding_deadline": mulai.replace(
                year=mulai.year + 1, month=12
            ).isoformat(),
            "score_threshold": 60,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


async def _submit_proposal(client, umkm: dict, campaign_id: str, diminta: int):
    res = await client.post(
        f"/api/v1/campaigns/{campaign_id}/proposals",
        headers=umkm["headers"],
        json={
            "business_name": "Warung Kopi R3",
            "business_profile": "Warung kopi rumahan di Jakarta Timur, berjalan 3 "
            "tahun, 2 pekerja, omzet rata-rata Rp12 juta per bulan. "
            "[[SCORE:80]]",
            "requested_amount": diminta,
            "fund_usage_plan": "Rp5 juta untuk mesin kopi semi-otomatis, Rp5 juta "
            "untuk bahan baku biji dan susu selama tiga bulan ke depan.",
            "business_projection": "Omzet diperkirakan naik ke Rp18 juta per bulan "
            "dalam 6 bulan setelah mesin baru dipakai.",
            "milestones": [
                {
                    "seq": 1,
                    "title": "Beli mesin",
                    "description": "Mesin kopi semi-otomatis untuk mempercepat produksi.",
                    "amount": AMOUNT_MILESTONE_1,
                },
                {
                    "seq": 2,
                    "title": "Bahan baku",
                    "description": "Stok biji kopi dan susu untuk tiga bulan.",
                    "amount": AMOUNT_MILESTONE_2,
                },
            ],
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


async def _ambil_proposal(client, proposal_id: str) -> dict:
    res = await client.get(f"/api/v1/proposals/{proposal_id}")
    assert res.status_code == 200, res.text
    return res.json()


async def _ambil_vote_count(client, campaign_id: str, proposal_id: str) -> int:
    # vote_count hanya ada di ProposalWithSignalsOut (10-api-contract.md:
    # skor lalu vote lalu waktu submit), bukan di ProposalOut yang dipakai
    # GET /proposals/{id}: proposal tunggal tidak diurutkan terhadap apa pun
    # jadi sinyal pengurutannya tidak dikirim di sana. Daftar proposal milik
    # campaign ini satu-satunya endpoint publik yang membawanya.
    res = await client.get(f"/api/v1/campaigns/{campaign_id}/proposals")
    assert res.status_code == 200, res.text
    [item] = [p for p in res.json()["items"] if p["id"] == proposal_id]
    return item["vote_count"]


async def _vote(client, community: dict, proposal_id: str) -> None:
    res = await client.post(
        f"/api/v1/proposals/{proposal_id}/vote", headers=community["headers"]
    )
    assert res.status_code == 200, res.text


async def _pledge(client, investor: dict, proposal_id: str, amount: int) -> None:
    res = await client.post(
        f"/api/v1/proposals/{proposal_id}/pledges",
        headers=investor["headers"],
        json={"amount": amount},
    )
    assert res.status_code == 201, res.text


async def _ambil_milestones(client, proposal_id: str) -> list[dict]:
    res = await client.get(f"/api/v1/proposals/{proposal_id}/milestones")
    assert res.status_code == 200, res.text
    return res.json()["items"]


async def _approve(client, investor: dict, milestone_id: str):
    return await client.post(
        f"/api/v1/milestones/{milestone_id}/approve", headers=investor["headers"]
    )


async def _lapor(client, umkm: dict, milestone_id: str, narrative: str):
    res = await client.post(
        f"/api/v1/milestones/{milestone_id}/reports",
        headers=umkm["headers"],
        json={"narrative": narrative},
    )
    assert res.status_code == 201, res.text


async def _ambil_ledger(client, proposal_id: str) -> dict:
    # Endpoint internal (BR-63): tidak memeriksa peran atau kepemilikan sama
    # sekali (lihat docstring app/api/v1/internal.py), hanya terdaftar karena
    # ENV=dev di .env test. Dipakai di sini sebagai sumber kebenaran ledger,
    # sama seperti cara juri memverifikasinya lewat browser saat demo.
    res = await client.get(f"/api/v1/internal/ledger/{proposal_id}")
    assert res.status_code == 200, res.text
    return res.json()


async def test_r3_full_flow_from_campaign_to_completed(client, clock):
    mulai = clock.now()
    a = await _daftar(client, "r3-investor-a@contoh.id", "investor")
    b = await _daftar(client, "r3-investor-b@contoh.id", "investor")
    campaign = await _buat_campaign(client, a, mulai, "Modal warung kopi R3")

    umkm = await _daftar(client, "r3-umkm@contoh.id", "umkm")
    proposal = await _submit_proposal(client, umkm, campaign["id"], REQUESTED_AMOUNT)
    proposal_id = proposal["id"]

    # MockScoringEngine menilai di latar belakang yang berjalan sinkron di
    # bawah test client ASGI (lihat app/jobs/inline.py): pada saat POST di
    # atas kembali, scoring_result sudah ter-commit.
    assert (await _ambil_proposal(client, proposal_id))["status"] == "listed"

    warga = await _daftar(client, "r3-warga@contoh.id", "community")
    await _vote(client, warga, proposal_id)
    assert await _ambil_vote_count(client, campaign["id"], proposal_id) == 1

    separuh = REQUESTED_AMOUNT // 2 + 1_000_000  # 6 juta: lebih dari separuh
    await _pledge(client, a, proposal_id, separuh)
    assert (await _ambil_proposal(client, proposal_id))["status"] == "partially_funded"

    sisa = REQUESTED_AMOUNT - separuh  # 4 juta
    await _pledge(client, b, proposal_id, sisa)
    detail = await _ambil_proposal(client, proposal_id)
    assert detail["status"] == "funded"
    # BR-23: lead investor adalah pledge terbesar, a (6 juta) bukan b (4 juta).
    assert detail["lead_investor_id"] == a["user_id"]

    m1, m2 = await _ambil_milestones(client, proposal_id)
    assert m1["seq"] == 1
    assert m2["seq"] == 2

    # D-13: milestone pertama cair tanpa laporan.
    res_approve_m1 = await _approve(client, a, m1["id"])
    assert res_approve_m1.status_code == 200, res_approve_m1.text
    assert (await _ambil_milestones(client, proposal_id))[0]["status"] == "disbursed"

    await _lapor(
        client, umkm, m2["id"], "Mesin terpasang, omzet naik 15 persen." + "x" * 30
    )
    res_approve_m2 = await _approve(client, a, m2["id"])
    assert res_approve_m2.status_code == 200, res_approve_m2.text

    proposal_akhir = await _ambil_proposal(client, proposal_id)
    assert proposal_akhir["status"] == "completed"

    ledger = await _ambil_ledger(client, proposal_id)
    cair = sum(
        e["amount"]
        for e in ledger["entries"]
        if e["entry_type"] == EntryType.DISBURSEMENT_OUT.value
    )
    assert cair == REQUESTED_AMOUNT
    assert ledger["balance"] == 0


async def test_r3_non_lead_investor_cannot_approve_milestone(client, clock):
    """Cabang kecil dari alur yang sama, dipisah supaya kegagalannya jelas
    (lihat docstring modul ini soal dua investor): investor b pledge lebih
    kecil daripada a, jadi b bukan lead investor dan approve-nya ditolak
    404 (BR-44), bukan 403 -- pola yang sama dengan test_r4_non_lead_
    investor_cannot_approve di test_r4_failure_paths.py."""
    mulai = clock.now()
    a = await _daftar(client, "r3-nonlead-a@contoh.id", "investor")
    b = await _daftar(client, "r3-nonlead-b@contoh.id", "investor")
    umkm = await _daftar(client, "r3-nonlead-umkm@contoh.id", "umkm")
    campaign = await _buat_campaign(client, a, mulai, "Modal warung kopi R3 non-lead")

    proposal = await _submit_proposal(client, umkm, campaign["id"], REQUESTED_AMOUNT)
    proposal_id = proposal["id"]
    assert (await _ambil_proposal(client, proposal_id))["status"] == "listed"

    await _pledge(client, a, proposal_id, REQUESTED_AMOUNT - 1_000_000)
    await _pledge(client, b, proposal_id, 1_000_000)
    detail = await _ambil_proposal(client, proposal_id)
    assert detail["status"] == "funded"
    assert detail["lead_investor_id"] == a["user_id"]

    m1, _m2 = await _ambil_milestones(client, proposal_id)
    res = await _approve(client, b, m1["id"])
    assert res.status_code == 404

    # Ledger tidak boleh tersentuh sama sekali oleh approve yang ditolak.
    ledger = await _ambil_ledger(client, proposal_id)
    assert not [
        e
        for e in ledger["entries"]
        if e["entry_type"] == EntryType.DISBURSEMENT_OUT.value
    ]

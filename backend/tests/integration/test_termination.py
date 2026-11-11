"""Penghentian proposal yang sudah penuh tapi tahapnya macet.

Menutup satu-satunya jalan buntu yang tersisa di aliran dana: sebelum
mekanisme ini ada, proposal `funded` yang UMKM-nya berhenti melapor menahan
sisa dananya selamanya. Lead investor tidak bisa menyetujui (belum ada
laporan), tidak bisa menolak (menolak hanya sah untuk laporan yang masuk),
dan tidak ada tenggat apa pun yang berlaku lagi setelah proposal penuh.
"""

from app.domain.termination import HARI_JENDELA_JAWABAN, HARI_TAHAP_MACET


async def _cairkan_tahap_pertama(client, funded_proposal, investor):
    r = await client.post(
        f"/api/v1/milestones/{funded_proposal.milestones[0].id}/approve",
        headers=investor.headers,
    )
    assert r.status_code == 200, r.text


async def _ajukan(client, proposal_id, akun):
    return await client.post(
        f"/api/v1/proposals/{proposal_id}/terminate", headers=akun.headers
    )


class TestWhenTerminationIsAllowed:
    async def test_a_stage_still_within_its_deadline_cannot_be_terminated(
        self, client, funded_proposal, investor
    ):
        """Tahap yang belum lewat tenggat bukan tahap yang macet. Tanpa
        pemeriksaan ini, lead investor bisa menarik dana kapan saja setelah
        tahap pertama cair, termasuk ketika UMKM sedang mengerjakannya."""
        await _cairkan_tahap_pertama(client, funded_proposal, investor)
        r = await _ajukan(client, funded_proposal.id, investor)
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "tahap_belum_macet"

    async def test_an_overdue_stage_can_be_terminated_by_the_lead_investor(
        self, client, funded_proposal, investor, majukan
    ):
        await _cairkan_tahap_pertama(client, funded_proposal, investor)
        await majukan(HARI_TAHAP_MACET + 1)
        r = await _ajukan(client, funded_proposal.id, investor)
        assert r.status_code == 200, r.text
        assert r.json()["termination_requested_at"] is not None
        # Belum ada dana yang kembali: pengajuan bukan penghentian.
        assert r.json()["status"] == "funded"

    async def test_an_investor_who_is_not_the_lead_cannot_terminate(
        self, client, funded_proposal, investor, investor_lain, majukan
    ):
        """404, bukan 403: investor lain tidak boleh sekaligus mengonfirmasi
        keberadaan proposal ini."""
        await _cairkan_tahap_pertama(client, funded_proposal, investor)
        await majukan(HARI_TAHAP_MACET + 1)
        r = await _ajukan(client, funded_proposal.id, investor_lain)
        assert r.status_code == 404

    async def test_a_proposal_that_is_not_funded_cannot_be_terminated(
        self, client, listed_proposal, investor
    ):
        """Pledge sebagian dulu, supaya `investor` benar-benar menjadi lead
        investor. Tanpa itu, proposal tanpa pledge tidak punya lead sama
        sekali dan permintaannya berhenti di 404 (bukan pemilik) sebelum
        sempat sampai ke pemeriksaan status yang sedang diuji di sini.
        """
        sebagian = await client.post(
            f"/api/v1/proposals/{listed_proposal.id}/pledges",
            json={"amount": 1_000_000},
            headers=investor.headers,
        )
        assert sebagian.status_code == 201, sebagian.text
        r = await _ajukan(client, listed_proposal.id, investor)
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "proposal_tidak_bisa_dihentikan"

    async def test_an_outsider_never_learns_whether_the_proposal_exists(
        self, client, listed_proposal, investor_lain
    ):
        """Proposal tanpa pledge tidak punya lead investor sama sekali, jadi
        siapa pun yang mencoba menghentikannya dibalas 404, bukan 409 yang
        akan mengonfirmasi keberadaannya."""
        r = await _ajukan(client, listed_proposal.id, investor_lain)
        assert r.status_code == 404

    async def test_a_stage_already_reported_is_not_considered_stalled(
        self, client, db, funded_proposal, investor, umkm_lain, majukan
    ):
        """Kalau laporannya sudah masuk, bolanya ada di lead investor, bukan
        di UMKM. Ia tidak boleh menyebut macet sesuatu yang justru sedang
        menunggu dirinya sendiri."""
        await _cairkan_tahap_pertama(client, funded_proposal, investor)
        await majukan(HARI_TAHAP_MACET + 1)
        lapor = await client.post(
            f"/api/v1/milestones/{funded_proposal.milestones[1].id}/reports",
            json={"narrative": "x" * 60},
            headers=umkm_lain.headers,
        )
        assert lapor.status_code == 201, lapor.text
        r = await _ajukan(client, funded_proposal.id, investor)
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "tahap_belum_macet"


class TestTheAnswerWindow:
    async def test_a_report_inside_the_window_cancels_the_termination(
        self, client, funded_proposal, investor, umkm_lain, majukan
    ):
        """Inti dari jendela jawaban: UMKM yang akhirnya melapor tidak
        kehilangan sisa dananya hanya karena sempat terlambat."""
        await _cairkan_tahap_pertama(client, funded_proposal, investor)
        await majukan(HARI_TAHAP_MACET + 1)
        assert (await _ajukan(client, funded_proposal.id, investor)).status_code == 200

        lapor = await client.post(
            f"/api/v1/milestones/{funded_proposal.milestones[1].id}/reports",
            json={"narrative": "x" * 60},
            headers=umkm_lain.headers,
        )
        assert lapor.status_code == 201, lapor.text

        detail = (await client.get(f"/api/v1/proposals/{funded_proposal.id}")).json()
        assert detail["termination_requested_at"] is None
        assert detail["status"] == "funded"

    async def test_silence_through_the_window_returns_the_remaining_money(
        self, client, funded_proposal, investor, majukan
    ):
        await _cairkan_tahap_pertama(client, funded_proposal, investor)
        await majukan(HARI_TAHAP_MACET + 1)
        await _ajukan(client, funded_proposal.id, investor)

        # Masih di dalam jendela: belum ada yang berubah.
        await majukan(HARI_TAHAP_MACET + HARI_JENDELA_JAWABAN - 1)
        belum = (await client.get(f"/api/v1/proposals/{funded_proposal.id}")).json()
        assert belum["status"] == "funded"

        # Lewat jendela: dibaca sekali, dan rekonsiliasinya terjadi saat itu.
        await majukan(HARI_TAHAP_MACET + HARI_JENDELA_JAWABAN + 1)
        sesudah = (await client.get(f"/api/v1/proposals/{funded_proposal.id}")).json()
        assert sesudah["status"] == "failed"
        assert sesudah["termination_requested_at"] is None

    async def test_only_the_undisbursed_remainder_comes_back(
        self, client, funded_proposal, investor, majukan
    ):
        """Dana yang sudah diterima UMKM TIDAK ditarik kembali oleh mekanisme
        ini. Yang kembali hanya saldo yang belum cair, dan ledger harus
        menunjukkan persis itu."""
        await _cairkan_tahap_pertama(client, funded_proposal, investor)
        cair = funded_proposal.milestones[0].amount
        total = funded_proposal.requested_amount

        await majukan(HARI_TAHAP_MACET + 1)
        await _ajukan(client, funded_proposal.id, investor)
        await majukan(HARI_TAHAP_MACET + HARI_JENDELA_JAWABAN + 1)
        await client.get(f"/api/v1/proposals/{funded_proposal.id}")

        buku = (
            await client.get(
                f"/api/v1/proposals/{funded_proposal.id}/ledger",
                headers=investor.headers,
            )
        ).json()
        assert buku["total_cair"] == cair
        # Saldo nol: tidak ada rupiah yang tertinggal menggantung.
        assert buku["balance"] == 0
        dikembalikan = sum(
            e["amount"] for e in buku["entries"] if e["entry_type"] == "refund_out"
        )
        assert dikembalikan == total - cair

    async def test_reconciling_twice_never_refunds_twice(
        self, client, funded_proposal, investor, majukan
    ):
        """Rekonsiliasi berjalan di SETIAP pembacaan proposal (D-06), jadi
        idempotensinya bukan kenyamanan, melainkan syarat agar ledger tidak
        menciptakan uang."""
        await _cairkan_tahap_pertama(client, funded_proposal, investor)
        await majukan(HARI_TAHAP_MACET + 1)
        await _ajukan(client, funded_proposal.id, investor)
        await majukan(HARI_TAHAP_MACET + HARI_JENDELA_JAWABAN + 1)

        for _ in range(3):
            await client.get(f"/api/v1/proposals/{funded_proposal.id}")

        buku = (
            await client.get(
                f"/api/v1/proposals/{funded_proposal.id}/ledger",
                headers=investor.headers,
            )
        ).json()
        baris_refund = [e for e in buku["entries"] if e["entry_type"] == "refund_out"]
        assert len(baris_refund) == 1
        assert buku["balance"] == 0

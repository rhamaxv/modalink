"""Verifikasi identitas dan gerbangnya.

Fixture akun di tests/conftest.py otomatis menandai investor dan UMKM sudah
terverifikasi, karena tanpa itu SELURUH test yang menyentuh uang berubah jadi
test tentang gerbang ini. Berkas inilah yang menguji gerbangnya sendiri, dan
karena itu ia membuat akunnya sendiri lewat `buat_akun` lalu menghapus
verifikasinya.
"""

from sqlmodel import select

from app.models.kyc import KycStatus, KycSubmission
from app.models.user import Role

NIK_SAH = "3201011708900001"
BODY = {
    "full_name": "Sri Wahyuni",
    "nik": NIK_SAH,
    "bank_code": "bca",
    "account_holder_name": "Sri Wahyuni",
    "account_number": "1234567890",
}


async def _tanpa_verifikasi(db, akun):
    """Menghapus verifikasi yang dipasang fixture, supaya gerbangnya bisa
    diuji terhadap akun yang sungguh belum terverifikasi."""
    baris = await db.scalar(
        select(KycSubmission).where(KycSubmission.user_id == akun.user.id)
    )
    if baris is not None:
        await db.delete(baris)
        await db.flush()


class TestSubmission:
    async def test_a_valid_submission_is_verified_and_never_echoes_the_full_number(
        self, client, investor
    ):
        r = await client.post("/api/v1/kyc", json=BODY, headers=investor.headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "verified"
        assert body["nik_last4"] == "0001"
        assert body["account_last4"] == "7890"
        # NIK dan nomor rekening utuh tidak pernah dikirim balik, dan
        # memang tidak disimpan utuh sejak awal.
        assert NIK_SAH not in r.text
        assert "1234567890" not in r.text
        # Field yang memaksa antarmuka menyebut sifat verifikasinya.
        assert body["verifikasi_simulasi"] is True

    async def test_the_full_nik_never_reaches_the_database(self, client, db, investor):
        await client.post("/api/v1/kyc", json=BODY, headers=investor.headers)
        baris = await db.scalar(
            select(KycSubmission).where(KycSubmission.user_id == investor.user.id)
        )
        assert baris is not None
        # Yang tersimpan hash, bukan NIK. Panjang sha256 heksadesimal.
        assert baris.nik_hash != NIK_SAH
        assert len(baris.nik_hash) == 64
        assert baris.nik_last4 == "0001"

    async def test_submitting_again_replaces_the_previous_one(
        self, client, db, investor
    ):
        await client.post("/api/v1/kyc", json=BODY, headers=investor.headers)
        r = await client.post(
            "/api/v1/kyc",
            json={**BODY, "bank_code": "bni", "account_number": "9876543210"},
            headers=investor.headers,
        )
        assert r.status_code == 200
        assert r.json()["bank_code"] == "bni"
        assert r.json()["account_last4"] == "3210"
        # Satu baris, bukan dua: orang yang salah mengetik rekening harus bisa
        # memperbaikinya tanpa meninggalkan baris lama yang mana pun bisa
        # terpilih belakangan.
        semua = (
            await db.scalars(
                select(KycSubmission).where(KycSubmission.user_id == investor.user.id)
            )
        ).all()
        assert len(semua) == 1

    async def test_one_nik_belongs_to_one_account_only(
        self, client, investor, investor_lain
    ):
        """Tanpa aturan ini gerbang verifikasi tidak menahan apa pun: satu
        orang bisa membuat akun sebanyak yang ia mau dan memverifikasi
        semuanya dengan NIK yang sama."""
        await client.post("/api/v1/kyc", json=BODY, headers=investor.headers)
        r = await client.post("/api/v1/kyc", json=BODY, headers=investor_lain.headers)
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "nik_sudah_dipakai"
        # Pesannya tidak menyebut akun mana yang memakainya.
        assert "investor" not in r.json()["error"]["message"].lower()

    async def test_rejects_a_malformed_nik_with_a_message_that_says_why(
        self, client, investor
    ):
        r = await client.post(
            "/api/v1/kyc", json={**BODY, "nik": "12345"}, headers=investor.headers
        )
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "identitas_tidak_sah"
        assert "16 digit" in r.json()["error"]["message"]

    async def test_rejects_a_nik_whose_owner_would_be_under_age(
        self, client, investor, clock
    ):
        # Lahir tahun ini: umurnya nol.
        tahun_ini = clock.now().year % 100
        r = await client.post(
            "/api/v1/kyc",
            json={**BODY, "nik": f"3201010101{tahun_ini:02d}0001"},
            headers=investor.headers,
        )
        assert r.status_code == 422
        assert "17 tahun" in r.json()["error"]["message"]

    async def test_a_community_account_is_never_asked_for_its_nik(
        self, client, community
    ):
        """Peran komunitas tidak pernah menyentuh uang, jadi meminta NIK
        darinya adalah mengumpulkan data pribadi tanpa alasan."""
        r = await client.post("/api/v1/kyc", json=BODY, headers=community.headers)
        assert r.status_code == 403


class TestGate:
    async def test_an_unverified_umkm_cannot_submit_a_proposal(
        self, client, db, campaign, buat_akun, kirim_proposal
    ):
        akun = await buat_akun(db, "umkm-belum-verifikasi@contoh.id", Role.UMKM)
        await _tanpa_verifikasi(db, akun)
        r = await kirim_proposal(campaign.id, headers=akun.headers)
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "belum_terverifikasi"
        # Pesannya menyebut APA yang harus dilakukan: pengguna yang ditolak
        # tanpa jalan keluar akan mengira produknya rusak.
        assert "verifikasi" in r.json()["error"]["message"].lower()

    async def test_an_unverified_investor_cannot_pledge(
        self, client, db, listed_proposal, buat_akun
    ):
        akun = await buat_akun(db, "investor-belum-verifikasi@contoh.id", Role.INVESTOR)
        await _tanpa_verifikasi(db, akun)
        r = await client.post(
            f"/api/v1/proposals/{listed_proposal.id}/pledges",
            json={"amount": 1_000_000},
            headers=akun.headers,
        )
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "belum_terverifikasi"

    async def test_verifying_opens_the_gate_that_was_closed(
        self, client, db, listed_proposal, buat_akun
    ):
        """Sisi sebaliknya, dan ia yang membuktikan gerbangnya memang bisa
        dibuka: akun yang sama, ditolak lalu diterima, hanya karena ia
        memverifikasi identitasnya di antara kedua percobaan."""
        akun = await buat_akun(db, "investor-verifikasi-dulu@contoh.id", Role.INVESTOR)
        await _tanpa_verifikasi(db, akun)

        sebelum = await client.post(
            f"/api/v1/proposals/{listed_proposal.id}/pledges",
            json={"amount": 1_000_000},
            headers=akun.headers,
        )
        assert sebelum.status_code == 403

        kyc = await client.post(
            "/api/v1/kyc",
            json={**BODY, "nik": "3201011708900077"},
            headers=akun.headers,
        )
        assert kyc.status_code == 200

        sesudah = await client.post(
            f"/api/v1/proposals/{listed_proposal.id}/pledges",
            json={"amount": 1_000_000},
            headers=akun.headers,
        )
        assert sesudah.status_code == 201, sesudah.text


class TestReadingOwnStatus:
    async def test_an_account_that_never_submitted_gets_a_clear_404(
        self, client, db, buat_akun
    ):
        akun = await buat_akun(db, "belum-pernah-kyc@contoh.id", Role.INVESTOR)
        await _tanpa_verifikasi(db, akun)
        r = await client.get("/api/v1/kyc/me", headers=akun.headers)
        assert r.status_code == 404
        assert r.json()["error"]["code"] == "kyc_belum_diajukan"

    async def test_an_account_only_ever_reads_its_own_status(
        self, client, investor, investor_lain
    ):
        await client.post("/api/v1/kyc", json=BODY, headers=investor.headers)
        milik_lain = await client.get("/api/v1/kyc/me", headers=investor_lain.headers)
        # Akun lain membaca MILIKNYA SENDIRI (dipasang fixture), bukan milik
        # investor di atas: tidak ada parameter apa pun yang bisa dipakai
        # menunjuk akun orang lain.
        assert milik_lain.json()["nik_last4"] != "0001"

    async def test_the_status_endpoint_never_returns_the_full_numbers(
        self, client, investor
    ):
        await client.post("/api/v1/kyc", json=BODY, headers=investor.headers)
        r = await client.get("/api/v1/kyc/me", headers=investor.headers)
        assert NIK_SAH not in r.text
        assert "1234567890" not in r.text
        assert r.json()["status"] == KycStatus.VERIFIED.value

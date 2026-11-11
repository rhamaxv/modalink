"""H-1: get_session harus commit saat request selesai tanpa error.

Test ini sengaja tidak memakai fixture `db`: fixture itu membungkus setiap
test dalam transaksi yang di-rollback di akhir test (lihat tests/conftest.py),
yang justru menyembunyikan bug ini sepenuhnya karena baris yang di-flush tetap
terlihat lewat sesi yang sama tanpa pernah perlu benar-benar commit. Di sini
request dikirim ke app yang sama sekali tidak menimpa get_session, lalu baris
yang ditulis diperiksa lewat SessionLocal terpisah: koneksi lain yang baru,
yang hanya bisa melihat baris yang sudah benar-benar ter-commit ke Postgres,
bukan yang sekadar di-flush dalam transaksi yang belum ditutup.
"""

import uuid
from datetime import timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.domain.clock import SystemClock
from app.main import create_app


async def test_register_endpoint_really_commits_to_database() -> None:
    email = f"br-h1-persistence-{uuid.uuid4().hex}@contoh.id"
    app = create_app()  # tanpa dependency_overrides: jalur get_session produksi.
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": email,
                    "password": "rahasia123",
                    "name": "Pengguna Uji Persistence",
                    "role": "umkm",
                },
            )
        assert res.status_code == 201

        async with SessionLocal() as sesi_terpisah:
            baris = (
                await sesi_terpisah.execute(
                    text("SELECT 1 FROM users WHERE email = :email"), {"email": email}
                )
            ).first()
        assert baris is not None, (
            "Baris tidak ditemukan lewat koneksi terpisah: request sukses "
            "tapi tidak ter-commit ke database (H-1)."
        )
    finally:
        # Tidak ada fixture yang membersihkan baris ini: ia benar-benar
        # ter-commit ke database uji, jadi test ini wajib menghapusnya sendiri.
        async with SessionLocal() as sesi_bersih:
            await sesi_bersih.execute(
                text("DELETE FROM users WHERE email = :email"), {"email": email}
            )
            await sesi_bersih.commit()


async def test_c31_background_scoring_job_really_commits_to_database() -> None:
    """C-31: test di atas membuktikan H-1 lewat /auth/register, yang tidak
    punya job latar belakang. Bug sungguhan yang memotivasi H-1 adalah job
    scoring membaca proposal lewat sesi terpisahnya sendiri dan tidak
    menemukan apa pun karena request submit proposal belum pernah commit.

    Test ini menjalankan jalur itu end-to-end lewat app produksi tanpa
    dependency_overrides: submit proposal sungguhan, biarkan job scoring
    latar belakang (InlineRunner) jalan sampai selesai, lalu baca
    ScoringResult lewat SessionLocal terpisah, bukan lewat sesi request.
    """
    sufiks = uuid.uuid4().hex
    email_investor = f"br-h1-investor-{sufiks}@contoh.id"
    email_umkm = f"br-h1-umkm-{sufiks}@contoh.id"
    sekarang = SystemClock().now()

    app = create_app()  # tanpa dependency_overrides: jalur get_session produksi.
    transport = ASGITransport(app=app)
    proposal_id: uuid.UUID | None = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for email, peran, nama in (
                (email_investor, "investor", "Investor Uji Persistence"),
                (email_umkm, "umkm", "UMKM Uji Persistence"),
            ):
                res = await client.post(
                    "/api/v1/auth/register",
                    json={
                        "email": email,
                        "password": "rahasia123",
                        "name": nama,
                        "role": peran,
                    },
                )
                assert res.status_code == 201

            token_investor = (
                await client.post(
                    "/api/v1/auth/login",
                    json={"email": email_investor, "password": "rahasia123"},
                )
            ).json()["access_token"]
            token_umkm = (
                await client.post(
                    "/api/v1/auth/login",
                    json={"email": email_umkm, "password": "rahasia123"},
                )
            ).json()["access_token"]

            # Investor dan UMKM tidak bisa menyentuh uang tanpa verifikasi
            # identitas (gerbang di api/v1/proposals.py dan pledges.py).
            # NIK-nya diturunkan dari email yang sudah unik per jalannya test
            # ini, supaya dua akun di sini tidak pernah memakai NIK yang sama.
            for token, nama in ((token_investor, "Investor"), (token_umkm, "UMKM")):
                urut = abs(hash(f"{email_investor}{nama}")) % 9000 + 1000
                kyc = await client.post(
                    "/api/v1/kyc",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "full_name": f"{nama} Uji Persistence",
                        "nik": f"3271030101900{urut % 1000:03d}",
                        "bank_code": "bca",
                        "account_holder_name": f"{nama} Uji Persistence",
                        "account_number": "1234567890",
                    },
                )
                assert kyc.status_code == 200, kyc.text

            res_campaign = await client.post(
                "/api/v1/campaigns",
                headers={"Authorization": f"Bearer {token_investor}"},
                json={
                    "title": "Campaign uji persistence job latar belakang",
                    "description": "Mendanai warung kopi skala rumahan." * 2,
                    "sector": "kuliner",
                    "target_amount": 50_000_000,
                    "apply_deadline": (sekarang + timedelta(days=7)).isoformat(),
                    "funding_deadline": (sekarang + timedelta(days=21)).isoformat(),
                    "score_threshold": 60,
                },
            )
            assert res_campaign.status_code == 201
            campaign_id = res_campaign.json()["id"]

            res_proposal = await client.post(
                f"/api/v1/campaigns/{campaign_id}/proposals",
                headers={"Authorization": f"Bearer {token_umkm}"},
                json={
                    "business_name": "Warung Kopi Uji Persistence",
                    "business_profile": (
                        "Warung kopi rumahan di Jakarta Timur, berjalan 3 tahun, "
                        "2 pekerja, omzet rata-rata Rp12 juta per bulan."
                    ),
                    "requested_amount": 10_000_000,
                    "fund_usage_plan": (
                        "Rp6 juta untuk mesin kopi semi-otomatis, Rp3 juta untuk "
                        "bahan baku biji dan susu selama tiga bulan, dan Rp1 juta "
                        "untuk memperbaiki etalase depan yang sudah lapuk."
                    ),
                    "business_projection": (
                        "Omzet diperkirakan naik ke Rp18 juta per bulan dalam 6 "
                        "bulan setelah mesin baru dipakai."
                    ),
                    "milestones": [
                        {
                            "seq": 1,
                            "title": "Beli mesin",
                            "description": "x" * 20,
                            "amount": 5_000_000,
                        },
                        {
                            "seq": 2,
                            "title": "Bahan baku",
                            "description": "x" * 20,
                            "amount": 5_000_000,
                        },
                    ],
                },
            )
            assert res_proposal.status_code == 201
            proposal_id = uuid.UUID(res_proposal.json()["id"])

        async with SessionLocal() as sesi_terpisah:
            baris = (
                await sesi_terpisah.execute(
                    text("SELECT 1 FROM scoring_results WHERE proposal_id = :pid"),
                    {"pid": str(proposal_id)},
                )
            ).first()
        assert baris is not None, (
            "Tidak ada baris scoring_results lewat koneksi terpisah: job "
            "scoring latar belakang membaca lewat sesinya sendiri dan tidak "
            "melihat proposal yang belum ter-commit (bug yang memotivasi H-1)."
        )
    finally:
        # Sama seperti test di atas: baris ini benar-benar ter-commit, jadi
        # harus dihapus tangan sendiri, bukan diandalkan pada rollback test.
        async with SessionLocal() as sesi_bersih:
            if proposal_id is not None:
                await sesi_bersih.execute(
                    text("DELETE FROM scoring_results WHERE proposal_id = :pid"),
                    {"pid": str(proposal_id)},
                )
                await sesi_bersih.execute(
                    text("DELETE FROM proposal_milestones WHERE proposal_id = :pid"),
                    {"pid": str(proposal_id)},
                )
                await sesi_bersih.execute(
                    text("DELETE FROM proposals WHERE id = :pid"),
                    {"pid": str(proposal_id)},
                )
            await sesi_bersih.execute(
                text(
                    "DELETE FROM campaigns WHERE investor_id IN "
                    "(SELECT id FROM users WHERE email = :email)"
                ),
                {"email": email_investor},
            )
            await sesi_bersih.execute(
                text("DELETE FROM users WHERE email IN (:e1, :e2)"),
                {"e1": email_investor, "e2": email_umkm},
            )
            await sesi_bersih.commit()

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

from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.main import create_app


async def test_register_endpoint_benar_benar_commit_ke_database() -> None:
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

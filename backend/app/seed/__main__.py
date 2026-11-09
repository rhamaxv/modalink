"""Entry point `python -m app.seed`: satu-satunya jalan menyemai data demo di
server produksi, karena `POST /internal/seed` tidak pernah terdaftar di sana
(ENV=prod, BR-63). Dipanggil pemilik project lewat
`docker compose exec backend python -m app.seed`.

Membuka sesinya sendiri dan meng-commit sendiri di sini, bukan di
app/seed/demo.py: `seed_demo_data` murni menerima sesi yang sudah terbuka
(dipakai juga oleh endpoint internal lewat dependency `get_session`, yang
sudah meng-commit sendiri), supaya logikanya tidak terikat pada cara
sesi itu dibuka.
"""

import asyncio

from app.db.session import SessionLocal
from app.seed.demo import DEMO_PASSWORD, seed_demo_data


async def main() -> None:
    async with SessionLocal() as session:
        hasil = await seed_demo_data(session)
        await session.commit()

    if hasil.sudah_pernah_disemai:
        print("Seed sudah pernah dijalankan sebelumnya, tidak ada yang ditulis ulang.")
    else:
        print(
            "Seed berhasil dijalankan. Password demo untuk seluruh akun:", DEMO_PASSWORD
        )
    print(
        f"users={hasil.jumlah_user} campaigns={hasil.jumlah_campaign} "
        f"proposals={hasil.jumlah_proposal} pledges={hasil.jumlah_pledge} "
        f"ledger_entries={hasil.jumlah_ledger_entry}"
    )


if __name__ == "__main__":
    asyncio.run(main())

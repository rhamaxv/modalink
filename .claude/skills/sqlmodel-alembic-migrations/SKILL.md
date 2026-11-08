---
name: sqlmodel-alembic-migrations
description: Alur kerja model SQLModel dan migrasi Alembic di Logicodix. Gunakan saat menambah atau mengubah tabel, kolom, index, atau constraint. Memuat jebakan tipe BigInteger, constraint yang tidak dihasilkan autogenerate, dan cara menguji migrasi bisa dibalik.
---

# Model dan migrasi di Logicodix

## Jebakan nomor satu: `int` bukan `BIGINT`

SQLModel memetakan `int` ke `INTEGER`, yang meluap di sekitar Rp2,1 miliar. Untuk produk yang
mencatat dana usaha, itu bukan batas teoretis.

```python
# Salah: meluap di Rp2.147.483.647
target_amount: int

# Benar
target_amount: int = Field(sa_column=Column(BigInteger, nullable=False))
```

Berlaku untuk **setiap** kolom nominal: `target_amount`, `requested_amount`, `amount` di
milestone, pledge, dan ledger.

## Constraint ditegakkan di database

Validasi Python adalah lapisan pertama untuk pesan error yang enak dibaca. Ia bukan penjaga
terakhir, karena seed script, migrasi data, dan dua request bersamaan bisa menembusnya.

```python
__table_args__ = (
    CheckConstraint("amount > 0", name="ck_ledger_amount_positif"),
    CheckConstraint("funding_deadline > apply_deadline", name="ck_campaign_urutan_deadline"),
)
```

## Yang tidak dihasilkan `--autogenerate`

Tiga hal ini harus ditulis tangan di berkas migrasi. Diam-diam tidak ikut, dan baru ketahuan
saat test gagal di CI:

**Partial unique index**

```python
op.create_index(
    "uq_proposal_aktif_per_umkm_per_campaign",
    "proposals", ["campaign_id", "umkm_id"],
    unique=True,
    postgresql_where=sa.text("status NOT IN ('rejected', 'failed')"),
)
```

Index ini **harus** partial. UMKM yang proposalnya ditolak harus bisa mengajukan lagi.

**Perubahan tipe enum.** Menambah nilai ke enum Postgres butuh `ALTER TYPE ... ADD VALUE`, dan di
Postgres lama itu tidak bisa berjalan di dalam transaksi.

**Data migration.** Mengisi kolom baru pada baris yang sudah ada selalu ditulis tangan.

## Alur kerja

```bash
# 1. Ubah modelnya
# 2. Hasilkan migrasi
cd backend && alembic revision --autogenerate -m "nama_jelas"

# 3. BACA berkas yang dihasilkan. Tambahkan partial index, enum, data migration.
# 4. Jalankan
alembic upgrade head

# 5. Uji bisa dibalik
alembic downgrade -1 && alembic upgrade head
```

Langkah 3 bukan formalitas. Autogenerate sering menghasilkan `drop_table` lalu `create_table`
untuk perubahan yang sebenarnya kecil.

Langkah 5 juga bukan formalitas. Migrasi yang tidak bisa dibalik baru terasa saat sudah terlambat.

## Penamaan

| Objek | Pola | Contoh |
| --- | --- | --- |
| Tabel | jamak, snake_case, Inggris | `ledger_entries` |
| Index unik | `uq_` | `uq_proposal_aktif_per_umkm_per_campaign` |
| Check constraint | `ck_<tabel>_<maksud>` | `ck_ledger_amount_positif` |
| Foreign key | default Alembic | |

Nama constraint muncul di pesan `IntegrityError`, jadi nama yang jelas menghemat waktu saat
debugging.

## Test berjalan di Postgres

Bukan SQLite. Dialectnya berbeda di partial unique index, `CHECK`, `ON CONFLICT`, dan tipe
numerik. Test yang lolos di SQLite tapi jebol di Postgres memberi rasa aman palsu.

`docker-compose.yml` menyediakan `db-test` terpisah dari `db`, memakai `tmpfs`, sehingga test
cepat dan tidak menghapus data dev.

## Daftar periksa

- [ ] Kolom nominal memakai `sa_column=Column(BigInteger)`
- [ ] Constraint yang bisa ditegakkan database sudah ada di `__table_args__`
- [ ] Berkas migrasi dibaca, bukan hanya dihasilkan
- [ ] Partial index, enum, dan data migration ditulis tangan kalau ada
- [ ] `alembic downgrade -1 && alembic upgrade head` berhasil
- [ ] Nama constraint mengikuti pola
- [ ] Test ada yang membuktikan constraint benar-benar menolak, bukan hanya bahwa kolomnya ada
- [ ] `.claude/prd/09-data-model.md` diperbarui

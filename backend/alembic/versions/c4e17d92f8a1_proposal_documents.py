"""proposal documents

Revision ID: c4e17d92f8a1
Revises: 70b38e7b1a1e
Create Date: 2026-11-14

Uraian proposal pindah dari tiga textarea ke satu berkas PDF yang wajib
diunggah. Migrasi ini melakukan tiga hal sekaligus karena ketiganya satu
perubahan yang sama dan memisahkannya akan meninggalkan keadaan antara yang
tidak sah: tabel dokumen dibuat, `business_profile` disempitkan menjadi
`business_summary`, dan dua kolom narasi sisanya dibuang.

Tidak ada penyelamatan data lama pada `downgrade`, dan itu disengaja serta
perlu disebut: dokumen PDF tidak bisa dikembalikan menjadi tiga textarea,
jadi turun dari revisi ini mengembalikan bentuk tabelnya saja, bukan isinya.
Deployment ini satu-satunya yang ada dan datanya data demo yang di-seed
ulang, sehingga harga itu nyata tapi nol.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e17d92f8a1"
down_revision: Union[str, Sequence[str], None] = "70b38e7b1a1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Dieja di sini, tidak diimpor dari app.models: migrasi harus tetap berarti
# sama ketika kode aplikasinya sudah berubah jauh di masa depan.
MAX_DOCUMENT_BYTES = 5_242_880


def upgrade() -> None:
    op.create_table(
        "proposal_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["proposal_id"], ["proposals.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("proposal_id", name="uq_proposal_documents_proposal_id"),
        sa.CheckConstraint(
            f"byte_size > 0 AND byte_size <= {MAX_DOCUMENT_BYTES}",
            name="ck_proposal_documents_byte_size",
        ),
        sa.CheckConstraint("page_count > 0", name="ck_proposal_documents_page_count"),
    )

    # Urutannya penting: CHECK lama dibuang lebih dulu, karena ia menyebut
    # nama kolom yang sebentar lagi berganti dan Postgres akan ikut
    # mengganti namanya di dalam ekspresi constraint, meninggalkan aturan
    # "panjang antara 100 dan 5000" yang menempel pada field ringkasan yang
    # batas atasnya 500 -- setiap ringkasan yang sah akan ditolak database.
    op.drop_constraint(
        "ck_proposals_business_profile_length", "proposals", type_="check"
    )
    op.drop_constraint(
        "ck_proposals_fund_usage_plan_length", "proposals", type_="check"
    )
    op.drop_constraint(
        "ck_proposals_business_projection_length", "proposals", type_="check"
    )

    op.alter_column("proposals", "business_profile", new_column_name="business_summary")
    # Dipotong, bukan ditolak: baris lama memuat sampai 5.000 karakter dan
    # CHECK baru membatasi 500, jadi tanpa langkah ini migrasi gagal di
    # tengah pada database mana pun yang sudah berisi data.
    op.execute(
        "UPDATE proposals SET business_summary = left(business_summary, 500) "
        "WHERE length(business_summary) > 500"
    )
    op.create_check_constraint(
        "ck_proposals_business_summary_length",
        "proposals",
        "length(business_summary) BETWEEN 30 AND 500",
    )

    op.drop_column("proposals", "fund_usage_plan")
    op.drop_column("proposals", "business_projection")


def downgrade() -> None:
    # Teks penampung, bukan string kosong, dan panjangnya bukan kebetulan:
    # kedua kolom NOT NULL dan CHECK yang dipasang kembali di bawah menuntut
    # minimal 100 karakter, jadi penampung yang lebih pendek membuat
    # downgrade mati di tengah pada tabel yang ada isinya. Versi pertama
    # baris ini 69 karakter dan persis itu yang terjadi.
    penampung = (
        "Isi lama tidak tersedia. Proposal ini diajukan dalam bentuk dokumen PDF, "
        "dan dokumen itu tidak bisa dikembalikan menjadi isian teks per bagian."
    )
    op.add_column(
        "proposals",
        sa.Column(
            "fund_usage_plan", sa.String(), nullable=False, server_default=penampung
        ),
    )
    op.add_column(
        "proposals",
        sa.Column(
            "business_projection",
            sa.String(),
            nullable=False,
            server_default=penampung,
        ),
    )
    op.alter_column("proposals", "fund_usage_plan", server_default=None)
    op.alter_column("proposals", "business_projection", server_default=None)

    op.drop_constraint(
        "ck_proposals_business_summary_length", "proposals", type_="check"
    )
    op.alter_column("proposals", "business_summary", new_column_name="business_profile")
    op.execute(
        "UPDATE proposals SET business_profile = business_profile || ' ' || "
        f"'{penampung}' WHERE length(business_profile) < 100"
    )
    op.create_check_constraint(
        "ck_proposals_business_profile_length",
        "proposals",
        "length(business_profile) BETWEEN 100 AND 5000",
    )
    op.create_check_constraint(
        "ck_proposals_fund_usage_plan_length",
        "proposals",
        "length(fund_usage_plan) BETWEEN 100 AND 5000",
    )
    op.create_check_constraint(
        "ck_proposals_business_projection_length",
        "proposals",
        "length(business_projection) BETWEEN 50 AND 3000",
    )

    op.drop_table("proposal_documents")

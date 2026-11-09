"""bound text fields with check constraints

Lapisan kedua di belakang Field(max_length=...) di schemas/ (Task 3 review
keamanan: business_profile, fund_usage_plan, business_projection,
MilestoneReportIn.narrative, dan MilestoneRejectIn.note semua lolos sampai
5 MB sebelum ini, tanpa batas atas sama sekali). Pola yang sama dengan
ck_comments_body_length yang sudah ada (migrasi 152f14ae708d): batas
Pydantic saja bisa dilewati pemanggil yang menyusun baris langsung tanpa
lewat skema (fixture test, service lain, migrasi data), batas database tidak.

`reject_milestone` (services/milestone.py) menerima `note` sebagai `str`
polos, bukan `MilestoneRejectIn` -- pemanggil non-HTTP yang melompati
schemas/milestone.py sama sekali masih tertahan lewat CHECK ini.

Revision ID: a061fd4c5ee6
Revises: 78b36c0cb4dc
Create Date: 2026-11-09 18:09:27.666797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a061fd4c5ee6'
down_revision: Union[str, Sequence[str], None] = '78b36c0cb4dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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
    op.create_check_constraint(
        "ck_milestone_reports_narrative_length",
        "milestone_reports",
        "length(narrative) BETWEEN 50 AND 5000",
    )
    # reviewer_note nullable (hanya wajib saat rejected, BR-45): CHECK harus
    # tetap meloloskan NULL, bukan hanya rentang panjangnya.
    op.create_check_constraint(
        "ck_milestone_reports_reviewer_note_length",
        "milestone_reports",
        "reviewer_note IS NULL OR length(reviewer_note) BETWEEN 10 AND 2000",
    )
    op.create_check_constraint(
        "ck_users_name_length",
        "users",
        "length(name) BETWEEN 1 AND 120",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_users_name_length", "users", type_="check")
    op.drop_constraint(
        "ck_milestone_reports_reviewer_note_length", "milestone_reports", type_="check"
    )
    op.drop_constraint(
        "ck_milestone_reports_narrative_length", "milestone_reports", type_="check"
    )
    op.drop_constraint(
        "ck_proposals_business_projection_length", "proposals", type_="check"
    )
    op.drop_constraint("ck_proposals_fund_usage_plan_length", "proposals", type_="check")
    op.drop_constraint(
        "ck_proposals_business_profile_length", "proposals", type_="check"
    )

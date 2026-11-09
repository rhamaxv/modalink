"""BR-64 dan BR-50: dua deadline dan nominal ditegakkan sebagai CHECK di database."""

from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.clock import SystemClock
from app.models.campaign import Campaign, CampaignStatus, Sector

SEKARANG = SystemClock().now()


async def test_br64_funding_deadline_must_be_after_apply_deadline(db, investor):
    db.add(
        Campaign(
            investor_id=investor.user.id,
            title="Modal warung",
            description="x" * 60,
            sector=Sector.KULINER,
            target_amount=50_000_000,
            apply_deadline=SEKARANG + timedelta(days=10),
            funding_deadline=SEKARANG + timedelta(days=5),  # lebih awal, harus ditolak
            score_threshold=60,
            status=CampaignStatus.OPEN,
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_target_amount_must_be_positive(db, investor):
    db.add(
        Campaign(
            investor_id=investor.user.id,
            title="x",
            description="x" * 60,
            sector=Sector.KULINER,
            target_amount=0,
            apply_deadline=SEKARANG + timedelta(days=5),
            funding_deadline=SEKARANG + timedelta(days=10),
            score_threshold=60,
            status=CampaignStatus.OPEN,
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()

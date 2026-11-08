from datetime import UTC, datetime, timedelta

from app.domain.clock import FrozenClock, SystemClock, VirtualClock


def test_system_clock_mengembalikan_waktu_aware():
    assert SystemClock().now().tzinfo is not None


def test_frozen_clock_selalu_mengembalikan_waktu_yang_sama():
    saat = datetime(2026, 11, 7, 10, 0, tzinfo=UTC)
    clock = FrozenClock(saat)
    assert clock.now() == saat == clock.now()


def test_virtual_clock_maju_sesuai_offset():
    dasar = FrozenClock(datetime(2026, 11, 7, tzinfo=UTC))
    virtual = VirtualClock(dasar, offset=timedelta(days=30))
    assert virtual.now() == datetime(2026, 12, 7, tzinfo=UTC)

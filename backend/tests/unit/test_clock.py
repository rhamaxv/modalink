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


class _JamDasarBergerak:
    """Jam dasar yang nilainya berubah setiap now() dipanggil.

    FrozenClock tidak bisa membuktikan VirtualClock membaca ulang base.now() di
    setiap pemanggilan: implementasi yang salah (menyimpan base.now() sekali di
    __init__) tetap lolos kalau base-nya selalu mengembalikan nilai yang sama.
    """

    def __init__(self, urutan_waktu: list[datetime]) -> None:
        self._sisa = iter(urutan_waktu)

    def now(self) -> datetime:
        return next(self._sisa)


def test_virtual_clock_ikut_bergerak_saat_jam_dasar_berubah():
    dasar = _JamDasarBergerak(
        [
            datetime(2026, 11, 7, tzinfo=UTC),
            datetime(2026, 11, 8, tzinfo=UTC),
        ]
    )
    virtual = VirtualClock(dasar, offset=timedelta(days=30))
    assert virtual.now() == datetime(2026, 12, 7, tzinfo=UTC)
    assert virtual.now() == datetime(2026, 12, 8, tzinfo=UTC)

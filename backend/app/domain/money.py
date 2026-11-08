"""Rupiah selalu integer penuh. Tidak ada sen, tidak ada float (BR-50)."""

Rupiah = int

MAX_RUPIAH = 9_223_372_036_854_775_807  # batas BIGINT Postgres


def parse_rupiah(value: object) -> Rupiah:
    # bool adalah subclass int di Python, jadi tanpa pengecualian ini
    # parse_rupiah(True) diam-diam menghasilkan 1. ValueError, bukan TypeError
    # (noqa di bawah), karena fungsi ini dipanggil dari field validator
    # Pydantic, yang hanya menangkap ValueError sebagai error validasi.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Nominal harus berupa bilangan bulat rupiah, tanpa desimal.")  # noqa: TRY004
    if value <= 0:
        raise ValueError("Nominal harus lebih besar dari nol.")
    if value > MAX_RUPIAH:
        raise ValueError("Nominal terlalu besar.")
    return value


def format_rupiah(amount: Rupiah) -> str:
    return f"Rp{amount:,}".replace(",", ".")

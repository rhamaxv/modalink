"""Membagi sisa dana yang belum cair ke para investor, proporsional kontribusi.

Dipakai saat UMKM berhenti di tengah jalan: sebagian dana sudah dicairkan per
milestone, sisanya harus kembali ke investor. Fungsi di sini hanya menghitung
nominalnya; yang menuliskan baris `refund_out` ke ledger adalah layer services.

Keluaran dijumlahkan ke `sisa` secara persis. Ledger di produk ini append-only
dan saldonya hasil penjumlahan baris, jadi selisih satu rupiah tidak bisa
diperbaiki dengan UPDATE: ia tertinggal di saldo selamanya atau menjadi uang
yang tidak pernah ada.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.domain.money import Rupiah


@dataclass(frozen=True, slots=True)
class KontribusiPledge:
    pledge_id: UUID
    investor_id: UUID
    amount: Rupiah


def bagi_sisa_pro_rata(
    kontribusi: Sequence[KontribusiPledge], sisa: Rupiah
) -> dict[UUID, Rupiah]:
    """Mengembalikan {pledge_id: nominal refund}."""
    if sisa < 0:
        raise ValueError("Sisa dana yang dikembalikan tidak boleh negatif.")

    total = 0
    for k in kontribusi:
        if k.amount < 0:
            raise ValueError("Kontribusi pledge tidak boleh negatif.")
        total += k.amount

    if sisa > total:
        raise ValueError(
            "Sisa dana yang dikembalikan melebihi total kontribusi: "
            f"{sisa} dari {total}."
        )

    # pledge_id ganda akan saling menimpa di dict keluaran, dan uang milik salah
    # satu baris hilang tanpa error apa pun. Lebih baik berhenti di sini.
    if len({k.pledge_id for k in kontribusi}) != len(kontribusi):
        raise ValueError("Ada pledge_id yang muncul lebih dari sekali.")

    if not kontribusi:
        return {}
    if sisa == 0 or total == 0:
        return dict.fromkeys((k.pledge_id for k in kontribusi), 0)

    # Largest remainder (Hare quota). Bagian dasar dihitung dengan pembagian
    # bilangan bulat, lalu rupiah yang tersisa karena pembulatan ke bawah
    # dibagikan satu-satu. Float tidak dipakai sama sekali: pada nominal
    # ratusan miliar, 53 bit mantissa double sudah tidak cukup untuk membedakan
    # dua pembagian yang berbeda satu rupiah.
    bagian: dict[UUID, Rupiah] = {}
    # Pembilang sisa pembagian: (sisa * amount) mod total. Nilai inilah
    # "pecahan rupiah" yang terpotong, disimpan sebagai integer agar
    # perbandingannya tepat.
    remainder: dict[UUID, int] = {}
    for k in kontribusi:
        hak = sisa * k.amount
        bagian[k.pledge_id] = hak // total
        remainder[k.pledge_id] = hak % total

    kurang = sisa - sum(bagian.values())

    # Yang pecahan terpotongnya paling besar menerima rupiah tambahan lebih
    # dulu: itu yang membuat hasilnya paling dekat ke porsi sebenarnya. Seri
    # diputus oleh amount terbesar, lalu pledge_id terkecil. Keduanya melekat
    # pada datanya, bukan pada urutan masukan, sehingga daftar yang sama dengan
    # urutan berbeda menghasilkan pembagian yang sama.
    urutan = sorted(
        kontribusi, key=lambda k: (-remainder[k.pledge_id], -k.amount, k.pledge_id)
    )
    for k in urutan[:kurang]:
        bagian[k.pledge_id] += 1

    return bagian

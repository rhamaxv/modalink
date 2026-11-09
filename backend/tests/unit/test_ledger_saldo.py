from app.models.ledger import EntryType as T
from app.services.ledger import LedgerEntrySummary, compute_balance, total_raised


def e(tipe, jumlah):
    return LedgerEntrySummary(entry_type=tipe, amount=jumlah)


def test_br52_saldo_dijumlahkan_dari_entri():
    entri = [
        e(T.PLEDGE_IN, 5_000_000),
        e(T.PLEDGE_IN, 5_000_000),
        e(T.DISBURSEMENT_OUT, 3_000_000),
    ]
    assert compute_balance(entri) == 7_000_000


def test_br52_refund_mengurangi_saldo():
    entri = [e(T.PLEDGE_IN, 5_000_000), e(T.REFUND_OUT, 5_000_000)]
    assert compute_balance(entri) == 0


def test_total_terkumpul_hanya_menghitung_pledge_dikurangi_refund():
    entri = [
        e(T.PLEDGE_IN, 10_000_000),
        e(T.REFUND_OUT, 2_000_000),
        e(T.DISBURSEMENT_OUT, 4_000_000),
    ]
    assert total_raised(entri) == 8_000_000  # pencairan tidak mengurangi yang terkumpul
    assert compute_balance(entri) == 4_000_000


def test_saldo_kosong_adalah_nol():
    assert compute_balance([]) == 0

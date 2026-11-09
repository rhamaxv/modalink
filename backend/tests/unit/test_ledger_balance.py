from app.models.ledger import EntryType as T
from app.services.ledger import LedgerEntrySummary, compute_balance, total_raised


def e(tipe, jumlah):
    return LedgerEntrySummary(entry_type=tipe, amount=jumlah)


def test_br52_balance_is_summed_from_entries():
    entri = [
        e(T.PLEDGE_IN, 5_000_000),
        e(T.PLEDGE_IN, 5_000_000),
        e(T.DISBURSEMENT_OUT, 3_000_000),
    ]
    assert compute_balance(entri) == 7_000_000


def test_br52_refund_reduces_balance():
    entri = [e(T.PLEDGE_IN, 5_000_000), e(T.REFUND_OUT, 5_000_000)]
    assert compute_balance(entri) == 0


def test_total_raised_only_counts_pledges_minus_refunds():
    entri = [
        e(T.PLEDGE_IN, 10_000_000),
        e(T.REFUND_OUT, 2_000_000),
        e(T.DISBURSEMENT_OUT, 4_000_000),
    ]
    assert total_raised(entri) == 8_000_000  # pencairan tidak mengurangi yang terkumpul
    assert compute_balance(entri) == 4_000_000


def test_empty_balance_is_zero():
    assert compute_balance([]) == 0

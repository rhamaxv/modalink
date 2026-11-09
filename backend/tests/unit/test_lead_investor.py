from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.domain.lead_investor import PledgeSummary, pick_lead_investor

T0 = datetime(2026, 11, 7, tzinfo=UTC)
A, B = uuid4(), uuid4()


def test_tidak_ada_pledge_berarti_tidak_ada_lead():
    assert pick_lead_investor([]) is None


def test_br23_pledge_terbesar_jadi_lead():
    pledges = [PledgeSummary(A, 3_000_000, T0), PledgeSummary(B, 7_000_000, T0)]
    assert pick_lead_investor(pledges) == B


def test_br24_beberapa_pledge_dari_investor_sama_dijumlahkan():
    pledges = [
        PledgeSummary(A, 4_000_000, T0),
        PledgeSummary(A, 4_000_000, T0 + timedelta(minutes=1)),
        PledgeSummary(B, 7_000_000, T0),
    ]
    assert pick_lead_investor(pledges) == A  # 8 juta mengalahkan 7 juta


def test_br23_seri_dimenangkan_pledge_paling_awal():
    pledges = [
        PledgeSummary(B, 5_000_000, T0 + timedelta(minutes=5)),
        PledgeSummary(A, 5_000_000, T0),
    ]
    assert pick_lead_investor(pledges) == A

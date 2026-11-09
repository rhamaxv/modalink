"""Laporan progres milestone dan jejak revisinya (BR-41 sampai BR-46, T-30, T-31).

`funded_proposal` (lewat `listed_proposal` di conftest.py) dimiliki
`umkm_lain`, bukan `umkm`: lihat docstring fixture itu soal BR-13. Karena itu
test di sini memakai `umkm_lain` sebagai pemilik yang melapor, dan `umkm`
sebagai UMKM lain yang harus ditolak.
"""

from sqlalchemy import desc
from sqlmodel import select

from app.models.milestone_report import MilestoneReport, ReportStatus


def body_laporan(**ubah):
    return {
        "narrative": "Mesin kopi sudah dibeli dan dipasang. "
        "Omzet minggu pertama naik 15 persen.",
        "metrics": {"omzet_minggu_1": 3_200_000},
    } | ubah


async def cairkan_lewat_api(client, investor, milestone):
    return await client.post(
        f"/api/v1/milestones/{milestone.id}/approve", headers=investor.headers
    )


async def laporan_terakhir(db, milestone_id):
    return await db.scalar(
        select(MilestoneReport)
        .where(MilestoneReport.milestone_id == milestone_id)
        .order_by(desc("submitted_at"))
        .limit(1)
    )


async def test_umkm_can_report_second_milestone(
    client, umkm_lain, investor, funded_proposal
):
    m1, m2 = funded_proposal.milestones
    await cairkan_lewat_api(client, investor, m1)
    res = await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json=body_laporan(),
    )
    assert res.status_code == 201


async def test_br41_first_milestone_cannot_be_reported(
    client, umkm_lain, funded_proposal
):
    m1 = funded_proposal.milestones[0]
    res = await client.post(
        f"/api/v1/milestones/{m1.id}/reports",
        headers=umkm_lain.headers,
        json=body_laporan(),
    )
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "milestone_pertama_tanpa_laporan"


async def test_br43_second_milestone_report_before_first_disbursed_rejected(
    client, umkm_lain, funded_proposal
):
    m2 = funded_proposal.milestones[1]
    res = await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json=body_laporan(),
    )
    assert res.status_code == 409


async def test_br46_rejected_report_kept_and_revision_is_new_row(
    client, db, umkm_lain, investor, funded_proposal
):
    m1, m2 = funded_proposal.milestones
    await cairkan_lewat_api(client, investor, m1)

    await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json=body_laporan(),
    )
    await client.post(
        f"/api/v1/milestones/{m2.id}/reject",
        headers=investor.headers,
        json={"note": "Angka omzet belum disertai bukti."},
    )
    await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm_lain.headers,
        json=body_laporan(narrative="Revisi: bukti terlampir." + "x" * 40),
    )

    laporan = (
        await db.scalars(
            select(MilestoneReport)
            .where(MilestoneReport.milestone_id == m2.id)
            .order_by(MilestoneReport.submitted_at)
        )
    ).all()
    assert len(laporan) == 2
    assert laporan[0].review_status is ReportStatus.REJECTED
    assert laporan[0].reviewer_note == "Angka omzet belum disertai bukti."
    assert laporan[1].review_status is ReportStatus.PENDING


async def test_t30_approve_marks_report_approved(
    client, db, investor, milestone_reported
):
    await client.post(
        f"/api/v1/milestones/{milestone_reported.id}/approve", headers=investor.headers
    )
    laporan = await laporan_terakhir(db, milestone_reported.id)
    assert laporan.review_status is ReportStatus.APPROVED
    assert laporan.reviewed_by == investor.user.id


async def test_t31_reject_marks_report_rejected_with_note(
    client, db, investor, milestone_reported
):
    await client.post(
        f"/api/v1/milestones/{milestone_reported.id}/reject",
        headers=investor.headers,
        json={"note": "Angka omzet belum disertai bukti."},
    )
    laporan = await laporan_terakhir(db, milestone_reported.id)
    assert laporan.review_status is ReportStatus.REJECTED
    assert laporan.reviewer_note == "Angka omzet belum disertai bukti."
    assert laporan.reviewed_at is not None


async def test_br45_reject_without_note_returns_422(
    client, investor, milestone_reported
):
    res = await client.post(
        f"/api/v1/milestones/{milestone_reported.id}/reject",
        headers=investor.headers,
        json={"note": "x"},
    )
    assert res.status_code == 422


async def test_other_umkm_cannot_report(client, umkm, funded_proposal):
    m2 = funded_proposal.milestones[1]
    res = await client.post(
        f"/api/v1/milestones/{m2.id}/reports",
        headers=umkm.headers,
        json=body_laporan(),
    )
    assert res.status_code in {403, 404}

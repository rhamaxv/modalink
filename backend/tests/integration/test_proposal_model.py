import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.transitions import ProposalStatus


async def test_br13_umkm_tidak_bisa_punya_dua_proposal_aktif_di_campaign_sama(
    db, umkm, campaign, buat_proposal
):
    await buat_proposal(status=ProposalStatus.LISTED)
    with pytest.raises(IntegrityError):
        await buat_proposal(status=ProposalStatus.SUBMITTED)


@pytest.mark.parametrize(
    "status_mati", [ProposalStatus.REJECTED, ProposalStatus.FAILED]
)
async def test_br13_proposal_yang_sudah_mati_tidak_menghalangi_pengajuan_baru(
    db, buat_proposal, status_mati
):
    await buat_proposal(status=status_mati)
    await buat_proposal(status=ProposalStatus.SUBMITTED)  # harus lolos

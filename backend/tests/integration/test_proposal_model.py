import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.transitions import ProposalStatus


async def test_br13_umkm_cannot_have_two_active_proposals_in_same_campaign(
    db, umkm, campaign, buat_proposal
):
    await buat_proposal(status=ProposalStatus.LISTED)
    with pytest.raises(IntegrityError):
        await buat_proposal(status=ProposalStatus.SUBMITTED)


@pytest.mark.parametrize(
    "status_mati", [ProposalStatus.REJECTED, ProposalStatus.FAILED]
)
async def test_br13_dead_proposal_does_not_block_new_submission(
    db, buat_proposal, status_mati
):
    await buat_proposal(status=status_mati)
    await buat_proposal(status=ProposalStatus.SUBMITTED)  # harus lolos

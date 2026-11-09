"""Endpoint vote dan komentar komunitas (BR-30 sampai BR-34)."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_clock, get_own_comment, require_role
from app.db.session import get_session
from app.domain.clock import Clock
from app.errors import NotFoundError
from app.models.comment import Comment
from app.models.user import Role, User
from app.schemas.community import CommentIn, CommentListOut, CommentOut, VoteOut
from app.services.community import (
    create_comment,
    delete_comment,
    list_comments,
    toggle_vote,
)
from app.services.proposal import get_proposal

router = APIRouter(tags=["community"])


@router.post("/api/v1/proposals/{proposal_id}/vote", response_model=VoteOut)
async def toggle_vote_endpoint(
    proposal_id: UUID,
    community: User = Depends(require_role(Role.COMMUNITY)),
    session: AsyncSession = Depends(get_session),
) -> VoteOut:
    proposal = await get_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    voted, jumlah = await toggle_vote(session, community, proposal)
    return VoteOut(voted=voted, vote_count=jumlah)


@router.get("/api/v1/proposals/{proposal_id}/comments", response_model=CommentListOut)
async def list_comments_endpoint(
    proposal_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> CommentListOut:
    return CommentListOut(items=await list_comments(session, proposal_id))


@router.post(
    "/api/v1/proposals/{proposal_id}/comments",
    status_code=status.HTTP_201_CREATED,
    response_model=CommentOut,
)
async def create_comment_endpoint(
    proposal_id: UUID,
    body: CommentIn,
    community: User = Depends(require_role(Role.COMMUNITY)),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> Comment:
    proposal = await get_proposal(session, proposal_id)
    if proposal is None:
        raise NotFoundError("proposal_tidak_ada", "Proposal tidak ditemukan.")
    return await create_comment(session, community, proposal, body.body, clock)


@router.delete("/api/v1/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment_endpoint(
    komentar: Comment = Depends(get_own_comment),
    session: AsyncSession = Depends(get_session),
    clock: Clock = Depends(get_clock),
) -> None:
    await delete_comment(session, komentar, clock)

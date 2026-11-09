"""Skema request/response vote dan komentar komunitas (BR-30 sampai BR-34)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, StringConstraints


class VoteOut(BaseModel):
    voted: bool
    vote_count: int


# strip_whitespace=True: komentar yang isinya cuma spasi harus ditolak sebagai
# kosong (BR-33), bukan lolos sebagai string " ". max_length=500 dihitung per
# karakter oleh Pydantic, bukan per byte, jadi emoji tetap dihitung satu.
CommentBody = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


class CommentIn(BaseModel):
    body: CommentBody


class CommentOut(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    proposal_id: UUID
    user_id: UUID
    body: str
    created_at: datetime


class CommentListOut(BaseModel):
    items: list[CommentOut]

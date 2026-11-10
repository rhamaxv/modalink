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
    # Jumlah dukungan ikut di amplop ini, dan itu memperbaiki keadaan yang
    # terlihat rusak di layar. Sebelumnya satu-satunya sumber vote_count
    # adalah respons POST /vote, jadi pengunjung yang belum pernah menekan
    # tombolnya selalu membaca "Jumlah dukungan belum tersedia" -- termasuk
    # pengunjung yang memang tidak boleh memberi dukungan sama sekali, yang
    # berarti angka itu tidak pernah muncul untuk mereka.
    vote_count: int
    # None untuk pengunjung anonim: "belum diketahui", bukan "belum memberi
    # dukungan". Keduanya berbeda, dan menyamakannya membuat tombol vote
    # menyatakan aria-pressed="false" untuk orang yang bahkan tidak punya akun.
    voted_by_me: bool | None = None

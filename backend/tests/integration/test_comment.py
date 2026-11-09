"""Komentar komunitas: 500 karakter, soft delete, hanya penulis yang bisa
menghapus (BR-33, BR-34)."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.comment import Comment


async def test_br33_database_check_also_rejects_comment_over_500(
    db, community, listed_proposal
):
    """Lapisan pertama (StringConstraints di schemas/community.py) hanya
    menjaga pintu HTTP. Baris yang ditulis lewat jalur lain -- migrasi data,
    service lain yang lupa lewat CommentIn -- harus tetap ditolak database,
    bukan lolos diam-diam. Dibuktikan dengan fault injection: menaikkan
    max_length Pydantic ke 5000 tidak membuat body 501 karakter lolos
    tersimpan, constraint database ini yang menahannya."""
    db.add(
        Comment(
            proposal_id=listed_proposal.id, user_id=community.user.id, body="x" * 501
        )
    )
    with pytest.raises(IntegrityError):
        await db.flush()


async def test_community_can_comment(client, community, listed_proposal):
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/comments",
        headers=community.headers,
        json={"body": "Semoga warungnya makin ramai."},
    )
    assert res.status_code == 201


async def test_br33_comment_over_500_characters_rejected(
    client, community, listed_proposal
):
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/comments",
        headers=community.headers,
        json={"body": "x" * 501},
    )
    assert res.status_code == 422


async def test_br33_empty_comment_rejected(client, community, listed_proposal):
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/comments",
        headers=community.headers,
        json={"body": "   "},
    )
    assert res.status_code == 422


async def test_br34_only_author_can_delete(
    client, community, community_lain, listed_proposal
):
    # Dua akun komunitas sungguhan, bukan satu: menghapus komentar milik
    # sendiri lolos dengan guard apa pun, termasuk yang tidak memeriksa
    # kepemilikan sama sekali. Akun kedua yang membuktikan BR-34 benar-benar
    # menolak.
    buat = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/comments",
        headers=community.headers,
        json={"body": "Semangat."},
    )
    cid = buat.json()["id"]
    assert (
        await client.delete(f"/api/v1/comments/{cid}", headers=community_lain.headers)
    ).status_code == 403
    assert (
        await client.delete(f"/api/v1/comments/{cid}", headers=community.headers)
    ).status_code == 204


async def test_deleted_comment_does_not_appear_in_list(
    client, community, listed_proposal
):
    buat = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/comments",
        headers=community.headers,
        json={"body": "Semangat."},
    )
    await client.delete(
        f"/api/v1/comments/{buat.json()['id']}", headers=community.headers
    )
    daftar = await client.get(f"/api/v1/proposals/{listed_proposal.id}/comments")
    assert daftar.json()["items"] == []


async def test_br05_comment_readable_publicly_without_token(
    client, community, listed_proposal
):
    await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/comments",
        headers=community.headers,
        json={"body": "Semangat."},
    )
    assert (
        await client.get(f"/api/v1/proposals/{listed_proposal.id}/comments")
    ).status_code == 200


async def test_long_comment_with_emoji_counted_by_character_not_byte(
    client, community, listed_proposal
):
    """500 karakter emoji adalah 2000 byte. Batas dihitung per karakter."""
    res = await client.post(
        f"/api/v1/proposals/{listed_proposal.id}/comments",
        headers=community.headers,
        json={"body": "🙂" * 500},
    )
    assert res.status_code == 201

"""Media intake: image-only, album reject, single-flight shell."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kolobot.handlers.media import MediaHandler


def _make_photo_message(user_id: int = 100, file_size: int = 50_000):
    """Simulate a Telegram photo message (largest size)."""
    photo_size = SimpleNamespace(
        file_id="photo_fid_123",
        file_unique_id="photo_uid_123",
        file_size=file_size,
        width=1920,
        height=1080,
    )
    msg = MagicMock()
    msg.from_user = SimpleNamespace(id=user_id)
    msg.photo = [
        SimpleNamespace(file_id="small", file_unique_id="s", file_size=1000, width=320, height=240),
        photo_size,
    ]
    msg.document = None
    msg.media_group_id = None
    msg.answer = AsyncMock()
    msg.bot = MagicMock()
    msg.bot.download = AsyncMock(return_value=b"image-bytes")
    return msg


def _make_doc_message(mime: str = "image/jpeg", file_size: int = 50_000):
    doc = SimpleNamespace(
        file_id="doc_fid_456",
        file_unique_id="doc_uid_456",
        file_size=file_size,
        mime_type=mime,
        file_name="receipt.jpg",
    )
    msg = MagicMock()
    msg.from_user = SimpleNamespace(id=100)
    msg.photo = None
    msg.document = doc
    msg.media_group_id = None
    msg.answer = AsyncMock()
    msg.bot = MagicMock()
    msg.bot.download = AsyncMock(return_value=b"doc-bytes")
    return msg


def _make_album_message(group_id: str = "album-1"):
    msg = _make_photo_message()
    msg.media_group_id = group_id
    return msg


@pytest.fixture
def handler():
    file_store = MagicMock()
    file_store.save_tmp = MagicMock(return_value="/tmp/fake.jpg")
    return MediaHandler(file_store=file_store, owner_user_id=100)


@pytest.mark.asyncio
async def test_photo_accepted_uses_largest_size(handler: MediaHandler):
    msg = _make_photo_message()
    result = await handler.handle_media(msg)
    assert result is not None
    assert result["file_id"] == "photo_fid_123"
    assert result["file_unique_id"] == "photo_uid_123"


@pytest.mark.asyncio
async def test_image_document_accepted(handler: MediaHandler):
    msg = _make_doc_message(mime="image/png")
    result = await handler.handle_media(msg)
    assert result is not None
    assert result["file_id"] == "doc_fid_456"


@pytest.mark.asyncio
async def test_non_image_document_rejected(handler: MediaHandler):
    msg = _make_doc_message(mime="application/zip")
    result = await handler.handle_media(msg)
    assert result is None
    msg.answer.assert_awaited_once()
    text = msg.answer.await_args.args[0].lower()
    assert "зображ" in text or "image" in text


@pytest.mark.asyncio
async def test_oversize_image_rejected(handler: MediaHandler):
    msg = _make_photo_message(file_size=25_000_000)
    result = await handler.handle_media(msg)
    assert result is None
    msg.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_album_rejected_with_single_debounced_reply(handler: MediaHandler):
    m1 = _make_album_message("grp-1")
    m2 = _make_album_message("grp-1")

    r1 = await handler.handle_media(m1)
    r2 = await handler.handle_media(m2)

    assert r1 is None
    assert r2 is None
    # Only one reply for the group
    total_answers = m1.answer.await_count + m2.answer.await_count
    assert total_answers == 1


@pytest.mark.asyncio
async def test_single_flight_rejects_second_image_while_pending(handler: MediaHandler):
    msg1 = _make_photo_message()
    r1 = await handler.handle_media(msg1)
    assert r1 is not None

    # Slot is held; second image should be rejected
    msg2 = _make_photo_message()
    r2 = await handler.handle_media(msg2)
    assert r2 is None
    msg2.answer.assert_awaited_once()
    text = msg2.answer.await_args.args[0].lower()
    assert "зберегти" in text or "відхил" in text or "закінч" in text or "поточн" in text


@pytest.mark.asyncio
async def test_clear_pending_allows_new_upload(handler: MediaHandler):
    msg1 = _make_photo_message()
    await handler.handle_media(msg1)

    handler.clear_pending()

    msg2 = _make_photo_message()
    r2 = await handler.handle_media(msg2)
    assert r2 is not None

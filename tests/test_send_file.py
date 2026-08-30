"""Tests for send_archive_file helper and document/photo downloading fallback logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import FSInputFile

from kolobot.main import send_archive_file


def _make_mock_message():
    msg = MagicMock()
    msg.answer = AsyncMock()
    msg.answer_photo = AsyncMock()
    msg.answer_document = AsyncMock()
    return msg


def _make_mock_file_store(path_return: str | None = None):
    fs = MagicMock()
    fs.get_final_path = MagicMock(return_value=path_return)
    return fs


@pytest.mark.asyncio
async def test_send_archive_file_photo_file_id_success():
    msg = _make_mock_message()
    fs = _make_mock_file_store()
    metadata = {
        "telegram_file_id": "photo_fid_123",
        "source": "photo",
        "mime": "image/jpeg",
    }

    res = await send_archive_file(
        message=msg,
        file_store=fs,
        doc_id="doc1",
        metadata=metadata,
    )

    assert res is True
    msg.answer_photo.assert_awaited_once_with("photo_fid_123")
    msg.answer_document.assert_not_called()
    msg.answer.assert_not_called()


@pytest.mark.asyncio
async def test_send_archive_file_doc_file_id_success():
    msg = _make_mock_message()
    fs = _make_mock_file_store()
    metadata = {
        "telegram_file_id": "doc_fid_456",
        "source": "document",
        "mime": "image/png",
    }

    res = await send_archive_file(
        message=msg,
        file_store=fs,
        doc_id="doc2",
        metadata=metadata,
    )

    assert res is True
    msg.answer_document.assert_awaited_once_with("doc_fid_456")
    msg.answer_photo.assert_not_called()
    msg.answer.assert_not_called()


@pytest.mark.asyncio
async def test_send_archive_file_fallback_on_telegram_error():
    msg = _make_mock_message()
    # answer_photo with fid raises error (e.g. photo file_id rejected or expired)
    msg.answer_photo.side_effect = [Exception("Bad Request: wrong file id"), None]

    fs = _make_mock_file_store(path_return="/downloads/doc1.jpg")
    metadata = {
        "telegram_file_id": "bad_fid",
        "source": "photo",
        "mime": "image/jpeg",
    }

    res = await send_archive_file(
        message=msg,
        file_store=fs,
        doc_id="doc1",
        metadata=metadata,
    )

    assert res is True
    assert msg.answer_photo.await_count == 2
    # Second call uses FSInputFile
    second_arg = msg.answer_photo.await_args_list[1].args[0]
    assert isinstance(second_arg, FSInputFile)
    assert second_arg.path == "/downloads/doc1.jpg"


@pytest.mark.asyncio
async def test_send_archive_file_fallback_when_file_id_missing():
    msg = _make_mock_message()
    fs = _make_mock_file_store(path_return="/downloads/doc2.png")
    metadata = {
        "telegram_file_id": "",
        "source": "document",
        "mime": "image/png",
    }

    res = await send_archive_file(
        message=msg,
        file_store=fs,
        doc_id="doc2",
        metadata=metadata,
    )

    assert res is True
    msg.answer_document.assert_awaited_once()
    arg = msg.answer_document.await_args.args[0]
    assert isinstance(arg, FSInputFile)
    assert arg.path == "/downloads/doc2.png"


@pytest.mark.asyncio
async def test_send_archive_file_candidate_extension_fallback():
    msg = _make_mock_message()
    fs = MagicMock()
    # First call with .png returns None, second call with .jpg returns path
    fs.get_final_path.side_effect = lambda doc_id, ext: "/downloads/doc4.jpg" if ext == ".jpg" else None
    metadata = {
        "telegram_file_id": "",
        "source": "photo",
        "mime": "image/png",
    }

    res = await send_archive_file(
        message=msg,
        file_store=fs,
        doc_id="doc4",
        metadata=metadata,
    )

    assert res is True
    msg.answer_photo.assert_awaited_once()
    arg = msg.answer_photo.await_args.args[0]
    assert isinstance(arg, FSInputFile)
    assert arg.path == "/downloads/doc4.jpg"


@pytest.mark.asyncio
async def test_send_archive_file_total_failure_reports_error():
    msg = _make_mock_message()
    msg.answer_document.side_effect = Exception("Telegram API error")
    fs = _make_mock_file_store(path_return=None)
    metadata = {
        "telegram_file_id": "expired_fid",
        "source": "document",
        "mime": "image/jpeg",
    }

    res = await send_archive_file(
        message=msg,
        file_store=fs,
        doc_id="doc3",
        metadata=metadata,
        error_text="Custom error message",
    )

    assert res is False
    msg.answer.assert_awaited_once_with("Custom error message")

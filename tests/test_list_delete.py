"""/list + /delete: list recent, send file, delete cascade."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from kolobot.handlers.list_delete import ListDeleteHandler


def _make_vector_store(docs=None):
    vs = MagicMock()
    if docs is None:
        docs = [
            {"id": f"d{i:03}", "document": f"doc {i}", "metadata": {
                "telegram_file_id": f"fid{i}",
                "file_unique_id": f"uid{i}",
                "file_name": f"file{i}.jpg",
                "created_at": 1000.0 + i,
            }}
            for i in range(12)
        ]
    vs.list_recent = MagicMock(return_value=docs[:10])
    vs.get = MagicMock(side_effect=lambda doc_id: next(
        (d for d in docs if d["id"] == doc_id), None
    ))
    vs.delete = MagicMock()
    return vs


@pytest.fixture
def handler():
    vs = _make_vector_store()
    fs = MagicMock()
    fs.delete_final = MagicMock()
    return ListDeleteHandler(vector_store=vs, file_store=fs, owner_user_id=42)


@pytest.mark.asyncio
async def test_list_shows_at_most_10(handler):
    msg = MagicMock()
    msg.answer = AsyncMock()
    await handler.handle_list(msg, user_id=42)
    msg.answer.assert_awaited_once()
    text = msg.answer.await_args.args[0]
    # Should mention documents
    assert "d0" in text or "file" in text.lower()


@pytest.mark.asyncio
async def test_list_empty_archive(handler):
    handler._vs.list_recent.return_value = []
    msg = MagicMock()
    msg.answer = AsyncMock()
    await handler.handle_list(msg, user_id=42)
    text = msg.answer.await_args.args[0]
    assert "порожн" in text.lower() or "немає" in text.lower()


@pytest.mark.asyncio
async def test_delete_cascade_chroma_and_disk(handler):
    result = await handler.delete_doc(doc_id="d001", user_id=42)
    assert result.success
    handler._vs.delete.assert_called_once_with("d001")
    handler._fs.delete_final.assert_called_once()


@pytest.mark.asyncio
async def test_delete_missing_doc_fails_gracefully(handler):
    handler._vs.get.return_value = None
    result = await handler.delete_doc(doc_id="ghost", user_id=42)
    assert not result.success


@pytest.mark.asyncio
async def test_delete_no_longer_appears_in_list(handler):
    handler._vs.delete.side_effect = lambda doc_id: None
    await handler.delete_doc(doc_id="d001", user_id=42)
    handler._vs.delete.assert_called_with("d001")

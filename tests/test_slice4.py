"""Unit and integration tests for Slice-4 (Issue #15):
Smart Polling, Retry button, POST /api/warehouse/documents/{id}/retry, and batch media deduplication.
"""

from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiohttp.test_utils import TestClient, TestServer
from aiogram.types import InlineKeyboardMarkup, Message, Update

from kolobot.doc_structurer import DocStructurer, Document
from kolobot.log_service import LogBuffer
from kolobot.main import build_app
from kolobot.queue_service import DocumentQueueService, QueueItem
from kolobot.warehouse_db import WarehouseDB
from kolobot.web_server import WebServer


@pytest.fixture
def warehouse_env(tmp_path):
    db_path = str(tmp_path / "warehouse.db")
    db = WarehouseDB(db_path=db_path)
    db.init_db()

    fs = MagicMock()
    fs._base = str(tmp_path)
    fs.get_tmp_path.side_effect = lambda ext=".jpg": str(tmp_path / f"tmp_mock{ext}")

    vs = MagicMock()
    vs.list_all_ids.return_value = []

    return db, fs, vs


def _make_photo_message(user_id: int = 100, file_id: str = "photo_1", file_unique_id: str = None, group_id: str = None):
    bot = MagicMock()
    bot.download = AsyncMock(return_value=b"fake-image-bytes")
    bot.edit_message_text = AsyncMock()
    bot.send_message = AsyncMock(return_value=SimpleNamespace(message_id=1000))

    msg = MagicMock(spec=Message)
    msg.bot = bot
    msg.from_user = SimpleNamespace(id=user_id, is_bot=False, first_name="User")
    msg.chat = SimpleNamespace(id=user_id, type="private")
    msg.is_topic_message = False
    msg.message_thread_id = None
    msg.business_connection_id = None
    msg.message_effect_id = None
    msg.text = None
    msg.caption = None
    uniq = file_unique_id or f"u_{file_id}"
    msg.photo = [
        SimpleNamespace(file_id="thumb", file_unique_id=uniq, file_size=100, width=100, height=100),
        SimpleNamespace(file_id=file_id, file_unique_id=uniq, file_size=50_000, width=1920, height=1080),
    ]
    msg.document = None
    msg.media_group_id = group_id
    msg.answer = AsyncMock(return_value=SimpleNamespace(message_id=999))
    return msg


# =========================================================================
# 1. API Retry Endpoint tests
# =========================================================================

@pytest.mark.asyncio
async def test_api_retry_document_not_found(warehouse_env):
    """POST /api/warehouse/documents/{id}/retry returns 404 if document does not exist."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.post("/api/warehouse/documents/9999/retry")
        assert resp.status == 404
        data = await resp.json()
        assert "Документ не знайдено" in data["error"]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_retry_document_resets_status_and_clears_error(warehouse_env, tmp_path):
    """POST /api/warehouse/documents/{id}/retry resets DB status to queued and clears error_message."""
    db, fs, vs = warehouse_env
    img_file = tmp_path / "failed.jpg"
    img_file.write_bytes(b"image-data")
    doc_id = db.add_document(
        filename="failed.jpg",
        file_type="photo",
        file_path=str(img_file),
        status="error",
    )
    db.update_document(doc_id, error_message="Gemini API timeout")

    mock_qs = MagicMock()
    mock_qs.retry_document = AsyncMock(return_value=True)

    server = WebServer(
        warehouse_db=db,
        file_store=fs,
        vector_store=vs,
        owner_user_id=42,
        queue_service=mock_qs,
    )
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.post(f"/api/warehouse/documents/{doc_id}/retry")
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["status"] == "queued"

        # Verify DB is updated
        doc = db.get_document(doc_id)
        assert doc["status"] == "queued"
        assert doc["error_message"] == ""

        # Verify queue service retry_document was invoked
        mock_qs.retry_document.assert_awaited_once_with(doc_id)
    finally:
        await client.close()
        db.close()


# =========================================================================
# 2. DocumentQueueService retry_document & has_file_unique_id tests
# =========================================================================

@pytest.mark.asyncio
async def test_queue_service_retry_document(tmp_path):
    """Calling queue_service.retry_document(doc_id) enqueues the item and resets status."""
    db = WarehouseDB(str(tmp_path / "wh.db"))
    db.init_db()

    f1 = tmp_path / "retry_doc.jpg"
    f1.write_bytes(b"retry-bytes")

    try:
        doc_id = db.add_document(
            filename="retry_doc.jpg",
            file_type="photo",
            file_path=str(f1),
            status="error",
        )
        db.update_document(doc_id, error_message="OCR failed")

        mock_gateway = MagicMock()
        mock_gateway.extract_document = AsyncMock(
            return_value='{"doc_type": "invoice", "title": "Успіх", "summary": "Повтор", "raw_text": "Рахунок"}'
        )
        mock_file_store = MagicMock()
        doc_structurer = DocStructurer()
        bot = MagicMock()
        log_buffer = LogBuffer()

        service = DocumentQueueService(
            gateway=mock_gateway,
            doc_structurer=doc_structurer,
            file_store=mock_file_store,
            bot=bot,
            warehouse_db=db,
            log_buffer=log_buffer,
            item_delay_sec=0.0,
            auto_recover=False,
        )

        item = await service.retry_document(doc_id)
        assert item is not None
        assert item.wh_doc_id == doc_id
        assert item.tmp_path == str(f1)
        assert service.get_queue_length() == 1

        # Check DB was updated to queued with error cleared
        doc = db.get_document(doc_id)
        assert doc["status"] == "queued"
        assert doc["error_message"] == ""

        # Process the queue
        await service.join()
        await service.stop()

        mock_gateway.extract_document.assert_awaited_once()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_queue_service_has_file_unique_id(tmp_path):
    """queue_service.has_file_unique_id returns True if an item with file_unique_id is queued or active."""
    mock_gateway = MagicMock()
    mock_file_store = MagicMock()
    doc_structurer = DocStructurer()

    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        auto_recover=False,
    )

    item = QueueItem(
        file_id="f1",
        file_unique_id="unique_abc_123",
        mime="image/jpeg",
        file_size=100,
        tmp_path=str(tmp_path / "t.jpg"),
        chat_id=1,
        user_id=1,
    )

    assert not service.has_file_unique_id("unique_abc_123")
    await service._queue.put(item)
    assert service.has_file_unique_id("unique_abc_123")
    assert not service.has_file_unique_id("other_id")


# =========================================================================
# 3. Web UI: Smart Polling & Retry Button tests
# =========================================================================

@pytest.mark.asyncio
async def test_web_ui_contains_smart_polling_and_retry_button(warehouse_env):
    """Web HTML contains Smart Polling (3000ms, active status tracking) and Retry button logic."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/")
        assert resp.status == 200
        html = await resp.text()

        # Check Smart Polling requirements
        assert "3000" in html, "Must configure 3 second (3000ms) polling interval"
        assert "smartPoll" in html or "checkSmartPolling" in html or "docsPoll" in html
        assert "queued" in html
        assert "processing_" in html or "processing_ocr" in html

        # Check Retry button in documents table
        assert "retryDocument" in html
        assert "Повторити" in html
        assert "/api/warehouse/documents/" in html
        assert "/retry" in html
    finally:
        await client.close()
        db.close()


# =========================================================================
# 4. Batch media deduplication tests
# =========================================================================

@pytest.mark.asyncio
async def test_batch_media_duplicate_prompts_and_batch_continues(tmp_path):
    """
    When files are sent as a batch (media_group_id present), a duplicate file
    gets the same interactive prompt as a standalone one, while non-duplicate
    files in the same batch are accepted and enqueued.
    """
    with patch("kolobot.main.load_config") as mock_conf:
        mock_conf.return_value = SimpleNamespace(
            bot_token="12345:test_token",
            gemini_keys_generate=["gen_key_1"],
            gemini_keys_embed=["emb_key_1"],
            rpm_limit=60,
            rpd_limit=1000,
            cooldown_sec=60,
            downloads_path=str(tmp_path / "downloads"),
            chroma_path=str(tmp_path / "chroma"),
            warehouse_db_path=str(tmp_path / "warehouse.db"),
            owner_user_id=100,
            generate_model="gemini-2.5-flash",
            embed_model="text-embedding-004",
            rag_top_k=5,
            rag_max_distance=1.0,
            confirm_timeout_sec=600,
            web_enabled=False,
            web_host="0.0.0.0",
            web_port=8080,
        )

        dp, bot, settings = build_app()
        queue_service: DocumentQueueService = dp["queue_service"]
        archive_service = dp["archive_service"]

        # Pre-populate archive with existing file unique id
        archive_service.lookup_duplicate = MagicMock(
            side_effect=lambda user_id, file_unique_id: {"id": "existing_123"} if file_unique_id == "u_dup" else None
        )

        # Batch with 3 files: file_a (new), file_b (duplicate), file_c (new)
        msg_a = _make_photo_message(user_id=100, file_id="photo_a", file_unique_id="u_a", group_id="batch_42")
        msg_b = _make_photo_message(user_id=100, file_id="photo_b", file_unique_id="u_dup", group_id="batch_42")
        msg_c = _make_photo_message(user_id=100, file_id="photo_c", file_unique_id="u_c", group_id="batch_42")

        upd_a = Update(update_id=1, message=msg_a)
        upd_a._bot = bot
        upd_b = Update(update_id=2, message=msg_b)
        upd_b._bot = bot
        upd_c = Update(update_id=3, message=msg_c)
        upd_c._bot = bot

        with patch.object(queue_service, "enqueue", new_callable=AsyncMock) as mock_enqueue:
            await dp.feed_update(bot, upd_a)
            await dp.feed_update(bot, upd_b)
            await dp.feed_update(bot, upd_c)

            # Files A and C must be enqueued
            assert mock_enqueue.call_count == 2
            enqueued_files = [call.args[0].file_id for call in mock_enqueue.call_args_list]
            assert "photo_a" in enqueued_files
            assert "photo_c" in enqueued_files
            assert "photo_b" not in enqueued_files

            # Duplicate file B must receive the interactive dedup keyboard
            assert msg_b.answer.await_count >= 1
            b_answers = [call.args[0] for call in msg_b.answer.await_args_list if call.args]
            assert any("вже є в архіві" in txt for txt in b_answers)

            found_kb = False
            for call in msg_b.answer.await_args_list:
                kb = call.kwargs.get("reply_markup")
                if kb and isinstance(kb, InlineKeyboardMarkup):
                    btn_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
                    if any("dedup_open:existing_123" == d for d in btn_data) and any(
                        d.startswith("dedup_force:") for d in btn_data
                    ):
                        found_kb = True
            assert found_kb, "Batch duplicate must present the same interactive keyboard as a standalone one"


@pytest.mark.asyncio
async def test_single_media_duplicate_presents_interactive_keyboard(tmp_path):
    """A standalone (non-batch) duplicate message continues to offer the interactive dedup keyboard."""
    with patch("kolobot.main.load_config") as mock_conf:
        mock_conf.return_value = SimpleNamespace(
            bot_token="12345:test_token",
            gemini_keys_generate=["gen_key_1"],
            gemini_keys_embed=["emb_key_1"],
            rpm_limit=60,
            rpd_limit=1000,
            cooldown_sec=60,
            downloads_path=str(tmp_path / "downloads"),
            chroma_path=str(tmp_path / "chroma"),
            warehouse_db_path=str(tmp_path / "warehouse.db"),
            owner_user_id=100,
            generate_model="gemini-2.5-flash",
            embed_model="text-embedding-004",
            rag_top_k=5,
            rag_max_distance=1.0,
            confirm_timeout_sec=600,
            web_enabled=False,
            web_host="0.0.0.0",
            web_port=8080,
        )

        dp, bot, settings = build_app()
        archive_service = dp["archive_service"]
        archive_service.lookup_duplicate = MagicMock(return_value={"id": "doc_archived_99"})

        # Single file without media_group_id
        msg = _make_photo_message(user_id=100, file_id="photo_single", file_unique_id="u_single", group_id=None)
        upd = Update(update_id=1, message=msg)
        upd._bot = bot

        await dp.feed_update(bot, upd)

        # Standalone duplicate receives interactive keyboard
        assert msg.answer.await_count >= 1
        found_kb = False
        for call in msg.answer.await_args_list:
            kb = call.kwargs.get("reply_markup")
            if kb and isinstance(kb, InlineKeyboardMarkup):
                btn_data = [btn.callback_data for row in kb.inline_keyboard for btn in row]
                if any("dedup_open" in d for d in btn_data) and any("dedup_force" in d for d in btn_data):
                    found_kb = True
        assert found_kb, "Standalone duplicate must present interactive inline keyboard"

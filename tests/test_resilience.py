"""Unit tests for Slice-3 (Issue #14): Resilience, Retries, LogBuffer logging, and Crash Recovery."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from kolobot.doc_structurer import DocStructurer
from kolobot.log_service import LogBuffer
from kolobot.queue_service import DEFAULT_RETRY_DELAYS, DocumentQueueService, QueueItem
from kolobot.warehouse_db import WarehouseDB


def test_default_retry_delays():
    """AC1: Retry delays must be exactly (5.0, 15.0, 30.0) seconds."""
    assert DEFAULT_RETRY_DELAYS == (5.0, 15.0, 30.0)


@pytest.mark.asyncio
async def test_transient_failure_logs_to_log_buffer_warn(tmp_path):
    """AC2: Intermediate failures log to LogBuffer with level WARN."""
    log_buffer = LogBuffer()
    mock_gateway = MagicMock()
    attempts = 0

    async def ocr_fail_once(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("Gemini 503 Service Unavailable")
        return '{"doc_type": "receipt", "title": "Чек", "summary": "Кава", "raw_text": "Чек 50грн"}'

    mock_gateway.extract_document = AsyncMock(side_effect=ocr_fail_once)
    mock_file_store = MagicMock()
    doc_structurer = DocStructurer()
    bot = MagicMock()
    bot.edit_message_text = AsyncMock()

    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=bot,
        log_buffer=log_buffer,
        retry_delays=(0.01, 0.02, 0.03),
    )

    tmp_file = tmp_path / "test.jpg"
    tmp_file.write_bytes(b"image")

    item = QueueItem(
        file_id="fid_1",
        file_unique_id="uid_1",
        mime="image/jpeg",
        file_size=10,
        tmp_path=str(tmp_file),
        chat_id=123,
        user_id=123,
        status_message_id=456,
    )

    await service.enqueue(item)
    await service.join()
    await service.stop()

    assert attempts == 2
    logs, total, _ = log_buffer.get_logs()
    warn_logs = [l for l in logs if l.level == "WARN"]
    assert len(warn_logs) >= 1
    assert "Gemini 503" in warn_logs[0].message or "failed" in warn_logs[0].message.lower()


@pytest.mark.asyncio
async def test_retry_countdown_updates_status(tmp_path):
    """AC2: Retry broadcasts countdown in Telegram message."""
    mock_gateway = MagicMock()
    attempts = 0

    async def ocr_fail_once(**kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("Connection reset")
        return '{"doc_type": "invoice", "title": "Рахунок", "summary": "Тест", "raw_text": "Рахунок"}'

    mock_gateway.extract_document = AsyncMock(side_effect=ocr_fail_once)
    mock_file_store = MagicMock()
    doc_structurer = DocStructurer()
    bot = MagicMock()
    bot.edit_message_text = AsyncMock()

    sleep_calls = []

    async def fake_sleep(duration):
        sleep_calls.append(duration)

    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=bot,
        retry_delays=(3.0,),
    )

    tmp_file = tmp_path / "test2.jpg"
    tmp_file.write_bytes(b"image")

    item = QueueItem(
        file_id="fid_2",
        file_unique_id="uid_2",
        mime="image/jpeg",
        file_size=10,
        tmp_path=str(tmp_file),
        chat_id=123,
        user_id=123,
        status_message_id=456,
    )

    with patch("asyncio.sleep", side_effect=fake_sleep):
        await service.enqueue(item)
        await service.join()
        await service.stop()

    texts = [call.kwargs.get("text", "") for call in bot.edit_message_text.call_args_list]
    # Check that countdown was posted: e.g., 3с, 2с, 1с
    countdown_texts = [t for t in texts if "Помилка розпізнавання" in t and "Повтор через" in t]
    assert len(countdown_texts) == 3
    assert any("Повтор через 3с" in t for t in countdown_texts)
    assert any("Повтор через 2с" in t for t in countdown_texts)
    assert any("Повтор через 1с" in t for t in countdown_texts)


@pytest.mark.asyncio
async def test_exhaustion_marks_db_error_and_logs_err(tmp_path):
    """AC3: Exhausted retries update DB status to error, store error_message, log ERR, and notify Telegram."""
    db = WarehouseDB(str(tmp_path / "wh.db"))
    db.init_db()
    log_buffer = LogBuffer()

    try:
        doc_id = db.add_document(filename="broken.jpg", file_type="photo", status="queued")

        mock_gateway = MagicMock()
        mock_gateway.extract_document = AsyncMock(side_effect=RuntimeError("Permanent API 500 error"))
        mock_file_store = MagicMock()
        doc_structurer = DocStructurer()
        bot = MagicMock()
        bot.edit_message_text = AsyncMock()
        bot.send_message = AsyncMock()

        service = DocumentQueueService(
            gateway=mock_gateway,
            doc_structurer=doc_structurer,
            file_store=mock_file_store,
            bot=bot,
            warehouse_db=db,
            log_buffer=log_buffer,
            retry_delays=(0.01, 0.01, 0.01),
        )

        tmp_file = tmp_path / "broken.jpg"
        tmp_file.write_bytes(b"data")

        item = QueueItem(
            file_id="fid_err",
            file_unique_id="uid_err",
            mime="image/jpeg",
            file_size=10,
            tmp_path=str(tmp_file),
            chat_id=555,
            user_id=555,
            status_message_id=777,
            wh_doc_id=doc_id,
        )

        await service.enqueue(item)
        await service.join()
        await service.stop()

        # Verify DB updated to error with message
        doc = db.get_document(doc_id)
        assert doc["status"] == "error"
        assert "Permanent API 500 error" in doc["error_message"]

        # Verify ERR log in LogBuffer
        logs, _, _ = log_buffer.get_logs()
        err_logs = [l for l in logs if l.level == "ERR"]
        assert len(err_logs) >= 1
        assert "exhausted" in err_logs[0].message.lower() or "permanent" in err_logs[0].message.lower()

        # Verify Telegram notified
        texts = [call.kwargs.get("text", "") for call in bot.edit_message_text.call_args_list]
        assert any("Не вдалося розпізнати документ" in t for t in texts)

    finally:
        db.close()


@pytest.mark.asyncio
async def test_crash_recovery_finds_and_enqueues_unprocessed_documents(tmp_path):
    """AC4: Startup crash recovery enqueues queued, processing_ocr, processing_emb documents."""
    db = WarehouseDB(str(tmp_path / "wh.db"))
    db.init_db()

    f1 = tmp_path / "f1.jpg"
    f1.write_bytes(b"f1")
    f2 = tmp_path / "f2.jpg"
    f2.write_bytes(b"f2")
    f3 = tmp_path / "f3.pdf"
    f3.write_bytes(b"f3")
    f4 = tmp_path / "f4.jpg"
    f4.write_bytes(b"f4")
    f5 = tmp_path / "f5.jpg"
    f5.write_bytes(b"f5")

    try:
        id1 = db.add_document(filename="f1.jpg", file_type="photo", file_path=str(f1), status="queued")
        id2 = db.add_document(filename="f2.jpg", file_type="photo", file_path=str(f2), status="processing_ocr")
        id3 = db.add_document(filename="f3.pdf", file_type="pdf", file_path=str(f3), status="processing_emb")
        id4 = db.add_document(filename="f4.jpg", file_type="photo", file_path=str(f4), status="completed")
        id5 = db.add_document(filename="f5.jpg", file_type="photo", file_path=str(f5), status="error")

        mock_gateway = MagicMock()
        mock_gateway.extract_document = AsyncMock(return_value='{"doc_type": "other", "title": "Doc", "summary": "S", "raw_text": "T"}')
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

        recovered_count = await service.recover_pending(default_chat_id=123, default_user_id=123)
        assert recovered_count == 3
        assert service.queue_size == 3

        # Completed and error documents are not modified
        assert db.get_document(id4)["status"] == "completed"
        assert db.get_document(id5)["status"] == "error"

        # Recovered documents are reset to queued in DB
        assert db.get_document(id1)["status"] == "queued"
        assert db.get_document(id2)["status"] == "queued"
        assert db.get_document(id3)["status"] == "queued"

        # Run the queue worker and ensure they process
        await service.start()
        await service.join()
        await service.stop()

        assert mock_gateway.extract_document.call_count == 3

    finally:
        db.close()


@pytest.mark.asyncio
async def test_crash_recovery_auto_on_start(tmp_path):
    """AC4: When auto_recover=True, calling start() automatically recovers documents."""
    db = WarehouseDB(str(tmp_path / "wh.db"))
    db.init_db()

    f1 = tmp_path / "f1.jpg"
    f1.write_bytes(b"f1")

    try:
        id1 = db.add_document(filename="f1.jpg", file_type="photo", file_path=str(f1), status="queued")
        mock_gateway = MagicMock()
        mock_gateway.extract_document = AsyncMock(return_value='{"doc_type": "other", "title": "Doc", "summary": "S", "raw_text": "T"}')
        mock_file_store = MagicMock()
        doc_structurer = DocStructurer()
        bot = MagicMock()

        service = DocumentQueueService(
            gateway=mock_gateway,
            doc_structurer=doc_structurer,
            file_store=mock_file_store,
            bot=bot,
            warehouse_db=db,
            item_delay_sec=0.0,
            auto_recover=True,
        )

        await service.start()
        await service.join()
        await service.stop()

        assert mock_gateway.extract_document.call_count == 1
    finally:
        db.close()


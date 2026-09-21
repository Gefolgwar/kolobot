"""Tests for DocumentQueueService (Issue #3: FIFO Worker Loop & Document Queue Service)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from kolobot.doc_structurer import DocStructurer, Document
from kolobot.queue_service import DocumentQueueService, QueueItem, PendingCard, ClearResult


@pytest.fixture
def mock_gateway():
    gateway = MagicMock()
    gateway.extract_document = AsyncMock(
        return_value='{"doc_type": "invoice", "title": "Рахунок №123", "summary": "Оплата послуг", "raw_text": "Рахунок №123"}'
    )
    return gateway


@pytest.fixture
def mock_file_store(tmp_path):
    file_store = MagicMock()
    file_store.save_tmp = MagicMock(side_effect=lambda data, ext: str(tmp_path / f"tmp_{ext}"))
    file_store.delete_tmp = MagicMock()
    return file_store


@pytest.fixture
def doc_structurer():
    return DocStructurer()


@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.download = AsyncMock(return_value=b"fake-image-bytes")
    return bot


@pytest.mark.asyncio
async def test_queue_service_enqueue_and_fifo_processing(
    mock_gateway, mock_file_store, doc_structurer, mock_bot, tmp_path
):
    """Verify that multiple items enqueued are processed sequentially in strict FIFO order."""
    processed_order = []

    async def mock_extract(image_bytes, mime, file_path=None):
        # Simulate processing delay
        await asyncio.sleep(0.01)
        doc_title = f"Doc for {mime}"
        processed_order.append(mime)
        return f'{{"doc_type": "receipt", "title": "{doc_title}", "summary": "Summary", "raw_text": "Text"}}'

    mock_gateway.extract_document = AsyncMock(side_effect=mock_extract)

    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=mock_bot,
    )

    item1 = QueueItem(
        file_id="file_1",
        file_unique_id="uniq_1",
        mime="image/jpeg",
        file_size=1000,
        tmp_path=str(tmp_path / "tmp1.jpg"),
        source="photo",
        chat_id=12345,
        user_id=12345,
    )
    item2 = QueueItem(
        file_id="file_2",
        file_unique_id="uniq_2",
        mime="image/png",
        file_size=2000,
        tmp_path=str(tmp_path / "tmp2.png"),
        source="photo",
        chat_id=12345,
        user_id=12345,
    )
    item3 = QueueItem(
        file_id="file_3",
        file_unique_id="uniq_3",
        mime="application/pdf",
        file_size=3000,
        tmp_path=str(tmp_path / "tmp3.pdf"),
        source="document",
        chat_id=12345,
        user_id=12345,
    )

    # Start service
    await service.start()

    # Enqueue items
    await service.enqueue(item1)
    await service.enqueue(item2)
    await service.enqueue(item3)

    # Wait for queue to be fully processed
    await service.join()
    await service.stop()

    # Verify FIFO execution order
    assert processed_order == ["image/jpeg", "image/png", "application/pdf"]
    assert mock_gateway.extract_document.call_count == 3


@pytest.mark.asyncio
async def test_queue_service_pending_cards_lifecycle(
    mock_gateway, mock_file_store, doc_structurer, mock_bot, tmp_path
):
    """Verify that successfully processed items are registered in pending_cards with unique short card_ids."""
    ready_cards = []

    async def on_card_ready(card: PendingCard):
        ready_cards.append(card)

    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=mock_bot,
        on_card_ready=on_card_ready,
    )

    intake_dict = {
        "file_id": "file_abc",
        "file_unique_id": "uniq_abc",
        "mime": "image/jpeg",
        "file_size": 1500,
        "tmp_path": str(tmp_path / "tmp_abc.jpg"),
        "chat_id": 1001,
        "user_id": 1001,
        "source": "photo",
    }

    item_id = await service.enqueue(intake_dict)
    assert item_id is not None
    assert service.is_running is True

    await service.join()
    await service.stop()

    # Check that on_card_ready was invoked
    assert len(ready_cards) == 1
    card = ready_cards[0]
    assert len(card.card_id) == 8
    assert card.item.file_id == "file_abc"
    assert card.doc.title == "Рахунок №123"
    assert card.card.title == "Рахунок №123"

    # Check pending_cards lookup
    assert service.get_card(card.card_id) == card
    assert service.get_pending_card_count(user_id=1001) == 1
    assert service.get_pending_card_count(user_id=9999) == 0

    cards_for_user = service.list_pending_cards(user_id=1001)
    assert len(cards_for_user) == 1
    assert cards_for_user[0].card_id == card.card_id

    # Remove card
    removed = service.remove_card(card.card_id)
    assert removed == card
    assert service.get_card(card.card_id) is None
    assert service.get_pending_card_count(user_id=1001) == 0


@pytest.mark.asyncio
async def test_queue_service_error_handling(
    mock_gateway, mock_file_store, doc_structurer, mock_bot, tmp_path
):
    """Verify that failed extraction triggers on_error and does not add to pending_cards."""
    mock_gateway.extract_document = AsyncMock(side_effect=RuntimeError("Gemini API crash"))
    errors = []

    async def on_error(item: QueueItem, exc: Exception):
        errors.append((item, exc))

    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=mock_bot,
        on_error=on_error,
    )

    item = QueueItem(
        file_id="bad_file",
        file_unique_id="bad_uniq",
        mime="image/jpeg",
        file_size=500,
        tmp_path=str(tmp_path / "bad.jpg"),
        chat_id=1001,
        user_id=1001,
    )

    await service.enqueue(item)
    await service.join()
    await service.stop()

    assert len(errors) == 1
    assert errors[0][0].file_id == "bad_file"
    assert "Gemini API crash" in str(errors[0][1])
    assert service.get_pending_card_count(user_id=1001) == 0


@pytest.mark.asyncio
async def test_queue_service_lifecycle_and_non_blocking(
    mock_gateway, mock_file_store, doc_structurer, mock_bot, tmp_path
):
    """Verify worker lifecycle management, idempotency of start/stop, and non-blocking operation."""
    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=mock_bot,
    )

    assert service.is_running is False

    # Start service
    await service.start()
    assert service.is_running is True
    task1 = service._worker_task

    # Idempotent start
    await service.start()
    assert service._worker_task is task1

    # Non-blocking enqueue and event loop responsive
    start_time = asyncio.get_event_loop().time()
    await service.enqueue({
        "file_id": "file_slow",
        "file_unique_id": "uniq_slow",
        "mime": "image/jpeg",
        "file_size": 500,
        "tmp_path": str(tmp_path / "slow.jpg"),
        "chat_id": 1001,
        "user_id": 1001,
    })
    elapsed = asyncio.get_event_loop().time() - start_time
    assert elapsed < 0.05  # Enqueue returns instantly

    await service.join()

    # Stop service
    await service.stop()
    assert service.is_running is False

    # Idempotent stop
    await service.stop()
    assert service.is_running is False


@pytest.mark.asyncio
async def test_retry_logic_success_after_transient_failures(
    mock_gateway, mock_file_store, doc_structurer, mock_bot, tmp_path
):
    """Verify that DocumentQueueService retries on transient errors and succeeds when a retry works."""
    attempts = 0

    async def flaky_extract(image_bytes, mime, file_path=None):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError(f"Transient 429 error on attempt {attempts}")
        return '{"doc_type": "receipt", "title": "Чек після повтору", "summary": "Успіх", "raw_text": "Чек"}'

    mock_gateway.extract_document = AsyncMock(side_effect=flaky_extract)

    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=mock_bot,
        retry_delays=(0.01, 0.02, 0.03),
    )

    item = QueueItem(
        file_id="flaky_file",
        file_unique_id="flaky_uniq",
        mime="image/jpeg",
        file_size=1000,
        tmp_path=str(tmp_path / "flaky.jpg"),
        chat_id=1001,
        user_id=1001,
    )

    await service.enqueue(item)
    await service.join()
    await service.stop()

    assert attempts == 3
    assert service.get_pending_card_count(user_id=1001) == 1
    cards = service.list_pending_cards(user_id=1001)
    assert cards[0].doc.title == "Чек після повтору"


@pytest.mark.asyncio
async def test_retry_logic_status_message_updates(
    mock_gateway, mock_file_store, doc_structurer, tmp_path
):
    """Verify that Telegram status messages are updated in-place via edit_message_text during retries."""
    bot = MagicMock()
    bot.download = AsyncMock(return_value=b"fake-bytes")
    bot.edit_message_text = AsyncMock()

    status_updates = []

    async def on_status(item, text):
        status_updates.append(text)

    attempts = 0

    async def extract_fail_twice(image_bytes, mime, file_path=None):
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise RuntimeError(f"Rate limited (attempt {attempts})")
        return '{"doc_type": "contract", "title": "Договір оренди", "summary": "Оренда", "raw_text": "Договір"}'

    mock_gateway.extract_document = AsyncMock(side_effect=extract_fail_twice)

    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=bot,
        on_status_update=on_status,
        retry_delays=(0.01, 0.02, 0.03),
    )

    item = QueueItem(
        file_id="status_file",
        file_unique_id="status_uniq",
        mime="image/jpeg",
        file_size=1000,
        tmp_path=str(tmp_path / "status.jpg"),
        chat_id=777,
        user_id=777,
        status_message_id=999,
    )

    await service.enqueue(item)
    await service.join()
    await service.stop()

    assert attempts == 3
    # Verify bot.edit_message_text was called for retries 1 and 2
    assert bot.edit_message_text.call_count == 2
    call_args_list = bot.edit_message_text.call_args_list

    # First retry (attempt 1/3)
    assert call_args_list[0].kwargs["chat_id"] == 777
    assert call_args_list[0].kwargs["message_id"] == 999
    assert "Спроба 1/3" in call_args_list[0].kwargs["text"]

    # Second retry (attempt 2/3)
    assert call_args_list[1].kwargs["chat_id"] == 777
    assert call_args_list[1].kwargs["message_id"] == 999
    assert "Спроба 2/3" in call_args_list[1].kwargs["text"]

    # Verify callback was also notified
    assert len(status_updates) == 2
    assert "Спроба 1/3" in status_updates[0]
    assert "Спроба 2/3" in status_updates[1]


@pytest.mark.asyncio
async def test_retry_exhaustion_cleans_up_and_continues_worker(
    mock_gateway, mock_file_store, doc_structurer, tmp_path
):
    """Verify that exhausting all retries updates the status message to error, deletes tmp files, and processes next item."""
    bot = MagicMock()
    bot.download = AsyncMock(return_value=b"test-bytes")
    bot.edit_message_text = AsyncMock()

    mock_gateway.extract_document = AsyncMock(side_effect=[
        RuntimeError("Fatal error attempt 1"),
        RuntimeError("Fatal error attempt 2"),
        RuntimeError("Fatal error attempt 3"),
        RuntimeError("Fatal error attempt 4"),
        '{"doc_type": "invoice", "title": "Рахунок №2", "summary": "ОК", "raw_text": "Рахунок"}',
    ])

    errors = []

    async def on_error(item, exc):
        errors.append((item, exc))

    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=bot,
        on_error=on_error,
        retry_delays=(0.01, 0.02, 0.03),
    )

    bad_tmp_file = tmp_path / "bad.jpg"
    bad_tmp_file.write_bytes(b"bad-data")
    bad_item = QueueItem(
        file_id="bad_file",
        file_unique_id="bad_uniq",
        mime="image/jpeg",
        file_size=1000,
        tmp_path=str(bad_tmp_file),
        chat_id=1001,
        user_id=1001,
        status_message_id=501,
    )

    good_tmp_file = tmp_path / "good.jpg"
    good_tmp_file.write_bytes(b"good-data")
    good_item = QueueItem(
        file_id="good_file",
        file_unique_id="good_uniq",
        mime="image/jpeg",
        file_size=1000,
        tmp_path=str(good_tmp_file),
        chat_id=1001,
        user_id=1001,
        status_message_id=502,
    )

    await service.enqueue(bad_item)
    await service.enqueue(good_item)

    await service.join()
    await service.stop()

    # Total 4 calls for bad item + 1 call for good item = 5 calls
    assert mock_gateway.extract_document.call_count == 5

    # Verify on_error received bad item
    assert len(errors) == 1
    assert errors[0][0].file_id == "bad_file"
    assert "Fatal error attempt 4" in str(errors[0][1])

    # Verify temporary file cleanup for bad item was triggered
    mock_file_store.delete_tmp.assert_called_with(str(bad_tmp_file))

    # Verify status message for bad item was updated with error state
    error_status_calls = [
        call for call in bot.edit_message_text.call_args_list
        if call.kwargs.get("message_id") == 501 and "Не вдалося розпізнати документ" in call.kwargs.get("text", "")
    ]
    assert len(error_status_calls) == 1
    assert "після 3 повторних спроб" in error_status_calls[0].kwargs["text"]

    # Verify good item was processed successfully after the failure
    assert service.get_pending_card_count(user_id=1001) == 1
    pending_cards = service.list_pending_cards(user_id=1001)
    assert pending_cards[0].doc.title == "Рахунок №2"


@pytest.mark.asyncio
async def test_queue_service_clear_idle_drains_queue_cards_and_files(
    mock_gateway, mock_file_store, doc_structurer, mock_bot, tmp_path
):
    """Verify that clear() purges queued items, pending cards, deletes tmp files, and restarts worker."""
    service = DocumentQueueService(
        gateway=mock_gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=mock_bot,
    )

    # Add 2 pending cards manually
    tmp_card1 = tmp_path / "card1.jpg"
    tmp_card1.write_bytes(b"card1")
    item_card1 = QueueItem(
        file_id="f_c1",
        file_unique_id="u_c1",
        mime="image/jpeg",
        file_size=100,
        tmp_path=str(tmp_card1),
        chat_id=100,
        user_id=100,
    )
    doc1 = Document(doc_type="invoice", title="Doc 1")
    service._pending_cards["c1"] = PendingCard("c1", item_card1, doc1, doc_structurer.to_card(doc1))

    tmp_card2 = tmp_path / "card2.jpg"
    tmp_card2.write_bytes(b"card2")
    item_card2 = QueueItem(
        file_id="f_c2",
        file_unique_id="u_c2",
        mime="image/jpeg",
        file_size=100,
        tmp_path=str(tmp_card2),
        chat_id=100,
        user_id=100,
    )
    doc2 = Document(doc_type="receipt", title="Doc 2")
    service._pending_cards["c2"] = PendingCard("c2", item_card2, doc2, doc_structurer.to_card(doc2))

    # Add 2 items directly to queue without starting worker yet
    tmp_q1 = tmp_path / "q1.jpg"
    tmp_q1.write_bytes(b"q1")
    item_q1 = QueueItem(
        file_id="f_q1",
        file_unique_id="u_q1",
        mime="image/jpeg",
        file_size=100,
        tmp_path=str(tmp_q1),
        chat_id=100,
        user_id=100,
    )
    tmp_q2 = tmp_path / "q2.jpg"
    tmp_q2.write_bytes(b"q2")
    item_q2 = QueueItem(
        file_id="f_q2",
        file_unique_id="u_q2",
        mime="image/jpeg",
        file_size=100,
        tmp_path=str(tmp_q2),
        chat_id=100,
        user_id=100,
    )
    await service._queue.put(item_q1)
    await service._queue.put(item_q2)

    assert service.queue_size == 2
    assert service.get_pending_card_count() == 2

    # Perform clear
    result = await service.clear()

    assert isinstance(result, ClearResult)
    assert result.cancelled_active == 0
    assert result.drained_queue == 2
    assert result.cleared_cards == 2
    assert result.deleted_files == 4

    assert service.queue_size == 0
    assert service.get_pending_card_count() == 0
    assert service.is_running is True

    # Verify file_store.delete_tmp was called for all 4 temp paths
    deleted_paths = [call.args[0] for call in mock_file_store.delete_tmp.call_args_list]
    assert str(tmp_card1) in deleted_paths
    assert str(tmp_card2) in deleted_paths
    assert str(tmp_q1) in deleted_paths
    assert str(tmp_q2) in deleted_paths

    await service.stop()


@pytest.mark.asyncio
async def test_queue_service_clear_cancels_inflight_task_and_restarts_worker(
    mock_file_store, doc_structurer, mock_bot, tmp_path
):
    """Verify that clear() cancels an ongoing OCR extraction, deletes its tmp file, and allows subsequent jobs to run."""
    extract_started = asyncio.Event()
    extract_cancelled = asyncio.Event()

    async def slow_extract(image_bytes, mime, file_path=None):
        extract_started.set()
        try:
            await asyncio.sleep(10.0)  # Long running task
        except asyncio.CancelledError:
            extract_cancelled.set()
            raise
        return '{"doc_type": "invoice", "title": "Done"}'

    gateway = MagicMock()
    gateway.extract_document = AsyncMock(side_effect=slow_extract)

    service = DocumentQueueService(
        gateway=gateway,
        doc_structurer=doc_structurer,
        file_store=mock_file_store,
        bot=mock_bot,
    )

    tmp_inflight = tmp_path / "inflight.jpg"
    tmp_inflight.write_bytes(b"inflight-data")
    item_inflight = QueueItem(
        file_id="f_inflight",
        file_unique_id="u_inflight",
        mime="image/jpeg",
        file_size=500,
        tmp_path=str(tmp_inflight),
        chat_id=100,
        user_id=100,
    )

    tmp_queued = tmp_path / "queued.jpg"
    tmp_queued.write_bytes(b"queued-data")
    item_queued = QueueItem(
        file_id="f_queued",
        file_unique_id="u_queued",
        mime="image/jpeg",
        file_size=500,
        tmp_path=str(tmp_queued),
        chat_id=100,
        user_id=100,
    )

    await service.enqueue(item_inflight)
    await service.enqueue(item_queued)

    # Wait until in-flight extraction starts
    await asyncio.wait_for(extract_started.wait(), timeout=1.0)
    assert service.is_processing is True

    # Now call clear() while task is in flight
    result = await service.clear()

    assert result.cancelled_active == 1
    assert result.drained_queue == 1
    assert result.cleared_cards == 0
    assert result.deleted_files == 2

    assert extract_cancelled.is_set()

    assert service.is_processing is False
    assert service.queue_size == 0
    assert service.is_running is True

    # Now verify the restarted worker can process a brand new item cleanly
    gateway.extract_document = AsyncMock(
        return_value='{"doc_type": "invoice", "title": "Новий документ після clear", "summary": "ОК", "raw_text": "Текст"}'
    )

    tmp_new = tmp_path / "new.jpg"
    tmp_new.write_bytes(b"new-data")
    item_new = QueueItem(
        file_id="f_new",
        file_unique_id="u_new",
        mime="image/jpeg",
        file_size=500,
        tmp_path=str(tmp_new),
        chat_id=100,
        user_id=100,
    )

    await service.enqueue(item_new)
    await service.join()
    await service.stop()

    assert service.get_pending_card_count(100) == 1
    cards = service.list_pending_cards(100)
    assert cards[0].doc.title == "Новий документ після clear"


@pytest.mark.asyncio
async def test_queue_service_rate_limiting_delay_between_items(
    mock_gateway, mock_file_store, doc_structurer, mock_bot, tmp_path
):
    """Verify that DocumentQueueService waits item_delay_sec between items."""
    sleeps = []
    real_sleep = asyncio.sleep

    async def tracking_sleep(delay, *args, **kwargs):
        sleeps.append(delay)
        await real_sleep(0.001)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(asyncio, "sleep", tracking_sleep)
        service = DocumentQueueService(
            gateway=mock_gateway,
            doc_structurer=doc_structurer,
            file_store=mock_file_store,
            bot=mock_bot,
            item_delay_sec=3.0,
        )

        tmp1 = tmp_path / "f1.jpg"
        tmp1.write_bytes(b"data1")
        tmp2 = tmp_path / "f2.jpg"
        tmp2.write_bytes(b"data2")

        item1 = QueueItem(file_id="f1", file_unique_id="u1", mime="image/jpeg", file_size=10, tmp_path=str(tmp1), chat_id=1, user_id=1)
        item2 = QueueItem(file_id="f2", file_unique_id="u2", mime="image/jpeg", file_size=10, tmp_path=str(tmp2), chat_id=1, user_id=1)

        await service.enqueue(item1)
        await service.enqueue(item2)
        await service.join()
        assert 3.0 in sleeps
        await service.stop()


@pytest.mark.asyncio
async def test_queue_service_document_status_transitions(
    mock_gateway, mock_file_store, doc_structurer, mock_bot, tmp_path
):
    """Issue #13: Document transitions queued -> processing_ocr -> processing_emb in DB and Telegram."""
    from kolobot.warehouse_db import WarehouseDB

    db = WarehouseDB(str(tmp_path / "wh.db"))
    db.init_db()
    try:
        doc_id = db.add_document(filename="test.jpg", file_type="photo", status="queued")
        assert db.get_document(doc_id)["status"] == "queued"

        status_updates = []

        async def track_status(item, text):
            status_updates.append((item.wh_doc_id, text, db.get_document(doc_id)["status"]))

        service = DocumentQueueService(
            gateway=mock_gateway,
            doc_structurer=doc_structurer,
            file_store=mock_file_store,
            bot=mock_bot,
            warehouse_db=db,
            on_status_update=track_status,
        )

        tmp_file = tmp_path / "test.jpg"
        tmp_file.write_bytes(b"image-content")

        item = QueueItem(
            file_id="fid_999",
            file_unique_id="uid_999",
            mime="image/jpeg",
            file_size=100,
            tmp_path=str(tmp_file),
            chat_id=1,
            user_id=1,
            status_message_id=42,
            wh_doc_id=doc_id,
        )

        await service.enqueue(item)
        await service.join()
        await service.stop()

        # Check DB status after OCR and emb phase
        assert db.get_document(doc_id)["status"] == "processing_emb"

        # Check Telegram edit message was called for both stages
        texts = [call.kwargs.get("text") or call.args[2] if len(call.args) > 2 else call.kwargs.get("text", "") for call in mock_bot.edit_message_text.call_args_list]
        assert any("Розпізнавання" in str(t) for t in texts)
        assert any("Embeddings" in str(t) for t in texts)
    finally:
        db.close()









"""Integration tests for Issue #5: Interactive Multi-Card Confirmation & Media Intake Update."""

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, Update

from kolobot.doc_structurer import DocStructurer, Document
from kolobot.file_store import FileStore
from kolobot.handlers.media import MediaHandler
from kolobot.main import build_app, format_card_text, make_card_keyboard
from kolobot.queue_service import DocumentQueueService, PendingCard, QueueItem


def _make_photo_message(user_id: int = 100, file_id: str = "photo_1", group_id: str = None):
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
    msg.photo = [
        SimpleNamespace(file_id="thumb", file_unique_id=f"u_{file_id}", file_size=100, width=100, height=100),
        SimpleNamespace(file_id=file_id, file_unique_id=f"u_{file_id}", file_size=50_000, width=1920, height=1080),
    ]
    msg.document = None
    msg.media_group_id = group_id
    msg.answer = AsyncMock(return_value=SimpleNamespace(message_id=999))
    return msg


def _make_callback_query(data: str, user_id: int = 100):
    bot = MagicMock()
    bot.download = AsyncMock(return_value=b"fake-image-bytes")
    bot.edit_message_text = AsyncMock()
    bot.send_message = AsyncMock(return_value=SimpleNamespace(message_id=1000))

    msg = MagicMock(spec=Message)
    msg.bot = bot
    msg.chat = SimpleNamespace(id=user_id, type="private")
    msg.is_topic_message = False
    msg.message_thread_id = None
    msg.business_connection_id = None
    msg.message_effect_id = None
    msg.text = None
    msg.caption = None
    msg.answer = AsyncMock()
    msg.edit_reply_markup = AsyncMock()

    cb = MagicMock(spec=CallbackQuery)
    cb.bot = bot
    cb.data = data
    cb.from_user = SimpleNamespace(id=user_id, is_bot=False, first_name="User")
    cb.chat_instance = "chat_inst_1"
    cb.message = msg
    cb.answer = AsyncMock()
    return cb


@pytest.mark.asyncio
async def test_format_card_text_and_keyboard():
    structurer = DocStructurer()
    doc = Document(
        doc_type="invoice",
        title="Рахунок на оплату № 45",
        doc_number="45",
        doc_date="15.08.2026",
        summary="Послуги зв'язку",
        key_value_pairs=[{"key": "Постачальник", "value": "ТОВ Зв'язок"}],
        raw_text="Рахунок № 45 від 15.08.2026",
    )
    card_view = structurer.to_card(doc)
    text = format_card_text(doc, card_view)

    assert "INVOICE" in text or "НАКЛАДНА" in text
    assert "№ 45" in text
    assert "Послуги зв&#x27;язку" in text or "Послуги зв'язку" in text

    kb = make_card_keyboard("abcd1234")
    assert isinstance(kb, InlineKeyboardMarkup)
    assert len(kb.inline_keyboard) == 1
    assert kb.inline_keyboard[0][0].text == "Зберегти"
    assert kb.inline_keyboard[0][0].callback_data == "confirm_save:abcd1234"
    assert kb.inline_keyboard[0][1].text == "Відхилити"
    assert kb.inline_keyboard[0][1].callback_data == "confirm_reject:abcd1234"


@pytest.mark.asyncio
async def test_multi_card_confirm_and_reject_in_any_order(tmp_path):
    """Verify multiple recognized cards can be confirmed or rejected in arbitrary order."""
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

        # Create two pending cards
        item1 = QueueItem(
            file_id="fid_1",
            file_unique_id="uid_1",
            mime="image/jpeg",
            file_size=1000,
            tmp_path=str(tmp_path / "tmp1.jpg"),
            chat_id=100,
            user_id=100,
        )
        item2 = QueueItem(
            file_id="fid_2",
            file_unique_id="uid_2",
            mime="image/jpeg",
            file_size=1000,
            tmp_path=str(tmp_path / "tmp2.jpg"),
            chat_id=100,
            user_id=100,
        )

        doc1 = Document(doc_type="invoice", title="Рахунок 1", raw_text="Текст 1")
        doc2 = Document(doc_type="receipt", title="Чек 2", raw_text="Текст 2")

        structurer = DocStructurer()
        card1 = PendingCard("card_001", item1, doc1, structurer.to_card(doc1))
        card2 = PendingCard("card_002", item2, doc2, structurer.to_card(doc2))

        queue_service._pending_cards["card_001"] = card1
        queue_service._pending_cards["card_002"] = card2

        assert queue_service.get_pending_card_count(100) == 2

        # 1. Reject Card 2 FIRST
        cb_reject_2 = _make_callback_query("confirm_reject:card_002", user_id=100)
        upd1 = Update(update_id=1, callback_query=cb_reject_2)
        upd1._bot = bot
        await dp.feed_update(bot, upd1)

        # Check card 2 removed and keyboard cleared
        assert queue_service.get_card("card_002") is None
        assert queue_service.get_pending_card_count(100) == 1
        cb_reject_2.message.edit_reply_markup.assert_awaited_with(reply_markup=None)
        cb_reject_2.message.answer.assert_awaited_with("Відхилено — тимчасовий файл видалено.")

        # 2. Save Card 1 SECOND
        cb_save_1 = _make_callback_query("confirm_save:card_001", user_id=100)
        upd2 = Update(update_id=2, callback_query=cb_save_1)
        upd2._bot = bot
        with patch("kolobot.archive_service.ArchiveService.save", new_callable=AsyncMock) as mock_save:
            mock_save.return_value = SimpleNamespace(success=True, doc_id="doc_abc", disk_warning=False, error=None)
            await dp.feed_update(bot, upd2)

            assert queue_service.get_card("card_001") is None
            assert queue_service.get_pending_card_count(100) == 0
            cb_save_1.message.edit_reply_markup.assert_awaited_with(reply_markup=None)
            mock_save.assert_awaited_once()


@pytest.mark.asyncio
async def test_stale_card_interaction_alert(tmp_path):
    """Verify interacting with an already-cleared or non-existent card alerts the user and removes keyboard."""
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

        cb = _make_callback_query("confirm_save:nonexistent_card", user_id=100)
        upd = Update(update_id=1, callback_query=cb)
        upd._bot = bot
        await dp.feed_update(bot, upd)

        cb.answer.assert_awaited_once()
        answer_text = cb.answer.await_args.args[0] if cb.answer.await_args.args else cb.answer.await_args.kwargs.get("text", "")
        assert "не активна" in answer_text.lower()
        cb.message.edit_reply_markup.assert_awaited_with(reply_markup=None)


@pytest.mark.asyncio
async def test_unsaved_cards_reminder_on_media_intake(tmp_path):
    """Verify that uploading a new document when previous cards are pending sends a reminder with the count."""
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

        # Add 3 pending cards
        for i in range(3):
            cid = f"card_{i}"
            item = QueueItem(
                file_id=f"f_{i}",
                file_unique_id=f"u_{i}",
                mime="image/jpeg",
                file_size=1000,
                tmp_path=str(tmp_path / f"tmp{i}.jpg"),
                chat_id=100,
                user_id=100,
            )
            doc = Document(doc_type="invoice", title=f"Doc {i}")
            queue_service._pending_cards[cid] = PendingCard(cid, item, doc, DocStructurer().to_card(doc))

        assert queue_service.get_pending_card_count(100) == 3

        # Upload new media
        msg = _make_photo_message(user_id=100, file_id="new_photo")
        upd = Update(update_id=1, message=msg)
        upd._bot = bot
        with patch.object(queue_service, "enqueue", new_callable=AsyncMock) as mock_enqueue:
            await dp.feed_update(bot, upd)

            # Verify reminder was sent
            assert msg.answer.await_count >= 1
            answer_texts = [call.args[0] for call in msg.answer.await_args_list if call.args]
            reminder_found = any("3 незбережен" in txt for txt in answer_texts)
            assert reminder_found, f"Expected reminder with 3 unsaved cards in {answer_texts}"
            mock_enqueue.assert_awaited_once()


@pytest.mark.asyncio
async def test_album_intake_enqueues_all_files(tmp_path):
    """Verify that Telegram media album (group of multiple files) enqueues all files without rejection."""
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

        msg1 = _make_photo_message(user_id=100, file_id="photo_a", group_id="album_99")
        msg2 = _make_photo_message(user_id=100, file_id="photo_b", group_id="album_99")

        upd1 = Update(update_id=1, message=msg1)
        upd1._bot = bot
        upd2 = Update(update_id=2, message=msg2)
        upd2._bot = bot

        with patch.object(queue_service, "enqueue", new_callable=AsyncMock) as mock_enqueue:
            await dp.feed_update(bot, upd1)
            await dp.feed_update(bot, upd2)

            assert mock_enqueue.call_count == 2
            enqueued_items = [call.args[0] for call in mock_enqueue.call_args_list]
            assert enqueued_items[0].file_id == "photo_a"
            assert enqueued_items[1].file_id == "photo_b"


@pytest.mark.asyncio
async def test_duplicate_check_and_dedup_force_and_open(tmp_path):
    """Verify duplicate file detection prompts user with options and allows opening old or forcing new."""
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

        with patch("kolobot.archive_service.ArchiveService.lookup_duplicate") as mock_lookup:
            mock_lookup.return_value = {"id": "doc_existing_123", "metadata": {"telegram_file_id": "old_fid", "source": "photo"}}

            # Send duplicate photo
            msg = _make_photo_message(user_id=100, file_id="dup_photo")
            upd = Update(update_id=1, message=msg)
            upd._bot = bot

            await dp.feed_update(bot, upd)

            # Check duplicate prompt
            msg.answer.assert_awaited_once()
            ans_args = msg.answer.await_args
            assert "вже є в архіві" in ans_args.args[0]
            reply_markup = ans_args.kwargs.get("reply_markup")
            assert reply_markup is not None
            buttons = reply_markup.inline_keyboard[0]
            assert buttons[0].text == "Відкрити старий"
            assert buttons[0].callback_data == "dedup_open:doc_existing_123"
            assert buttons[1].text == "Все одно зберегти"
            assert buttons[1].callback_data.startswith("dedup_force:")

            dedup_force_cb_data = buttons[1].callback_data

            # 1. Test clicking dedup_force
            cb_force = _make_callback_query(dedup_force_cb_data, user_id=100)
            upd_force = Update(update_id=2, callback_query=cb_force)
            upd_force._bot = bot

            with patch.object(queue_service, "enqueue", new_callable=AsyncMock) as mock_enqueue:
                await dp.feed_update(bot, upd_force)

                mock_enqueue.assert_awaited_once()
                enqueued = mock_enqueue.await_args.args[0]
                assert enqueued.file_id == "dup_photo"
                cb_force.message.edit_reply_markup.assert_awaited_with(reply_markup=None)

            # 2. Test clicking dedup_open
            cb_open = _make_callback_query("dedup_open:doc_existing_123", user_id=100)
            upd_open = Update(update_id=3, callback_query=cb_open)
            upd_open._bot = bot

            with patch("kolobot.vector_store.VectorStore.get") as mock_vs_get:
                mock_vs_get.return_value = {"metadata": {"telegram_file_id": "old_fid", "source": "photo"}}
                with patch("kolobot.main.send_archive_file", new_callable=AsyncMock) as mock_send_file:
                    await dp.feed_update(bot, upd_open)
                    mock_send_file.assert_awaited_once()
                    cb_open.message.edit_reply_markup.assert_awaited_with(reply_markup=None)


@pytest.mark.asyncio
async def test_media_intake_saves_file_and_registers_queued_document(tmp_path):
    """Issue #12: bytes are stored immediately and the document is registered as `queued`."""
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
        from kolobot.warehouse_db import WarehouseDB

        msg = _make_photo_message(user_id=100, file_id="queued_photo")
        upd = Update(update_id=1, message=msg)
        upd._bot = bot

        with patch.object(queue_service, "enqueue", new_callable=AsyncMock) as mock_enqueue:
            await dp.feed_update(bot, upd)

        enqueued = mock_enqueue.await_args.args[0]

        # 1. Bot confirms the immediate local save with the queue position
        answers = [c.args[0] for c in msg.answer.await_args_list if c.args]
        queued_answers = [t for t in answers if t.startswith("📥 Збережено. В черзі (#")]
        assert len(queued_answers) == 1, answers

        # 2. The document is registered as `queued` with a saved file on disk
        wdb = WarehouseDB(settings.warehouse_db_path)
        wdb.init_db()
        try:
            docs = wdb.get_documents()
            assert len(docs) == 1
            assert docs[0]["status"] == "queued"
            assert os.path.exists(docs[0]["file_path"])
            with open(docs[0]["file_path"], "rb") as f:
                assert f.read() == b"fake-image-bytes"
        finally:
            wdb.close()

        # 3. The queue item carries the warehouse document id and the live status message
        assert enqueued.wh_doc_id == docs[0]["id"]
        assert enqueued.status_message_id is not None
        assert queued_answers[0] == f"📥 Збережено. В черзі (#{docs[0]['id']})"


@pytest.mark.asyncio
async def test_media_intake_does_not_register_queued_document_for_duplicate(tmp_path):
    """Issue #12: a skipped duplicate must not create a new queued document."""
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
        from kolobot.warehouse_db import WarehouseDB

        with patch("kolobot.archive_service.ArchiveService.lookup_duplicate") as mock_lookup:
            mock_lookup.return_value = {"id": "doc_existing_123", "metadata": {}}

            msg = _make_photo_message(user_id=100, file_id="dup_photo")
            upd = Update(update_id=1, message=msg)
            upd._bot = bot

            await dp.feed_update(bot, upd)

        wdb = WarehouseDB(settings.warehouse_db_path)
        wdb.init_db()
        try:
            assert wdb.get_documents() == []
        finally:
            wdb.close()


@pytest.mark.asyncio
async def test_worker_auto_save_warehouse_and_vector_store(tmp_path):
    """Issue #13: Processed queue items are automatically saved to warehouse & RAG without inline button confirmation."""
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
            queue_item_delay_sec=0.0,
            web_enabled=False,
            web_host="0.0.0.0",
            web_port=8080,
        )

        dp, bot, settings = build_app()
        bot.download = AsyncMock(return_value=b"fake-image-bytes")
        bot.edit_message_text = AsyncMock()
        bot.send_message = AsyncMock()
        queue_service: DocumentQueueService = dp["queue_service"]
        queue_service._bot = bot
        queue_service._retry_delays = (0.01, 0.01, 0.01)
        gateway = dp["gemini_gateway"]
        vector_store = dp["vector_store"]
        from kolobot.warehouse_db import WarehouseDB

        # Mock OCR extraction
        gateway.extract_document = AsyncMock(
            return_value='{"doc_type": "НАКЛАДНА", "title": "Накладна № 777", "doc_number": "777", "doc_date": "10.08.2026", "items": [{"name": "Болт М8", "quantity": "50", "unit": "шт"}], "raw_text": "НАКЛАДНА № 777 Болт М8 50 шт"}'
        )
        # Mock embedding
        gateway.embed_texts = AsyncMock(return_value=[[0.1] * 768])

        msg = _make_photo_message(user_id=100, file_id="auto_save_photo")
        upd = Update(update_id=1, message=msg)
        upd._bot = bot

        await dp.feed_update(bot, upd)

        # Wait for queue processing to complete
        await queue_service.join()
        await queue_service.stop()

        # 1. Warehouse document status is 'completed'
        wdb = WarehouseDB(settings.warehouse_db_path)
        wdb.init_db()
        try:
            docs = wdb.get_documents()
            assert len(docs) == 1
            assert docs[0]["status"] == "completed"
            assert docs[0]["doc_number"] == "777"
            assert docs[0]["doc_type"] == "НАКЛАДНА"

            # 2. Warehouse items and transactions were auto-created
            items = wdb.get_items_with_balance()
            assert len(items) == 1
            assert items[0]["name"] == "Болт М8"
            assert items[0]["balance"] == 50.0
        finally:
            wdb.close()

        # 3. Document is indexed in vector store
        assert vector_store.count(user_id=100) == 1

        # 4. No pending unconfirmed cards remain
        assert queue_service.get_pending_card_count() == 0

        # 5. Telegram live message was edited with completion
        edit_texts = [
            call.kwargs.get("text") or call.args[2] if len(call.args) > 2 else call.kwargs.get("text", "")
            for call in bot.edit_message_text.call_args_list
        ]
        assert any("Накладна № 777" in str(t) or "збережено" in str(t).lower() for t in edit_texts)



@pytest.mark.asyncio
async def test_clear_command_purges_queue_and_invalidates_cards(tmp_path):
    """Verify /clear command executes, cancels tasks, purges queue, and invalidates active cards."""
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

        # Add a pending card
        tmp_file = tmp_path / "card1.jpg"
        tmp_file.write_bytes(b"card1-data")
        item = QueueItem(
            file_id="fid_clear_1",
            file_unique_id="uid_clear_1",
            mime="image/jpeg",
            file_size=1000,
            tmp_path=str(tmp_file),
            chat_id=100,
            user_id=100,
        )
        doc = Document(doc_type="invoice", title="Документ для очищення")
        card = PendingCard("card_clear_1", item, doc, DocStructurer().to_card(doc))
        queue_service._pending_cards["card_clear_1"] = card

        assert queue_service.get_pending_card_count(100) == 1

        # Send /clear command
        msg_clear = MagicMock(spec=Message)
        msg_clear.bot = bot
        msg_clear.from_user = SimpleNamespace(id=100, is_bot=False, first_name="User")
        msg_clear.chat = SimpleNamespace(id=100, type="private")
        msg_clear.is_topic_message = False
        msg_clear.message_thread_id = None
        msg_clear.business_connection_id = None
        msg_clear.message_effect_id = None
        msg_clear.text = "/clear"
        msg_clear.caption = None
        msg_clear.photo = None
        msg_clear.document = None
        msg_clear.media_group_id = None
        msg_clear.answer = AsyncMock()

        upd_clear = Update(update_id=10, message=msg_clear)
        upd_clear._bot = bot

        await dp.feed_update(bot, upd_clear)

        # Verify summary was sent
        msg_clear.answer.assert_awaited_once()
        summary_text = msg_clear.answer.await_args.args[0]
        assert "Чергу та активні завдання очищено" in summary_text
        assert "Видалено незбережених карток: 1" in summary_text

        # Verify queue service state is now empty
        assert queue_service.get_pending_card_count(100) == 0
        assert queue_service.get_card("card_clear_1") is None

        # Verify clicking the old card now shows stale notification
        cb_stale = _make_callback_query("confirm_save:card_clear_1", user_id=100)
        upd_cb = Update(update_id=11, callback_query=cb_stale)
        upd_cb._bot = bot

        await dp.feed_update(bot, upd_cb)

        cb_stale.answer.assert_awaited_once()
        alert_msg = cb_stale.answer.await_args.args[0] if cb_stale.answer.await_args.args else cb_stale.answer.await_args.kwargs.get("text", "")
        assert "не активна" in alert_msg.lower()
        cb_stale.message.edit_reply_markup.assert_awaited_with(reply_markup=None)


@pytest.mark.asyncio
async def test_vymoha_and_nakladna_warehouse_operations(tmp_path):
    """Verify that saving a Вимога creates expense transactions and reduces balance, while Накладна creates income."""
    from kolobot.main import _detect_doc_type_and_op, _save_to_warehouse
    from kolobot.warehouse_db import WarehouseDB

    wdb_path = str(tmp_path / "wh.db")
    wdb = WarehouseDB(wdb_path)
    wdb.init_db()

    fs = FileStore(downloads_path=str(tmp_path / "downloads"))

    # 1. Test detection
    vymoha_doc = Document(
        doc_type="invoice",  # even if Gemini returns invoice
        title="Вимога № 0000215",
        summary="Вимога-накладна № 0000215 від 15.08.2026 року на видачу зі складу",
        doc_number="0000215",
        doc_date="15.08.2026",
        items=[
            {
                "num": 1,
                "nomenclature_number": "461993787922",
                "name": "АКУМУЛЯТОРНА БАТАРЕЯ 60Ач",
                "quantity": "1.000000",
                "unit": "51",
            },
            {
                "num": 2,
                "nomenclature_number": "461993787923",
                "name": "ЩІТКИ СКЛООЧИСНИКА 600мм",
                "quantity": "8.000000",
                "unit": "51",
            },
        ],
        raw_text="ВИМОГА № 0000215\nВІДПУСТИВ: комірник\nОДЕРЖАВ: МЕХАНІК СІДОРЕНКО",
    )
    doc_type_label, default_op = _detect_doc_type_and_op(vymoha_doc)
    assert doc_type_label == "ВИМОГА"
    assert default_op == "expense"

    # 2. First create initial stock via a Накладна (income)
    nakladna_doc = Document(
        doc_type="invoice",
        title="Накладна № 100",
        summary="Прибуткова накладна від постачальника",
        doc_number="100",
        doc_date="01.08.2026",
        items=[
            {
                "num": 1,
                "nomenclature_number": "461993787922",
                "name": "АКУМУЛЯТОРНА БАТАРЕЯ 60Ач",
                "quantity": "10",
                "unit": "51",
            },
            {
                "num": 2,
                "nomenclature_number": "461993787923",
                "name": "ЩІТКИ СКЛООЧИСНИКА 600мм",
                "quantity": "20",
                "unit": "51",
            },
        ],
        raw_text="НАКЛАДНА № 100\nПОСТАЧАЛЬНИК: ТОВ Батареї",
    )
    _save_to_warehouse(
        wdb=wdb,
        fs=fs,
        doc=nakladna_doc,
        pending={"file_name": "nakl100.jpg", "mime": "image/jpeg", "ext": ".jpg"},
        archive_doc_id="arc_nakl100",
    )

    items_after_income = wdb.get_items_with_balance()
    assert len(items_after_income) == 2
    item_map = {it["sku"]: it for it in items_after_income}
    assert item_map["461993787922"]["balance"] == 10.0
    assert item_map["461993787923"]["balance"] == 20.0

    # 3. Now save the Вимога (expense)
    _save_to_warehouse(
        wdb=wdb,
        fs=fs,
        doc=vymoha_doc,
        pending={"file_name": "vymoha215.jpg", "mime": "image/jpeg", "ext": ".jpg"},
        archive_doc_id="arc_vym215",
    )

    # 4. Check balances after expense
    items_after_expense = wdb.get_items_with_balance()
    item_map = {it["sku"]: it for it in items_after_expense}
    assert item_map["461993787922"]["balance"] == 9.0  # 10 - 1 = 9
    assert item_map["461993787923"]["balance"] == 12.0  # 20 - 8 = 12

    # 5. Check transactions for the Вимога document
    docs = wdb.get_documents()
    assert len(docs) == 2
    vymoha_db_doc = next(d for d in docs if d["doc_number"] == "0000215")
    assert vymoha_db_doc["doc_type"] == "ВИМОГА"

    impacts = wdb.get_document_impact(vymoha_db_doc["id"])
    assert len(impacts) == 2
    for imp in impacts:
        assert imp["operation_type"] == "expense"
        assert "Поз." in imp["source_row"]

    # 6. Test Condensator invoice with 'відпуск' in summary
    condensator_doc = Document(
        doc_type="накладна",
        title="Накладна № 00002143",
        summary="Накладна № 00002143 від 03.08.2026 на відпуск матеріалу КОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В у кількості 250 шт на суму 12.50 грн.",
        doc_number="00002143",
        doc_date="03.08.2026",
        items=[
            {
                "num": 1,
                "nomenclature_number": "288410091721",
                "name": "КОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В",
                "quantity": "250.000000",
                "unit": "17",
            }
        ],
        raw_text=(
            "НАКЛАДНА № К.ГР ДАТА ЛИСТ № ОПЕР СКЛ СКЛ ОТРИМ\n"
            "00002143 1 03.08.2026 16:09:52 1 3 212 402\n"
            "ЧЕРЕЗ КОГО 7939 - (ПІВ) ЗАМОВЛЕННЯ СТ. ВИТРАТ\n"
            "ЗАТРЕБУВАВ начальник служби (ПІВ)\n"
            "1 | 288410091721 | КОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В | 17 | 250.000000 | 250.000000 00 | 0.05 | 12.50\n"
            "БУХГАЛТЕР: ВІДПУСТИВ: службовець на складі (комірник) (ПІВ) ОДЕРЖАВ: службовець на складі (комірник) (ПІВ)"
        ),
    )
    doc_type_label, default_op = _detect_doc_type_and_op(condensator_doc)
    assert doc_type_label == "НАКЛАДНА"
    assert default_op == "income"

    _save_to_warehouse(
        wdb=wdb,
        fs=fs,
        doc=condensator_doc,
        pending={"file_name": "condensator.jpg", "mime": "image/jpeg", "ext": ".jpg"},
        archive_doc_id="arc_cond2143",
    )

    items_all = wdb.get_items_with_balance()
    cond_item = next(it for it in items_all if it["sku"] == "288410091721")
    assert cond_item["balance"] == 250.0
    assert cond_item["total_income"] == 250.0
    assert cond_item["total_expense"] == 0.0

    cond_txs = wdb.get_item_transactions(cond_item["id"])
    assert len(cond_txs) == 1
    assert cond_txs[0]["operation_type"] == "income"
    assert cond_txs[0]["doc_type"] == "НАКЛАДНА"
    assert cond_txs[0]["quantity"] == 250.0

    wdb.close()


@pytest.mark.asyncio
async def test_save_card_retry_status_updates_and_error(tmp_path):
    """Verify that during saving with retries, status messages are created and edited in Telegram."""
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

        item = QueueItem(
            file_id="fid_retry_1",
            file_unique_id="uid_retry_1",
            mime="image/jpeg",
            file_size=1000,
            tmp_path=str(tmp_path / "retry.jpg"),
            chat_id=100,
            user_id=100,
        )
        doc = Document(doc_type="invoice", title="Тестовий документ")
        card = PendingCard("card_retry_1", item, doc, DocStructurer().to_card(doc))
        queue_service._pending_cards["card_retry_1"] = card

        status_msg_mock = AsyncMock()
        status_msg_mock.edit_text = AsyncMock()

        cb = _make_callback_query("confirm_save:card_retry_1", user_id=100)
        cb.message.answer = AsyncMock(return_value=status_msg_mock)

        upd = Update(update_id=1, callback_query=cb)
        upd._bot = bot

        async def mock_save_with_retry(*args, **kwargs):
            on_status = kwargs.get("on_status_update")
            if on_status:
                await on_status("🔄 Помилка збереження. Спроба 1/3. Повтор через 10с...")
                await on_status("🔄 Помилка збереження. Спроба 2/3. Повтор через 30с...")
            return SimpleNamespace(
                success=False,
                doc_id="doc_retry",
                disk_warning=False,
                error="Недійсний API ключ для ембеддінгів (GEMINI_KEYS_EMBED). Перевірте ключ у файлі .env.",
            )

        with patch("kolobot.archive_service.ArchiveService.save", side_effect=mock_save_with_retry):
            await dp.feed_update(bot, upd)

            cb.message.answer.assert_awaited_once_with("🔄 Помилка збереження. Спроба 1/3. Повтор через 10с...")
            assert status_msg_mock.edit_text.await_count == 2
            # 1st edit: second retry
            status_msg_mock.edit_text.assert_any_await("🔄 Помилка збереження. Спроба 2/3. Повтор через 30с...")
            # 2nd edit: final error
            assert any(
                "Помилка збереження: Недійсний API ключ для ембеддінгів" in call.args[0]
                for call in status_msg_mock.edit_text.await_args_list
            )




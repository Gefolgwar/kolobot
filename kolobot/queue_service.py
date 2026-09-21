"""DocumentQueueService: asynchronous FIFO queue and background worker loop for OCR intake."""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from kolobot.doc_structurer import CardViewModel, DocStructurer, Document, ParseStatus
from kolobot.file_store import FileStore
from kolobot.gemini_gateway import GeminiGateway
from kolobot.log_service import get_global_log_buffer

logger = logging.getLogger(__name__)


@dataclass
class QueueItem:
    file_id: str
    file_unique_id: str
    mime: str
    file_size: int
    tmp_path: str
    chat_id: int
    user_id: int
    status_message_id: Optional[int] = None
    source: str = "photo"
    file_name: Optional[str] = None
    ext: str = ".jpg"
    wh_doc_id: Optional[int] = None
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: float = field(default_factory=time.time)


@dataclass
class PendingCard:
    card_id: str
    item: QueueItem
    doc: Document
    card: CardViewModel
    created_at: float = field(default_factory=time.time)


@dataclass
class ClearResult:
    cancelled_active: int
    drained_queue: int
    cleared_cards: int
    deleted_files: int


def _supports_status_update(fn: Any) -> bool:
    target = getattr(fn, "side_effect", None) or fn
    try:
        sig = inspect.signature(target)
        for param in sig.parameters.values():
            if param.kind == inspect.Parameter.VAR_KEYWORD or param.name == "on_status_update":
                return True
        return False
    except (ValueError, TypeError):
        return False


DEFAULT_RETRY_DELAYS = (5.0, 15.0, 30.0)


class DocumentQueueService:
    """
    Manages an in-memory FIFO queue for incoming documents and processes them
    sequentially with a dedicated background worker loop and exponential retry logic.
    """

    def __init__(
        self,
        gateway: GeminiGateway,
        doc_structurer: DocStructurer,
        file_store: FileStore,
        bot: Any = None,
        download_fn: Optional[Callable[[str], Awaitable[bytes]]] = None,
        on_card_ready: Optional[Callable[[PendingCard], Awaitable[None]]] = None,
        on_error: Optional[Callable[[QueueItem, Exception], Awaitable[None]]] = None,
        on_status_update: Optional[Callable[[QueueItem, str], Awaitable[None]]] = None,
        retry_delays: tuple[float, ...] = DEFAULT_RETRY_DELAYS,
        item_delay_sec: float = 0.0,
        warehouse_db: Optional[Any] = None,
        log_buffer: Optional[Any] = None,
        auto_recover: bool = True,
        default_chat_id: int = 0,
        default_user_id: int = 0,
    ) -> None:
        self._gateway = gateway
        self._doc_structurer = doc_structurer
        self._file_store = file_store
        self._bot = bot
        self._download_fn = download_fn
        self._on_card_ready = on_card_ready
        self._on_error = on_error
        self._on_status_update = on_status_update
        self._retry_delays = tuple(float(d) for d in retry_delays)
        self._item_delay_sec = float(item_delay_sec)
        self._warehouse_db = warehouse_db
        self._log_buffer = log_buffer if log_buffer is not None else get_global_log_buffer()
        self._auto_recover = auto_recover
        self._default_chat_id = int(default_chat_id)
        self._default_user_id = int(default_user_id)

        self._queue: asyncio.Queue[QueueItem] = asyncio.Queue()
        self._pending_cards: Dict[str, PendingCard] = {}
        self._worker_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._current_item: Optional[QueueItem] = None
        self._recovering: bool = False
        self._recovered: bool = False

    async def start(self) -> None:
        """Start background worker task if not already running, running crash recovery if enabled."""
        if self._worker_task is None or self._worker_task.done():
            self._running = True
            self._worker_task = asyncio.create_task(
                self._worker_loop(), name="document_queue_worker"
            )
            logger.info("DocumentQueueService background worker started.")
            if self._auto_recover and not self._recovered and self._warehouse_db:
                self._recovered = True
                try:
                    await self.recover_pending(
                        default_chat_id=self._default_chat_id,
                        default_user_id=self._default_user_id,
                    )
                except Exception as exc:
                    logger.error("Error during crash recovery on start: %s", exc)

    async def recover_pending(
        self,
        default_chat_id: Optional[int] = None,
        default_user_id: Optional[int] = None,
    ) -> int:
        """Recover unprocessed documents (queued, processing_ocr, processing_emb) from warehouse DB."""
        if not self._warehouse_db or self._recovering:
            return 0
        self._recovering = True
        try:
            unprocessed = self._warehouse_db.get_unprocessed_documents()
            if not unprocessed:
                return 0

            target_chat_id = self._default_chat_id if default_chat_id is None else default_chat_id
            target_user_id = self._default_user_id if default_user_id is None else default_user_id

            existing_doc_ids = set()
            if self._current_item and self._current_item.wh_doc_id is not None:
                existing_doc_ids.add(self._current_item.wh_doc_id)
            for q_item in list(self._queue._queue):
                if q_item.wh_doc_id is not None:
                    existing_doc_ids.add(q_item.wh_doc_id)

            count = 0
            for doc in unprocessed:
                doc_id = doc["id"]
                if doc_id in existing_doc_ids:
                    continue
                file_path = doc.get("file_path", "")
                filename = doc.get("filename", "recovered.jpg")
                file_type = doc.get("file_type", "photo")
                ext = os.path.splitext(file_path)[1] or os.path.splitext(filename)[1] or ".jpg"
                mime = "application/pdf" if ext.lower() == ".pdf" else "image/jpeg"
                size = os.path.getsize(file_path) if (file_path and os.path.exists(file_path)) else 0

                # Reset status in DB to queued
                self._warehouse_db.update_document(doc_id, status="queued")

                chat_id = doc.get("chat_id") or target_chat_id or 0
                user_id = doc.get("user_id") or target_user_id or 0
                file_id = doc.get("file_id") or f"recovered_{doc_id}"

                item = QueueItem(
                    file_id=file_id,
                    file_unique_id=f"recovered_uniq_{doc_id}",
                    mime=mime,
                    file_size=size,
                    tmp_path=file_path,
                    chat_id=chat_id,
                    user_id=user_id,
                    status_message_id=None,
                    source=file_type,
                    file_name=filename,
                    ext=ext,
                    wh_doc_id=doc_id,
                )
                await self._queue.put(item)
                count += 1

            msg = f"Crash recovery: restored and enqueued {count} unprocessed document(s)"
            logger.info(msg)
            if self._log_buffer:
                self._log_buffer.add_entry(level="INFO", logger_name="kolobot.queue_service", message=msg)
            return count
        finally:
            self._recovering = False

    async def stop(self) -> None:
        """Cancel and stop the background worker task."""
        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("DocumentQueueService background worker stopped.")

    async def clear(self) -> ClearResult:
        """
        Abort active in-flight OCR task, drain all items from the queue,
        purge all pending cards, delete temporary files, and restart a clean worker loop.
        """
        cancelled_active = 0
        deleted_files = 0

        # 1. Abort in-flight task if running
        active_item = self._current_item
        if active_item is not None:
            cancelled_active = 1

        self._running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

        if active_item and active_item.tmp_path:
            try:
                self._file_store.delete_tmp(active_item.tmp_path)
                deleted_files += 1
            except Exception as exc:
                logger.warning("Failed to delete active item tmp file %s: %s", active_item.tmp_path, exc)
        self._current_item = None

        # 2. Drain all waiting items from the queue
        drained_queue = 0
        while not self._queue.empty():
            try:
                item = self._queue.get_nowait()
                self._queue.task_done()
                drained_queue += 1
                if item.tmp_path:
                    try:
                        self._file_store.delete_tmp(item.tmp_path)
                        deleted_files += 1
                    except Exception as exc:
                        logger.warning("Failed to delete queued item tmp file %s: %s", item.tmp_path, exc)
            except asyncio.QueueEmpty:
                break

        # 3. Purge all pending cards
        cleared_cards = len(self._pending_cards)
        for card in list(self._pending_cards.values()):
            if card.item.tmp_path:
                try:
                    self._file_store.delete_tmp(card.item.tmp_path)
                    deleted_files += 1
                except Exception as exc:
                    logger.warning("Failed to delete pending card tmp file %s: %s", card.item.tmp_path, exc)
        self._pending_cards.clear()

        # 4. Restart clean worker loop
        await self.start()

        logger.info(
            "DocumentQueueService cleared: cancelled=%d, drained=%d, cards=%d, files=%d",
            cancelled_active,
            drained_queue,
            cleared_cards,
            deleted_files,
        )

        return ClearResult(
            cancelled_active=cancelled_active,
            drained_queue=drained_queue,
            cleared_cards=cleared_cards,
            deleted_files=deleted_files,
        )

    async def enqueue(self, item: QueueItem | Dict[str, Any]) -> str:
        """
        Put item into FIFO queue. Automatically starts worker if not running.
        Returns item_id.
        """
        if isinstance(item, dict):
            queue_item = QueueItem(
                file_id=item["file_id"],
                file_unique_id=item["file_unique_id"],
                mime=item.get("mime", "image/jpeg"),
                file_size=item.get("file_size", 0),
                tmp_path=item["tmp_path"],
                chat_id=item["chat_id"],
                user_id=item["user_id"],
                status_message_id=item.get("status_message_id"),
                source=item.get("source", "photo"),
                file_name=item.get("file_name"),
                ext=item.get("ext", ".jpg"),
            )
        else:
            queue_item = item

        await self._queue.put(queue_item)
        await self.start()
        logger.info(
            "Enqueued item %s (file_id=%s, queue_size=%d)",
            queue_item.item_id,
            queue_item.file_id,
            self._queue.qsize(),
        )
        return queue_item.item_id

    async def join(self) -> None:
        """Wait until all items in the queue have been processed."""
        await self._queue.join()

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    def get_queue_length(self) -> int:
        return self._queue.qsize()

    def get_queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def is_processing(self) -> bool:
        return self._current_item is not None

    @property
    def is_running(self) -> bool:
        return self._worker_task is not None and not self._worker_task.done()

    def get_card(self, card_id: str) -> Optional[PendingCard]:
        return self._pending_cards.get(card_id)

    def remove_card(self, card_id: str) -> Optional[PendingCard]:
        return self._pending_cards.pop(card_id, None)

    def list_pending_cards(self, user_id: Optional[int] = None) -> List[PendingCard]:
        if user_id is None:
            return list(self._pending_cards.values())
        return [c for c in self._pending_cards.values() if c.item.user_id == user_id]

    def get_pending_card_count(self, user_id: Optional[int] = None) -> int:
        return len(self.list_pending_cards(user_id))

    async def _worker_loop(self) -> None:
        """Continuously process queued items in strict FIFO order."""
        while self._running:
            try:
                item = await self._queue.get()
            except asyncio.CancelledError:
                break

            self._current_item = item
            try:
                await self._process_item(item)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Error processing queue item %s: %s", item.item_id, exc)
                if self._on_error:
                    try:
                        await self._on_error(item, exc)
                    except Exception as callback_err:
                        logger.error("Error in on_error callback: %s", callback_err)
            finally:
                self._current_item = None
                self._queue.task_done()
                if self._item_delay_sec > 0 and self._running:
                    await asyncio.sleep(self._item_delay_sec)

    async def _update_status(self, item: QueueItem, text: str) -> None:
        """Update live status message in Telegram or notify callback."""
        if self._on_status_update:
            try:
                await self._on_status_update(item, text)
            except Exception as exc:
                logger.error("Error in on_status_update callback: %s", exc)

        if self._bot:
            edited = False
            if item.status_message_id is not None:
                try:
                    await self._bot.edit_message_text(
                        chat_id=item.chat_id,
                        message_id=item.status_message_id,
                        text=text,
                    )
                    edited = True
                except Exception as exc:
                    logger.debug("Failed to edit Telegram status message %s: %s", item.status_message_id, exc)
            if not edited and item.status_message_id is None and ("❌" in text or "Помилка" in text):
                try:
                    await self._bot.send_message(
                        chat_id=item.chat_id,
                        text=text,
                    )
                except Exception as exc:
                    logger.debug("Failed to send error message to Telegram chat %s: %s", item.chat_id, exc)

    async def _process_item(self, item: QueueItem) -> None:
        """Download file, call Gemini OCR extraction with exponential retry logic, parse with DocStructurer, register PendingCard."""
        if self._warehouse_db and item.wh_doc_id is not None:
            self._warehouse_db.update_document(item.wh_doc_id, status="processing_ocr")
            await self._update_status(item, f"🔄 Розпізнавання (#{item.wh_doc_id})...")

        max_retries = len(self._retry_delays)
        total_attempts = 1 + max_retries

        for attempt in range(total_attempts):
            if attempt > 0:
                delay = self._retry_delays[attempt - 1]
                if delay < 1.0:
                    status_text = (
                        f"🔄 Помилка розпізнавання. Спроба {attempt}/{max_retries}. "
                        f"Повтор через {int(delay)}с..."
                    )
                    await self._update_status(item, status_text)
                    await asyncio.sleep(delay)
                else:
                    rem = int(delay)
                    while rem > 0 and self._running:
                        status_text = (
                            f"🔄 Помилка розпізнавання. Спроба {attempt}/{max_retries}. "
                            f"Повтор через {rem}с..."
                        )
                        await self._update_status(item, status_text)
                        await asyncio.sleep(1.0)
                        rem -= 1

            try:
                # 1. Obtain image/document bytes
                image_bytes: bytes = b""
                if os.path.exists(item.tmp_path) and os.path.getsize(item.tmp_path) > 0:
                    with open(item.tmp_path, "rb") as f:
                        image_bytes = f.read()
                elif self._download_fn:
                    image_bytes = await self._download_fn(item.file_id)
                elif self._bot:
                    raw_io = await self._bot.download(item.file_id)
                    image_bytes = raw_io.read() if hasattr(raw_io, "read") else raw_io

                if not image_bytes:
                    raise ValueError(f"Failed to acquire bytes for item {item.item_id} (file_id={item.file_id})")

                # Ensure bytes are written to tmp_path
                os.makedirs(os.path.dirname(os.path.abspath(item.tmp_path)), exist_ok=True)
                with open(item.tmp_path, "wb") as f:
                    f.write(image_bytes)

                # 2. Call OCR via Gemini Gateway
                async def _on_gw_status(status_msg: str) -> None:
                    await self._update_status(item, status_msg)

                gw_kwargs: Dict[str, Any] = {
                    "image_bytes": image_bytes,
                    "mime": item.mime,
                    "file_path": item.tmp_path,
                }
                if _supports_status_update(self._gateway.extract_document):
                    gw_kwargs["on_status_update"] = _on_gw_status

                model_text = await self._gateway.extract_document(**gw_kwargs)

                # 3. Parse with DocStructurer
                result = self._doc_structurer.parse(model_text)
                if result.status == ParseStatus.NEEDS_RETRY:
                    model_text2 = await self._gateway.extract_document(**gw_kwargs)
                    result = self._doc_structurer.parse(model_text2, is_retry=True)

                if result.doc is None or result.doc.is_empty:
                    raise ValueError("Document recognition returned empty result")

                if self._warehouse_db and item.wh_doc_id is not None:
                    self._warehouse_db.update_document(item.wh_doc_id, status="processing_emb")
                    await self._update_status(item, f"🧠 Embeddings (#{item.wh_doc_id})...")

                # 4. Generate unique short card_id and create PendingCard
                card_id = self._generate_card_id()
                card_view = self._doc_structurer.to_card(result.doc)
                pending_card = PendingCard(
                    card_id=card_id,
                    item=item,
                    doc=result.doc,
                    card=card_view,
                )

                self._pending_cards[card_id] = pending_card
                logger.info(
                    "Registered pending card %s for item %s (title=%s)",
                    card_id,
                    item.item_id,
                    card_view.title,
                )

                # 5. Notify callback if provided
                if self._on_card_ready:
                    try:
                        await self._on_card_ready(pending_card)
                    except Exception as exc:
                        logger.error("Error in on_card_ready callback: %s", exc)

                return

            except Exception as exc:
                if attempt < max_retries:
                    warn_msg = (
                        f"Attempt {attempt + 1}/{total_attempts} failed for item {item.item_id} "
                        f"(doc #{item.wh_doc_id}): {exc}. Retrying..."
                    )
                    logger.warning(warn_msg)
                    if self._log_buffer:
                        self._log_buffer.add_entry(
                            level="WARN",
                            logger_name="kolobot.queue_service",
                            message=warn_msg,
                        )
                else:
                    err_msg = (
                        f"All {total_attempts} attempts exhausted for item {item.item_id} "
                        f"(doc #{item.wh_doc_id}): {exc}"
                    )
                    logger.error(err_msg)
                    if self._log_buffer:
                        self._log_buffer.add_entry(
                            level="ERR",
                            logger_name="kolobot.queue_service",
                            message=err_msg,
                        )
                    if self._warehouse_db and item.wh_doc_id is not None:
                        self._warehouse_db.update_document(
                            item.wh_doc_id,
                            status="error",
                            error_message=str(exc) or "All retry attempts exhausted",
                        )
                    error_text = f"❌ Не вдалося розпізнати документ після {max_retries} повторних спроб."
                    await self._update_status(item, error_text)
                    try:
                        if os.path.exists(item.tmp_path):
                            self._file_store.delete_tmp(item.tmp_path)
                    except Exception as cleanup_err:
                        logger.warning("Failed to delete tmp file %s: %s", item.tmp_path, cleanup_err)
                    raise

    def _generate_card_id(self) -> str:
        """Generate a short unique 8-character hex card_id that does not collide with active cards."""
        while True:
            candidate = uuid.uuid4().hex[:8]
            if candidate not in self._pending_cards:
                return candidate

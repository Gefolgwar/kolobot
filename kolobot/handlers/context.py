"""``AppContext``: everything a Telegram handler is allowed to touch.

A handler module exposes ``register(router, ctx)`` and reaches the stores, the
queue, the pools and the bot only through the context — which is why a handler
module never imports ``build_app`` and never imports another handler module.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from aiogram import Bot

from kolobot.archive_service import ArchiveService
from kolobot.file_store import FileStore
from kolobot.handlers.list_delete import ListDeleteHandler
from kolobot.handlers.media import MediaHandler
from kolobot.intake_service import DocumentIntakeService
from kolobot.key_pool import KeyPool
from kolobot.queue_service import DocumentQueueService
from kolobot.rag_service import RagService
from kolobot.vector_store import VectorStore
from kolobot.warehouse_db import WarehouseDB


@dataclass
class AppContext:
    """Built once by ``build_app``, closed over by every handler."""

    owner_user_id: int
    bot: Bot
    gen_pool: KeyPool
    emb_pool: KeyPool
    archive_service: ArchiveService
    rag_service: RagService
    intake_service: DocumentIntakeService
    media_handler: MediaHandler
    list_delete: ListDeleteHandler
    vector_store: VectorStore
    warehouse_db: WarehouseDB
    file_store: FileStore
    # The queue is built with ``on_card_ready``, and that callback needs the
    # context — so the context exists first and this field is filled in
    # immediately after the queue is constructed.
    queue_service: Optional[DocumentQueueService] = None

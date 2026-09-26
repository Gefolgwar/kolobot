"""Process entrypoint: load config, wire bot, run polling.

The composition root and nothing else. Every service is built here and handed
to the handlers through an ``AppContext``. The handlers live in
``kolobot/handlers/``, one module per feature, each exposing
``register(router, ctx)`` and reaching the outside world only through the
context.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent

from kolobot.archive_service import ArchiveService
from kolobot.config import ConfigError, load_config
from kolobot.doc_structurer import DocStructurer
from kolobot.file_store import FileStore
from kolobot.gemini_gateway import GeminiError, GeminiGateway
from kolobot.handlers import cards, files, manage, query
from kolobot.handlers.commands import router as commands_router
from kolobot.handlers.context import AppContext
from kolobot.handlers.list_delete import ListDeleteHandler
from kolobot.handlers.media import MediaHandler
from kolobot.intake_service import DocumentIntakeService
from kolobot.key_pool import KeyPool, PoolKind
from kolobot.log_service import setup_logging_capture
from kolobot.middlewares.access import AccessMiddleware
from kolobot.queue_service import DocumentQueueService
from kolobot.rag_service import RagService
from kolobot.startup import _sync_chroma_with_warehouse
from kolobot.vector_store import VectorStore
from kolobot.warehouse_db import WarehouseDB

# Not used here. Kept because the tests import them from kolobot.main; the code
# itself lives in the module on the right.
from kolobot.archive_delivery import send_archive_file  # noqa: F401
from kolobot.card_view import format_card_text, make_card_keyboard  # noqa: F401
from kolobot.warehouse_writer import _detect_doc_type_and_op, _save_to_warehouse  # noqa: F401

logger = logging.getLogger(__name__)


def build_app():
    """Construct all deep modules and wire together. Returns (dp, bot, settings)."""
    settings = load_config()

    gen_pool = KeyPool(
        keys=settings.gemini_keys_generate,
        kind=PoolKind.GENERATE,
        rpm_limit=settings.rpm_limit,
        rpd_limit=settings.rpd_limit,
        cooldown_sec=settings.cooldown_sec,
    )
    emb_pool = KeyPool(
        keys=settings.gemini_keys_embed,
        kind=PoolKind.EMBED,
        rpm_limit=settings.rpm_limit,
        rpd_limit=settings.rpd_limit,
        cooldown_sec=settings.cooldown_sec,
    )

    file_store = FileStore(downloads_path=settings.downloads_path)
    vector_store = VectorStore(chroma_path=settings.chroma_path)
    warehouse_db = WarehouseDB(db_path=settings.warehouse_db_path)
    warehouse_db.init_db()

    gateway = GeminiGateway(
        gen_pool=gen_pool,
        emb_pool=emb_pool,
        generate_model=settings.generate_model,
        embed_model=settings.embed_model,
    )
    archive_svc = ArchiveService(
        gateway=gateway, vector_store=vector_store, file_store=file_store
    )
    rag_svc = RagService(
        gateway=gateway,
        vector_store=vector_store,
        top_k=settings.rag_top_k,
        max_distance=settings.rag_max_distance,
    )
    doc_structurer = DocStructurer()
    media_handler = MediaHandler(owner_user_id=settings.owner_user_id)
    list_delete = ListDeleteHandler(
        vector_store=vector_store,
        file_store=file_store,
        owner_user_id=settings.owner_user_id,
    )
    intake_service = DocumentIntakeService(
        file_store=file_store,
        warehouse_db=warehouse_db,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    ctx = AppContext(
        owner_user_id=settings.owner_user_id,
        bot=bot,
        gen_pool=gen_pool,
        emb_pool=emb_pool,
        archive_service=archive_svc,
        rag_service=rag_svc,
        intake_service=intake_service,
        media_handler=media_handler,
        list_delete=list_delete,
        vector_store=vector_store,
        warehouse_db=warehouse_db,
        file_store=file_store,
    )

    queue_service = DocumentQueueService(
        gateway=gateway,
        doc_structurer=doc_structurer,
        file_store=file_store,
        bot=bot,
        on_card_ready=lambda card: cards.on_card_ready(ctx, card),
        item_delay_sec=getattr(settings, "queue_item_delay_sec", 3.0),
        warehouse_db=warehouse_db,
        default_chat_id=settings.owner_user_id,
        default_user_id=settings.owner_user_id,
    )
    ctx.queue_service = queue_service

    # --- Router wiring ---
    # Order matters: the catch-all text handler in query.py goes last, or it
    # would swallow the media that files.py is waiting for.
    rt = Router(name="app")
    manage.register(rt, ctx)
    files.register(rt, ctx)
    cards.register(rt, ctx)
    query.register(rt, ctx)

    # --- Build dispatcher ---
    dp = Dispatcher()
    dp["queue_service"] = queue_service
    dp["gemini_gateway"] = gateway
    dp["vector_store"] = vector_store
    dp["archive_service"] = archive_svc
    dp["warehouse_db"] = warehouse_db
    access = AccessMiddleware(owner_user_id=settings.owner_user_id)
    dp.message.middleware(access)
    dp.callback_query.middleware(access)
    commands_router._parent_router = None
    dp.include_router(commands_router)
    dp.include_router(rt)

    @dp.errors()
    async def _on_error(event: ErrorEvent, bot: Bot) -> bool:
        exc = event.exception
        update = event.update

        chat_id = None
        if update.message:
            chat_id = update.message.chat.id
        elif update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat.id

        logger.error("Unhandled error: %s: %s", type(exc).__name__, exc, exc_info=exc)

        if chat_id is None:
            return True

        try:
            from google.genai.errors import ClientError
        except ImportError:
            ClientError = None

        if ClientError is not None and isinstance(exc, ClientError):
            code = getattr(exc, "code", None) or 0
            if code == 403:
                text = "API ключ заблоковано або проєкт недоступний. Зверніться до підтримки Google або замініть ключ."
            elif code == 429:
                text = "Перевищено ліміт запитів до API. Спробуйте пізніше."
            else:
                text = f"Помилка API Google (HTTP {code}). Спробуйте пізніше."
        elif isinstance(exc, GeminiError):
            text = str(exc)
        else:
            text = "Виникла внутрішня помилка. Спробуйте пізніше або зверніться до адміністратора."

        try:
            await bot.send_message(chat_id, text)
        except Exception:
            logger.warning("Failed to send error message to chat %s", chat_id)

        return True

    # Startup: GC tmp
    file_store.gc_tmp()
    logger.info("Startup tmp GC done.")

    # Startup: sync ChromaDB with warehouse DB — remove orphaned records and files
    _sync_chroma_with_warehouse(vector_store, warehouse_db, file_store, settings.owner_user_id)

    if settings.web_enabled:
        from kolobot.web_server import WebServer
        dp["web_server"] = WebServer(
            warehouse_db=warehouse_db,
            file_store=file_store,
            vector_store=vector_store,
            owner_user_id=settings.owner_user_id,
            host=settings.web_host,
            port=settings.web_port,
            queue_service=queue_service,
        )

    return dp, bot, settings


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    setup_logging_capture()
    try:
        dp, bot, settings = build_app()
    except ConfigError as exc:
        logger.error("Config error: %s", exc)
        raise SystemExit(2) from exc

    web_server = dp.workflow_data.get("web_server")
    if web_server:
        await web_server.start()

    queue_service: DocumentQueueService = dp.get("queue_service") or dp.workflow_data.get("queue_service")
    if queue_service:
        await queue_service.start()

    logger.info("kolobot starting for owner_user_id=%s, model=%s",
                settings.owner_user_id, settings.generate_model)
    try:
        await dp.start_polling(bot)
    finally:
        if queue_service:
            await queue_service.stop()
        if web_server:
            await web_server.stop()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()

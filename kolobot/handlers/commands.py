"""Command handlers: /start, /help, /status (and later /list, /delete)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from kolobot.messages import HELP_UK, START_UK

if TYPE_CHECKING:
    from kolobot.key_pool import KeyPool
    from kolobot.queue_service import DocumentQueueService

router = Router(name="commands")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(START_UK)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_UK)


async def cmd_clear(
    message: Message,
    *,
    queue_service: "DocumentQueueService",
) -> None:
    """Clear in-flight tasks, drain queue, purge cards, and report summary."""
    result = await queue_service.clear()
    text = (
        "🧹 <b>Чергу та активні завдання очищено:</b>\n"
        f"• Скасовано активних задач: {result.cancelled_active}\n"
        f"• Очищено документів з черги: {result.drained_queue}\n"
        f"• Видалено незбережених карток: {result.cleared_cards}\n"
        f"• Видалено тимчасових файлів: {result.deleted_files}"
    )
    await message.answer(text)


async def cmd_status(
    message: Message,
    *,
    gen_pool: Optional["KeyPool"] = None,
    emb_pool: Optional["KeyPool"] = None,
    queue_service: Optional["DocumentQueueService"] = None,
) -> None:
    """Display status of document processing queue, pending cards, and API key pools."""
    sections: list[str] = []

    if queue_service is not None:
        active = 1 if queue_service.is_processing else 0
        in_queue = queue_service.queue_size
        total_processing = active + in_queue
        pending_cards = queue_service.get_pending_card_count()

        status_lines = [
            "📊 <b>Статус обробки:</b>",
            f"• Файлів в обробці: {total_processing}" + (f" (активних: {active}, у черзі: {in_queue})" if in_queue > 0 else ""),
            f"• Очікують рішення (кнопок): {pending_cards}",
        ]
        sections.append("\n".join(status_lines))

    if gen_pool is not None and emb_pool is not None:
        gs = gen_pool.status()
        es = emb_pool.status()
        pool_lines = [
            "🔑 <b>Стан ключів API:</b>",
            f"• <b>Generate pool:</b> {gs['available']}/{gs['total']} доступно (cooldown: {gs['cooldown']}, limited: {gs['limited']})",
        ]
        if hasattr(gen_pool, "get_key_status_list"):
            for k in gen_pool.get_key_status_list():
                pool_lines.append(f"  └ {k['label']}: {k['status_desc']}")

        pool_lines.append(
            f"• <b>Embed pool:</b> {es['available']}/{es['total']} доступно (cooldown: {es['cooldown']}, limited: {es['limited']})"
        )
        if hasattr(emb_pool, "get_key_status_list"):
            for k in emb_pool.get_key_status_list():
                pool_lines.append(f"  └ {k['label']}: {k['status_desc']}")

        sections.append("\n".join(pool_lines))

    text = "\n\n".join(sections) if sections else "Інформація про статус недоступна."
    await message.answer(text)

"""Free-text questions against the archive, and the file buttons on the answers."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from kolobot.archive_delivery import send_archive_file
from kolobot.card_view import h
from kolobot.handlers.context import AppContext


def register(router: Router, ctx: AppContext) -> None:
    """Put file delivery and the RAG answer on ``router``.

    Register this one last: the text handler below catches every message that
    is not a command, and would otherwise swallow the media the other modules
    are waiting for.
    """

    @router.callback_query(F.data.startswith("file:"))
    async def _send_file(callback: CallbackQuery):
        doc_id = callback.data.split(":", 1)[1]
        doc = ctx.vector_store.get(doc_id)
        if doc and callback.message:
            await send_archive_file(
                message=callback.message,
                file_store=ctx.file_store,
                doc_id=doc_id,
                metadata=doc.get("metadata", {}),
                error_text="Не вдалося надіслати файл.",
            )
        elif callback.message:
            await callback.message.answer("Не вдалося надіслати файл.")
        await callback.answer()

    @router.message(~Command("start", "help", "status", "list", "delete", "clear"))
    async def _text(message: Message):
        if message.photo or message.document:
            return
        text = (message.text or "").strip()
        if not text:
            return
        rag_result = await ctx.rag_service.answer(
            user_id=ctx.owner_user_id, question=text
        )
        if rag_result.trivial:
            return
        if rag_result.empty_archive:
            await message.answer("Архів порожній — спершу надішли зображення документів.")
            return
        if rag_result.not_found:
            await message.answer("Не знайшов відповідної інформації в архіві.")
            return

        buttons = []
        for src in rag_result.sources:
            buttons.append([InlineKeyboardButton(
                text=f"📎 {src['doc_id']}",
                callback_data=f"file:{src['doc_id']}",
            )])
        kb = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None
        await message.answer(h(rag_result.answer), reply_markup=kb)

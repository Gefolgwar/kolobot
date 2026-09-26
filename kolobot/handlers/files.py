"""Media intake: taking a photo or a document, and the duplicate-file prompts."""

from __future__ import annotations

import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from kolobot.archive_delivery import send_archive_file
from kolobot.handlers.context import AppContext
from kolobot.queue_service import QueueItem


def register(router: Router, ctx: AppContext) -> None:
    """Put media intake and the dedup callbacks on ``router``."""
    # Duplicates held back until the user answers. Scoped to this registration
    # rather than to the module: ``build_app`` runs once per test, and an entry
    # left behind by an earlier run would be picked up by the fallback branch
    # of ``_dedup_force`` below.
    dedup_pending: dict[str, dict] = {}

    @router.message(F.photo | F.document)
    async def _media(message: Message):
        intake = await ctx.media_handler.handle_media(message)
        if intake is None:
            return

        unique_id = intake["file_unique_id"]

        # Dedup check in archive and active/queued queue
        existing = ctx.archive_service.lookup_duplicate(
            user_id=ctx.owner_user_id,
            file_unique_id=unique_id,
        )
        is_dup = (existing is not None) or ctx.queue_service.has_file_unique_id(unique_id)

        if is_dup:
            dedup_id = uuid.uuid4().hex[:8]
            dedup_pending[dedup_id] = intake
            existing_id = existing["id"] if existing else ""
            if existing_id:
                kb = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="Відкрити старий", callback_data=f"dedup_open:{existing_id}"),
                    InlineKeyboardButton(text="Все одно зберегти", callback_data=f"dedup_force:{dedup_id}"),
                ]])
                await message.answer("Цей файл вже є в архіві.", reply_markup=kb)
            else:
                await message.answer("Цей файл вже знаходиться в черзі на обробку.")
            return

        # Unsaved cards reminder
        pending_count = ctx.queue_service.get_pending_card_count(user_id=ctx.owner_user_id)
        if pending_count > 0:
            await message.answer(f"ℹ️ Зверни увагу: у тебе є {pending_count} незбережених карток на підтвердження.")

        intake_result = await ctx.intake_service.accept(intake, message.bot)

        status_msg = await message.answer(intake_result.message)
        status_id = getattr(status_msg, "message_id", None)

        item = QueueItem(
            file_id=intake["file_id"],
            file_unique_id=intake["file_unique_id"],
            mime=intake["mime"],
            file_size=intake["file_size"],
            tmp_path=intake_result.file_path,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else ctx.owner_user_id,
            status_message_id=status_id,
            source=intake["source"],
            file_name=intake.get("file_name"),
            ext=intake.get("ext", ".jpg"),
            wh_doc_id=intake_result.doc_id,
        )
        await ctx.queue_service.enqueue(item)

    @router.callback_query(F.data.startswith("dedup_open:"))
    async def _dedup_open(callback: CallbackQuery):
        doc_id = callback.data.split(":", 1)[1]
        doc = ctx.vector_store.get(doc_id)
        meta = doc.get("metadata", {}) if doc else {}
        if meta and callback.message:
            await send_archive_file(
                message=callback.message,
                file_store=ctx.file_store,
                doc_id=doc_id,
                metadata=meta,
                error_text="Не вдалося надіслати оригінал.",
            )
        elif callback.message:
            await callback.message.answer("Не вдалося надіслати оригінал.")

        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        await callback.answer()

    @router.callback_query(F.data.startswith("dedup_force"))
    async def _dedup_force(callback: CallbackQuery):
        parts = callback.data.split(":", 1)
        if len(parts) > 1:
            dedup_id = parts[1]
            intake = dedup_pending.pop(dedup_id, None)
        else:
            intake = next(iter(dedup_pending.values()), None) if dedup_pending else None
            dedup_pending.clear()

        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass

        if intake and callback.message:
            pending_count = ctx.queue_service.get_pending_card_count(user_id=ctx.owner_user_id)
            if pending_count > 0:
                await callback.message.answer(f"ℹ️ Зверни увагу: у тебе є {pending_count} незбережених карток на підтвердження.")

            intake_result = await ctx.intake_service.accept(intake, callback.message.bot)

            status_msg = await callback.message.answer(intake_result.message)
            status_id = getattr(status_msg, "message_id", None)

            item = QueueItem(
                file_id=intake["file_id"],
                file_unique_id=intake["file_unique_id"],
                mime=intake["mime"],
                file_size=intake["file_size"],
                tmp_path=intake_result.file_path,
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id if callback.from_user else ctx.owner_user_id,
                status_message_id=status_id,
                source=intake["source"],
                file_name=intake.get("file_name"),
                ext=intake.get("ext", ".jpg"),
                wh_doc_id=intake_result.doc_id,
            )
            await ctx.queue_service.enqueue(item)

        await callback.answer()

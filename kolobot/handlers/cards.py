"""Pending cards: confirming one into the archive, rejecting one, and the
automatic save that happens when a card is recognised."""

from __future__ import annotations

import logging
import os

from aiogram import F, Router
from aiogram.types import CallbackQuery

from kolobot.card_view import format_card_text
from kolobot.handlers.context import AppContext
from kolobot.queue_service import PendingCard
from kolobot.warehouse_writer import _save_to_warehouse

logger = logging.getLogger(__name__)


async def on_card_ready(ctx: AppContext, pending_card: PendingCard) -> None:
    """Save a recognised card to the archive and the warehouse, then report.

    Passed to ``DocumentQueueService`` as its callback, so it runs on the
    queue's own schedule rather than on a message.
    """
    doc = pending_card.doc
    item = pending_card.item

    # 1. Automatic save to archive / VectorStore (RAG)
    save_result = await ctx.archive_service.save(
        title=doc.title,
        summary=doc.summary,
        key_value_pairs=doc.key_value_pairs,
        raw_text=doc.raw_text,
        tmp_path=item.tmp_path,
        ext=item.ext,
        user_id=item.user_id,
        telegram_file_id=item.file_id,
        file_unique_id=item.file_unique_id,
        file_name=item.file_name,
        mime=item.mime,
        source=item.source,
        doc_number=getattr(doc, "doc_number", ""),
        doc_date=getattr(doc, "doc_date", ""),
        items=getattr(doc, "items", []),
        totals=getattr(doc, "totals", {}),
        item_name=getattr(doc, "item_name", ""),
        incoming=getattr(doc, "incoming", ""),
        outgoing=getattr(doc, "outgoing", ""),
        balance=getattr(doc, "balance", ""),
        unit=getattr(doc, "unit", ""),
        supplier=getattr(doc, "supplier", ""),
        notes=getattr(doc, "notes", ""),
    )

    # 2. Automatic save to warehouse DB (items, transactions, completed status)
    warehouse_msg = ""
    if save_result.success:
        try:
            pending_dict = {
                "file_name": item.file_name,
                "ext": item.ext,
                "mime": item.mime,
            }
            warehouse_msg = _save_to_warehouse(
                ctx.warehouse_db,
                ctx.file_store,
                doc,
                pending_dict,
                save_result.doc_id,
                existing_doc_id=item.wh_doc_id,
            )
        except Exception as exc:
            logger.warning("Warehouse save failed: %s", exc)
            warehouse_msg = "⚠️ Помилка збереження в складську таблицю."

    # Remove card from pending since it's auto-saved
    ctx.queue_service.remove_card(pending_card.card_id)

    # 3. Edit live status message in Telegram
    card_text = format_card_text(doc, pending_card.card)
    final_text = f"✅ Документ #{item.wh_doc_id or save_result.doc_id} збережено в архів та склад!\n\n{card_text}"
    if warehouse_msg:
        final_text += f"\n\n{warehouse_msg}"

    if item.status_message_id is not None:
        try:
            await ctx.bot.edit_message_text(
                chat_id=item.chat_id,
                message_id=item.status_message_id,
                text=final_text,
            )
            return
        except Exception as exc:
            logger.debug("Failed to edit Telegram status message %s: %s", item.status_message_id, exc)

    try:
        await ctx.bot.send_message(
            chat_id=item.chat_id,
            text=final_text,
        )
    except Exception as exc:
        logger.error("Failed to send card message to chat %s: %s", item.chat_id, exc)


def register(router: Router, ctx: AppContext) -> None:
    """Put the card confirmation and rejection callbacks on ``router``."""

    @router.callback_query(F.data.startswith("confirm_save"))
    async def _save(callback: CallbackQuery):
        if ":" in callback.data:
            card_id = callback.data.split(":", 1)[1]
            card = ctx.queue_service.get_card(card_id)
        else:
            cards = ctx.queue_service.list_pending_cards(user_id=ctx.owner_user_id)
            card = cards[0] if cards else None
            card_id = card.card_id if card else ""

        if card is None:
            await callback.answer("Ця картка більше не активна (чергу очищено або документ вже оброблено).", show_alert=True)
            if callback.message:
                try:
                    await callback.message.edit_reply_markup(reply_markup=None)
                except Exception:
                    pass
            return

        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass

        ctx.queue_service.remove_card(card_id)
        doc = card.doc

        status_msg = None

        async def _on_save_status_update(status_text: str) -> None:
            nonlocal status_msg
            if callback.message:
                try:
                    if status_msg is None:
                        status_msg = await callback.message.answer(status_text)
                    else:
                        await status_msg.edit_text(status_text)
                except Exception as exc:
                    logger.debug("Failed to update save status message: %s", exc)

        save_result = await ctx.archive_service.save(
            title=doc.title,
            summary=doc.summary,
            key_value_pairs=doc.key_value_pairs,
            raw_text=doc.raw_text,
            tmp_path=card.item.tmp_path,
            ext=card.item.ext,
            user_id=card.item.user_id,
            telegram_file_id=card.item.file_id,
            file_unique_id=card.item.file_unique_id,
            file_name=card.item.file_name,
            mime=card.item.mime,
            source=card.item.source,
            doc_number=getattr(doc, "doc_number", ""),
            doc_date=getattr(doc, "doc_date", ""),
            items=getattr(doc, "items", []),
            totals=getattr(doc, "totals", {}),
            item_name=getattr(doc, "item_name", ""),
            incoming=getattr(doc, "incoming", ""),
            outgoing=getattr(doc, "outgoing", ""),
            balance=getattr(doc, "balance", ""),
            unit=getattr(doc, "unit", ""),
            supplier=getattr(doc, "supplier", ""),
            notes=getattr(doc, "notes", ""),
            on_status_update=_on_save_status_update,
        )

        warehouse_msg = ""
        if save_result.success:
            try:
                pending_dict = {
                    "file_name": card.item.file_name,
                    "ext": card.item.ext,
                    "mime": card.item.mime,
                }
                warehouse_msg = _save_to_warehouse(
                    ctx.warehouse_db, ctx.file_store, doc, pending_dict, save_result.doc_id,
                    existing_doc_id=card.item.wh_doc_id,
                )
            except Exception as exc:
                logger.warning("Warehouse save failed: %s", exc)
                warehouse_msg = "\n⚠️ Помилка збереження в складську таблицю."

        if save_result.success:
            text = f"Збережено (id: <code>{save_result.doc_id}</code>)."
            if save_result.disk_warning:
                text += "\n⚠️ Локальна копія не збережена, але документ в архіві."
            if warehouse_msg:
                text += "\n" + warehouse_msg
            if callback.message:
                if status_msg is not None:
                    try:
                        await status_msg.edit_text(text)
                    except Exception:
                        await callback.message.answer(text)
                else:
                    await callback.message.answer(text)
        else:
            if callback.message:
                err_text = f"Помилка збереження: {save_result.error}"
                if status_msg is not None:
                    try:
                        await status_msg.edit_text(err_text)
                    except Exception:
                        await callback.message.answer(err_text)
                else:
                    await callback.message.answer(err_text)
        await callback.answer()

    @router.callback_query(F.data.startswith("confirm_reject"))
    async def _reject(callback: CallbackQuery):
        if ":" in callback.data:
            card_id = callback.data.split(":", 1)[1]
            card = ctx.queue_service.get_card(card_id)
        else:
            cards = ctx.queue_service.list_pending_cards(user_id=ctx.owner_user_id)
            card = cards[0] if cards else None
            card_id = card.card_id if card else ""

        if card is None:
            await callback.answer("Ця картка більше не активна (чергу очищено або документ вже оброблено).", show_alert=True)
            if callback.message:
                try:
                    await callback.message.edit_reply_markup(reply_markup=None)
                except Exception:
                    pass
            return

        if callback.message:
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass

        ctx.queue_service.remove_card(card_id)
        if card.item.tmp_path and os.path.exists(card.item.tmp_path):
            try:
                ctx.file_store.delete_tmp(card.item.tmp_path)
            except Exception as exc:
                logger.warning("Failed to delete tmp file %s: %s", card.item.tmp_path, exc)

        if card.item.wh_doc_id is not None:
            try:
                ctx.warehouse_db.delete_document(card.item.wh_doc_id)
            except Exception as exc:
                logger.warning("Failed to drop queued document %s: %s", card.item.wh_doc_id, exc)

        if callback.message:
            await callback.message.answer("Відхилено — тимчасовий файл видалено.")
        await callback.answer()

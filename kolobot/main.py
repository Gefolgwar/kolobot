"""Process entrypoint: load config, wire bot, run polling."""

from __future__ import annotations

import asyncio
import html
import logging
import os
import re
import sys
import uuid
from typing import Any, Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ErrorEvent, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message

from kolobot.archive_service import ArchiveService
from kolobot.config import ConfigError, load_config
from kolobot.doc_structurer import CardViewModel, DocStructurer, Document, normalize_doc_type
from kolobot.file_store import FileStore
from kolobot.gemini_gateway import GeminiError, GeminiGateway
from kolobot.handlers.commands import cmd_clear, cmd_status, router as commands_router
from kolobot.handlers.list_delete import ListDeleteHandler
from kolobot.handlers.media import MediaHandler, _ext_from_mime
from kolobot.intake_service import DocumentIntakeService
from kolobot.key_pool import KeyPool, PoolKind
from kolobot.log_service import setup_logging_capture
from kolobot.messages import ACCESS_DENIED_UK
from kolobot.middlewares.access import AccessMiddleware
from kolobot.queue_service import DocumentQueueService, PendingCard, QueueItem
from kolobot.rag_service import RagService
from kolobot.vector_store import VectorStore
from kolobot.warehouse_db import WarehouseDB

logger = logging.getLogger(__name__)


def h(text: Any) -> str:
    if not text:
        return ""
    return html.escape(str(text))


def format_card_text(doc: Document, card: CardViewModel) -> str:
    """Format a structured document and its card view model into HTML text for Telegram."""
    lines = [
        f"<b>{h(card.doc_type).upper()}</b>: {h(card.title)}",
    ]

    if card.doc_number or card.doc_date:
        meta_str = []
        if card.doc_number:
            meta_str.append(f"№ {h(card.doc_number)}")
        if card.doc_date:
            meta_str.append(f"від {h(card.doc_date)}")
        lines.append("<b>Документ:</b> " + " ".join(meta_str))

    if card.summary:
        lines.append(f"\n<b>Опис:</b> {h(card.summary)}")

    if card.key_value_pairs:
        lines.append("\n<b>Основні реквізити:</b>")
        for kv in card.key_value_pairs:
            lines.append(f"• <b>{h(kv['key'])}</b>: {h(kv['value'])}")

    if card.items:
        lines.append("\n<b>Повний перелік товарів / послуг:</b>")
        for it in card.items:
            num = h(it.get("num", ""))
            name = h(it.get("name", ""))
            qty = h(it.get("quantity", ""))
            unit = h(it.get("unit", ""))
            price = h(it.get("price_no_vat", ""))
            total_val = h(it.get("total_no_vat", ""))
            details = []
            if qty or unit:
                details.append(f"{qty} {unit}".strip())
            if price:
                details.append(f"ціна: {price}")
            if total_val:
                details.append(f"сума: {total_val}")
            det_str = f" ({', '.join(details)})" if details else ""
            num_str = f"{num}. " if num else "• "
            lines.append(f"  {num_str}<b>{name}</b>{det_str}")

    if card.totals:
        tot_parts = []
        if card.totals.get("total_no_vat"):
            tot_parts.append(f"Без ПДВ: {h(card.totals['total_no_vat'])}")
        if card.totals.get("vat"):
            tot_parts.append(f"ПДВ: {h(card.totals['vat'])}")
        if card.totals.get("total_with_vat"):
            tot_parts.append(f"Всього з ПДВ: {h(card.totals['total_with_vat'])}")
        if tot_parts:
            lines.append("\n<b>Підсумкові суми:</b>\n" + "\n".join(f"• {p}" for p in tot_parts))

    if getattr(doc, "raw_text", None):
        lines.append(f"\n<b>Повний розпізнаний текст:</b>\n<i>{h(doc.raw_text)}</i>")

    full_text = "\n".join(line for line in lines if line)
    if len(full_text) > 4000:
        full_text = full_text[:3950] + "\n\n<i>... [текст скорочено через ліміт Telegram (4000 символів)]</i>"

    return full_text


def make_card_keyboard(card_id: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for a specific pending card."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Зберегти", callback_data=f"confirm_save:{card_id}"),
        InlineKeyboardButton(text="Відхилити", callback_data=f"confirm_reject:{card_id}"),
    ]])


async def send_archive_file(
    message: Message,
    file_store: FileStore,
    doc_id: str,
    metadata: dict[str, Any],
    error_text: str = "Не вдалося надіслати файл.",
) -> bool:
    """
    Send an archived document or photo to Telegram.
    Tries telegram_file_id first (answer_photo for photos, answer_document for documents).
    Falls back to local storage using FSInputFile if file_id is invalid, expired, or missing.
    Reports failure only if both methods fail.
    """
    fid = metadata.get("telegram_file_id") or ""
    source = metadata.get("source") or ""
    mime = metadata.get("mime") or ""

    if fid:
        try:
            if source == "photo":
                await message.answer_photo(fid)
            else:
                await message.answer_document(fid)
            return True
        except Exception as exc:
            logger.warning("Failed to send via telegram_file_id=%s: %s", fid, exc)

    ext = _ext_from_mime(mime)
    file_path = file_store.get_final_path(doc_id, ext)
    if not file_path:
        for candidate in (".jpg", ".png", ".webp"):
            if candidate != ext:
                file_path = file_store.get_final_path(doc_id, candidate)
                if file_path:
                    break

    if file_path:
        try:
            input_file = FSInputFile(file_path)
            if source == "photo":
                await message.answer_photo(input_file)
            else:
                await message.answer_document(input_file)
            return True
        except Exception as exc:
            logger.warning("Failed to send local file %s via FSInputFile: %s", file_path, exc)

    await message.answer(error_text)
    return False


def _sync_chroma_with_warehouse(
    vs: "VectorStore",
    wdb: WarehouseDB,
    fs: FileStore,
    owner_user_id: int,
) -> None:
    chroma_ids = vs.list_all_ids(owner_user_id)
    if not chroma_ids:
        return

    wh_docs = wdb.get_documents()
    known_chroma_ids = set()
    for doc in wh_docs:
        fp = doc.get("file_path", "")
        if fp:
            stem = os.path.splitext(os.path.basename(fp))[0]
            if len(stem) == 10:
                known_chroma_ids.add(stem)

    orphans = [cid for cid in chroma_ids if cid not in known_chroma_ids]
    for cid in orphans:
        vs.delete(cid)
        for ext in (".jpg", ".png", ".webp", ".pdf"):
            fs.delete_final(cid, ext=ext)
    if orphans:
        logger.info("Startup sync: removed %d orphaned ChromaDB records.", len(orphans))


def _detect_doc_type_and_op(doc: Any) -> tuple[str, str]:
    """
    Returns (doc_type_label, default_op).
    doc_type_label: 'ВИМОГА', 'НАКЛАДНА', or custom uppercase string.
    default_op: 'expense', 'income', or ''.
    """
    raw_doc_type = (getattr(doc, "doc_type", "") or "").strip().lower()
    title = (getattr(doc, "title", "") or "").strip().lower()
    summary = (getattr(doc, "summary", "") or "").strip().lower()
    raw_text = (getattr(doc, "raw_text", "") or "").strip().lower()
    header_lines = "\n".join(raw_text.splitlines()[:5])

    # Priority 1: Check header lines of raw text for clear printed document title
    if re.search(r"\bвимога\b", header_lines) or re.search(r"\bакт\s+списанн", header_lines):
        return "ВИМОГА", "expense"
    if (
        re.search(r"\bнакладна\b", header_lines)
        or re.search(r"\bприбутков", header_lines)
        or re.search(r"\bвидатков", header_lines)
        or re.search(r"\bтоварна\b", header_lines)
        or re.search(r"\bттн\b", header_lines)
    ):
        return "НАКЛАДНА", "income"

    # Priority 2: Check explicit title
    if "вимога" in title or "списанн" in title:
        return "ВИМОГА", "expense"
    if (
        "накладна" in title
        or "прибутков" in title
        or "видатков" in title
        or "товарна" in title
        or "ттн" in title
    ):
        return "НАКЛАДНА", "income"

    # Priority 3: Check summary
    if "вимога" in summary or "списанн" in summary:
        return "ВИМОГА", "expense"
    if "накладна" in summary or "прибутков" in summary or "видатков" in summary:
        return "НАКЛАДНА", "income"

    # Priority 4: Direct match if doc_type was already set/normalized
    if raw_doc_type == "вимога":
        return "ВИМОГА", "expense"
    if raw_doc_type == "накладна":
        return "НАКЛАДНА", "income"
    if "вимога" in raw_doc_type or "списанн" in raw_doc_type:
        return "ВИМОГА", "expense"
    if "накладна" in raw_doc_type or "прибутков" in raw_doc_type or "видатков" in raw_doc_type:
        return "НАКЛАДНА", "income"

    # Priority 5: Full raw text search
    if (
        re.search(r"\bвимога\s*№", raw_text)
        or re.search(r"\bвимога-накладна", raw_text)
        or re.search(r"\bакт\s+списанн", raw_text)
    ):
        return "ВИМОГА", "expense"
    if (
        re.search(r"\bнакладна\s*№", raw_text)
        or re.search(r"\bприбуткова\s+накладна", raw_text)
        or re.search(r"\bвидаткова\s+накладна", raw_text)
    ):
        return "НАКЛАДНА", "income"

    return raw_doc_type.upper() if raw_doc_type else "", ""


def _save_to_warehouse(
    wdb: WarehouseDB,
    fs: FileStore,
    doc: Any,
    pending: dict,
    archive_doc_id: str,
    existing_doc_id: Optional[int] = None,
) -> str:
    file_name = pending.get("file_name") or f"{archive_doc_id}{pending.get('ext', '.jpg')}"
    mime = pending.get("mime", "image/jpeg")
    ext = pending.get("ext", ".jpg")

    file_path = fs.get_final_path(archive_doc_id, ext=ext) or ""
    raw_text = getattr(doc, "raw_text", "")
    if archive_doc_id and raw_text:
        try:
            fs.save_text(archive_doc_id, raw_text)
        except Exception:
            pass

    doc_type_label, default_op = _detect_doc_type_and_op(doc)
    file_type = "photo" if mime.startswith("image") else "pdf"

    if existing_doc_id is not None:
        wdb.update_document(
            existing_doc_id,
            filename=file_name,
            file_type=file_type,
            file_path=file_path,
            doc_number=getattr(doc, "doc_number", ""),
            doc_date=getattr(doc, "doc_date", ""),
            raw_text=raw_text,
            doc_type=doc_type_label,
            status="completed",
            error_message="",
        )
        wh_doc_id = existing_doc_id
    else:
        wh_doc_id = wdb.add_document(
            filename=file_name,
            file_type=file_type,
            file_path=file_path,
            doc_number=getattr(doc, "doc_number", ""),
            doc_date=getattr(doc, "doc_date", ""),
            raw_text=raw_text,
            doc_type=doc_type_label,
        )

    items_list = getattr(doc, "items", []) or []
    created = 0
    updated = 0
    txs = 0

    if items_list:
        for it in items_list:
            name = it.get("name", "").strip()
            if not name:
                continue
            sku = str(it.get("nomenclature_number", "") or "").strip()
            existing = wdb.find_item(sku=sku, name=name)
            if existing:
                item_id = existing["id"]
                updated += 1
                wdb.update_item(item_id, sku=sku, unit=it.get("unit", ""))
            else:
                item_id = wdb.add_item(
                    name=name, sku=sku,
                    unit=it.get("unit", ""),
                )
                created += 1

            qty_str = str(it.get("quantity", "") or "").strip().replace(" ", "")
            try:
                qty = float(qty_str) if qty_str else 0
            except ValueError:
                qty = 0

            if qty > 0:
                if default_op:
                    op_type = default_op
                else:
                    incoming_val = getattr(doc, "incoming", "")
                    outgoing_val = getattr(doc, "outgoing", "")
                    if outgoing_val and str(outgoing_val).strip():
                        op_type = "expense"
                    elif incoming_val and str(incoming_val).strip():
                        op_type = "income"
                    else:
                        op_type = "income"

                num_str = str(it.get("num", "") or "").strip()
                unit_str = str(it.get("unit", "") or "").strip()
                src_parts = []
                if num_str:
                    src_parts.append(f"Поз. {num_str}")
                if sku:
                    src_parts.append(sku)
                src_parts.append(name)
                if unit_str:
                    src_parts.append(unit_str)
                source_row = " | ".join(src_parts)

                wdb.add_transaction(
                    item_id=item_id, document_id=wh_doc_id,
                    operation_type=op_type, quantity=qty,
                    doc_number=getattr(doc, "doc_number", ""),
                    doc_date=getattr(doc, "doc_date", ""),
                    source_row=source_row,
                )
                txs += 1

    elif getattr(doc, "item_name", ""):
        name = doc.item_name.strip()
        sku = str(getattr(doc, "nomenclature_number", "") or "").strip()
        existing = wdb.find_item(sku=sku, name=name)
        if existing:
            item_id = existing["id"]
            updated += 1
        else:
            item_id = wdb.add_item(
                name=name, sku=sku,
                unit=getattr(doc, "unit", ""),
                supplier=getattr(doc, "supplier", ""),
                notes=getattr(doc, "notes", ""),
            )
            created += 1

        incoming_val = str(getattr(doc, "incoming", "") or "").strip().replace(" ", "")
        outgoing_val = str(getattr(doc, "outgoing", "") or "").strip().replace(" ", "")

        try:
            inc_qty = float(incoming_val) if incoming_val else 0
        except ValueError:
            inc_qty = 0
        try:
            exp_qty = float(outgoing_val) if outgoing_val else 0
        except ValueError:
            exp_qty = 0

        source_row = f"{sku} | {name}" if sku else name
        if default_op:
            total_qty = inc_qty + exp_qty
            if total_qty > 0:
                wdb.add_transaction(
                    item_id=item_id, document_id=wh_doc_id,
                    operation_type=default_op, quantity=total_qty,
                    doc_number=getattr(doc, "doc_number", ""),
                    doc_date=getattr(doc, "doc_date", ""),
                    source_row=source_row,
                )
                txs += 1
        else:
            if inc_qty > 0:
                wdb.add_transaction(
                    item_id=item_id, document_id=wh_doc_id,
                    operation_type="income", quantity=inc_qty,
                    doc_number=getattr(doc, "doc_number", ""),
                    doc_date=getattr(doc, "doc_date", ""),
                    source_row=source_row,
                )
                txs += 1
            if exp_qty > 0:
                wdb.add_transaction(
                    item_id=item_id, document_id=wh_doc_id,
                    operation_type="expense", quantity=exp_qty,
                    doc_number=getattr(doc, "doc_number", ""),
                    doc_date=getattr(doc, "doc_date", ""),
                    source_row=source_row,
                )
                txs += 1

    parts = []
    if created:
        parts.append(f"{created} нових позицій")
    if updated:
        parts.append(f"{updated} оновлено")
    if txs:
        parts.append(f"{txs} транзакцій")
    if parts:
        return "📦 Склад: " + ", ".join(parts) + "."
    return ""


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

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    async def _on_card_ready(pending_card: PendingCard) -> None:
        full_text = format_card_text(pending_card.doc, pending_card.card)
        kb = make_card_keyboard(pending_card.card_id)

        if pending_card.item.status_message_id is not None:
            try:
                await bot.edit_message_text(
                    chat_id=pending_card.item.chat_id,
                    message_id=pending_card.item.status_message_id,
                    text=full_text,
                    reply_markup=kb,
                )
                return
            except Exception as exc:
                logger.debug("Failed to edit Telegram status message %s: %s", pending_card.item.status_message_id, exc)

        try:
            await bot.send_message(
                chat_id=pending_card.item.chat_id,
                text=full_text,
                reply_markup=kb,
            )
        except Exception as exc:
            logger.error("Failed to send card message to chat %s: %s", pending_card.item.chat_id, exc)

    queue_service = DocumentQueueService(
        gateway=gateway,
        doc_structurer=doc_structurer,
        file_store=file_store,
        bot=bot,
        on_card_ready=_on_card_ready,
    )

    intake_service = DocumentIntakeService(
        file_store=file_store,
        warehouse_db=warehouse_db,
    )

    dedup_pending: dict[str, dict] = {}

    # --- Router wiring ---
    rt = Router(name="app")

    @rt.message(Command("status"))
    async def _status(message: Message):
        await cmd_status(
            message,
            gen_pool=gen_pool,
            emb_pool=emb_pool,
            queue_service=queue_service,
        )

    @rt.message(Command("list"))
    async def _list(message: Message):
        await list_delete.handle_list(message, user_id=settings.owner_user_id)

    @rt.message(Command("delete"))
    async def _delete(message: Message):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Використання: /delete <id>")
            return
        result = await list_delete.delete_doc(
            doc_id=parts[1].strip(), user_id=settings.owner_user_id
        )
        if result.success:
            await message.answer("Документ видалено.")
        else:
            await message.answer(result.error or "Помилка видалення.")

    @rt.message(Command("clear"))
    async def _clear(message: Message):
        await cmd_clear(message, queue_service=queue_service)

    @rt.message(F.photo | F.document)
    async def _media(message: Message):
        intake = await media_handler.handle_media(message)
        if intake is None:
            return

        # Dedup check
        existing = archive_svc.lookup_duplicate(
            user_id=settings.owner_user_id,
            file_unique_id=intake["file_unique_id"],
        )
        if existing is not None:
            dedup_id = uuid.uuid4().hex[:8]
            dedup_pending[dedup_id] = intake
            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Відкрити старий", callback_data=f"dedup_open:{existing['id']}"),
                InlineKeyboardButton(text="Все одно зберегти", callback_data=f"dedup_force:{dedup_id}"),
            ]])
            await message.answer("Цей файл вже є в архіві.", reply_markup=kb)
            return

        # Unsaved cards reminder
        pending_count = queue_service.get_pending_card_count(user_id=settings.owner_user_id)
        if pending_count > 0:
            await message.answer(f"ℹ️ Зверни увагу: у тебе є {pending_count} незбережених карток на підтвердження.")

        intake_result = await intake_service.accept(intake, message.bot)

        status_msg = await message.answer(intake_result.message)
        status_id = getattr(status_msg, "message_id", None)

        item = QueueItem(
            file_id=intake["file_id"],
            file_unique_id=intake["file_unique_id"],
            mime=intake["mime"],
            file_size=intake["file_size"],
            tmp_path=intake_result.file_path,
            chat_id=message.chat.id,
            user_id=message.from_user.id if message.from_user else settings.owner_user_id,
            status_message_id=status_id,
            source=intake["source"],
            file_name=intake.get("file_name"),
            ext=intake.get("ext", ".jpg"),
            wh_doc_id=intake_result.doc_id,
        )
        await queue_service.enqueue(item)

    @rt.callback_query(F.data.startswith("confirm_save"))
    async def _save(callback: CallbackQuery):
        if ":" in callback.data:
            card_id = callback.data.split(":", 1)[1]
            card = queue_service.get_card(card_id)
        else:
            cards = queue_service.list_pending_cards(user_id=settings.owner_user_id)
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

        queue_service.remove_card(card_id)
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

        save_result = await archive_svc.save(
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
                    warehouse_db, file_store, doc, pending_dict, save_result.doc_id,
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

    @rt.callback_query(F.data.startswith("confirm_reject"))
    async def _reject(callback: CallbackQuery):
        if ":" in callback.data:
            card_id = callback.data.split(":", 1)[1]
            card = queue_service.get_card(card_id)
        else:
            cards = queue_service.list_pending_cards(user_id=settings.owner_user_id)
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

        queue_service.remove_card(card_id)
        if card.item.tmp_path and os.path.exists(card.item.tmp_path):
            try:
                file_store.delete_tmp(card.item.tmp_path)
            except Exception as exc:
                logger.warning("Failed to delete tmp file %s: %s", card.item.tmp_path, exc)

        if card.item.wh_doc_id is not None:
            try:
                warehouse_db.delete_document(card.item.wh_doc_id)
            except Exception as exc:
                logger.warning("Failed to drop queued document %s: %s", card.item.wh_doc_id, exc)

        if callback.message:
            await callback.message.answer("Відхилено — тимчасовий файл видалено.")
        await callback.answer()

    @rt.callback_query(F.data.startswith("dedup_open:"))
    async def _dedup_open(callback: CallbackQuery):
        doc_id = callback.data.split(":", 1)[1]
        doc = vector_store.get(doc_id)
        meta = doc.get("metadata", {}) if doc else {}
        if meta and callback.message:
            await send_archive_file(
                message=callback.message,
                file_store=file_store,
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

    @rt.callback_query(F.data.startswith("dedup_force"))
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
            pending_count = queue_service.get_pending_card_count(user_id=settings.owner_user_id)
            if pending_count > 0:
                await callback.message.answer(f"ℹ️ Зверни увагу: у тебе є {pending_count} незбережених карток на підтвердження.")

            intake_result = await intake_service.accept(intake, callback.message.bot)

            status_msg = await callback.message.answer(intake_result.message)
            status_id = getattr(status_msg, "message_id", None)

            item = QueueItem(
                file_id=intake["file_id"],
                file_unique_id=intake["file_unique_id"],
                mime=intake["mime"],
                file_size=intake["file_size"],
                tmp_path=intake_result.file_path,
                chat_id=callback.message.chat.id,
                user_id=callback.from_user.id if callback.from_user else settings.owner_user_id,
                status_message_id=status_id,
                source=intake["source"],
                file_name=intake.get("file_name"),
                ext=intake.get("ext", ".jpg"),
                wh_doc_id=intake_result.doc_id,
            )
            await queue_service.enqueue(item)

        await callback.answer()

    @rt.callback_query(F.data.startswith("file:"))
    async def _send_file(callback: CallbackQuery):
        doc_id = callback.data.split(":", 1)[1]
        doc = vector_store.get(doc_id)
        if doc and callback.message:
            await send_archive_file(
                message=callback.message,
                file_store=file_store,
                doc_id=doc_id,
                metadata=doc.get("metadata", {}),
                error_text="Не вдалося надіслати файл.",
            )
        elif callback.message:
            await callback.message.answer("Не вдалося надіслати файл.")
        await callback.answer()

    @rt.callback_query(F.data.startswith("del_yes:"))
    async def _del_confirm(callback: CallbackQuery):
        doc_id = callback.data.split(":", 1)[1]
        result = await list_delete.delete_doc(
            doc_id=doc_id, user_id=settings.owner_user_id
        )
        if callback.message:
            if result.success:
                await callback.message.answer("Видалено.")
            else:
                await callback.message.answer(result.error or "Помилка.")
        await callback.answer()

    @rt.callback_query(F.data == "del_no")
    async def _del_cancel(callback: CallbackQuery):
        if callback.message:
            await callback.message.answer("Скасовано.")
        await callback.answer()

    @rt.message(~Command("start", "help", "status", "list", "delete", "clear"))
    async def _text(message: Message):
        if message.photo or message.document:
            return
        text = (message.text or "").strip()
        if not text:
            return
        rag_result = await rag_svc.answer(
            user_id=settings.owner_user_id, question=text
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

    # --- Build dispatcher ---
    dp = Dispatcher()
    dp["queue_service"] = queue_service
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

"""Process entrypoint: load config, wire bot, run polling."""

from __future__ import annotations

import asyncio
import html
import logging
import os
import sys
from dataclasses import replace
from typing import Any

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, ErrorEvent, FSInputFile, Message

from kolobot.archive_service import ArchiveService
from kolobot.config import ConfigError, load_config
from kolobot.doc_structurer import DocStructurer, ParseStatus
from kolobot.file_store import FileStore
from kolobot.gemini_gateway import GeminiError, GeminiGateway, NvidiaClient
from kolobot.handlers.commands import cmd_status, router as commands_router
from kolobot.handlers.list_delete import ListDeleteHandler
from kolobot.handlers.media import MediaHandler, _ext_from_mime
from kolobot.hardening import ConfirmTimeoutChecker, QuotaHandler
from kolobot.key_pool import KeyPool, PoolKind
from kolobot.messages import ACCESS_DENIED_UK
from kolobot.middlewares.access import AccessMiddleware
from kolobot.rag_service import RagService
from kolobot.vector_store import VectorStore
from kolobot.warehouse_db import WarehouseDB

logger = logging.getLogger(__name__)


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


def h(text: Any) -> str:
    if not text:
        return ""
    return html.escape(str(text))


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


def _save_to_warehouse(
    wdb: WarehouseDB,
    fs: FileStore,
    doc: Any,
    pending: dict,
    archive_doc_id: str,
) -> str:
    file_name = pending.get("file_name") or f"{archive_doc_id}{pending.get('ext', '.jpg')}"
    mime = pending.get("mime", "image/jpeg")
    ext = pending.get("ext", ".jpg")

    file_path = fs.get_final_path(archive_doc_id, ext=ext) or ""

    raw_doc_type = (getattr(doc, "doc_type", "") or "").strip().lower()
    raw_text_lower = (getattr(doc, "raw_text", "") or "").lower()
    if "накладна" in raw_doc_type or raw_doc_type == "invoice" or "накладна" in raw_text_lower:
        doc_type_label = "НАКЛАДНА"
        default_op = "income"
    elif "вимога" in raw_doc_type or "вимога" in raw_text_lower:
        doc_type_label = "ВИМОГА"
        default_op = "expense"
    else:
        doc_type_label = raw_doc_type.upper() if raw_doc_type else ""
        default_op = ""

    wh_doc_id = wdb.add_document(
        filename=file_name,
        file_type="photo" if mime.startswith("image") else "pdf",
        file_path=file_path,
        doc_number=getattr(doc, "doc_number", ""),
        doc_date=getattr(doc, "doc_date", ""),
        raw_text=getattr(doc, "raw_text", ""),
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

                wdb.add_transaction(
                    item_id=item_id, document_id=wh_doc_id,
                    operation_type=op_type, quantity=qty,
                    doc_number=getattr(doc, "doc_number", ""),
                    doc_date=getattr(doc, "doc_date", ""),
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

        if default_op:
            total_qty = inc_qty + exp_qty
            if total_qty > 0:
                wdb.add_transaction(
                    item_id=item_id, document_id=wh_doc_id,
                    operation_type=default_op, quantity=total_qty,
                    doc_number=getattr(doc, "doc_number", ""),
                    doc_date=getattr(doc, "doc_date", ""),
                )
                txs += 1
        else:
            if inc_qty > 0:
                wdb.add_transaction(
                    item_id=item_id, document_id=wh_doc_id,
                    operation_type="income", quantity=inc_qty,
                    doc_number=getattr(doc, "doc_number", ""),
                    doc_date=getattr(doc, "doc_date", ""),
                )
                txs += 1
            if exp_qty > 0:
                wdb.add_transaction(
                    item_id=item_id, document_id=wh_doc_id,
                    operation_type="expense", quantity=exp_qty,
                    doc_number=getattr(doc, "doc_number", ""),
                    doc_date=getattr(doc, "doc_date", ""),
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


def build_app(use_qwen3_vl: bool = False, use_gmodel: bool = False):
    """Construct all deep modules and wire together. Returns (dp, bot, settings)."""
    settings = load_config()
    if use_qwen3_vl:
        settings = replace(settings, use_qwen3_vl=True)
    if use_gmodel:
        settings = replace(settings, use_gmodel=True)

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

    if settings.ai_provider == "nvidia":
        if settings.nvidia_api_key:
            gen_pool = KeyPool(
                keys=[settings.nvidia_api_key],
                kind=PoolKind.GENERATE,
                rpm_limit=settings.rpm_limit,
                rpd_limit=settings.rpd_limit,
                cooldown_sec=settings.cooldown_sec,
            )
            emb_pool = KeyPool(
                keys=[settings.nvidia_api_key],
                kind=PoolKind.EMBED,
                rpm_limit=settings.rpm_limit,
                rpd_limit=settings.rpd_limit,
                cooldown_sec=settings.cooldown_sec,
            )
        client = NvidiaClient()
        gateway = GeminiGateway(
            gen_pool=gen_pool,
            emb_pool=emb_pool,
            client=client,
            generate_model=settings.nvidia_generate_model,
            embed_model=settings.nvidia_embed_model,
            use_qwen3_vl=settings.use_qwen3_vl,
            use_gmodel=settings.use_gmodel,
        )
    else:
        gateway = GeminiGateway(
            gen_pool=gen_pool,
            emb_pool=emb_pool,
            generate_model=settings.generate_model,
            embed_model=settings.embed_model,
            use_qwen3_vl=settings.use_qwen3_vl,
            use_gmodel=settings.use_gmodel,
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
    media_handler = MediaHandler(
        file_store=file_store, owner_user_id=settings.owner_user_id
    )
    list_delete = ListDeleteHandler(
        vector_store=vector_store,
        file_store=file_store,
        owner_user_id=settings.owner_user_id,
    )
    timeout_checker = ConfirmTimeoutChecker(timeout_sec=settings.confirm_timeout_sec)
    quota_handler = QuotaHandler()

    # Pending OCR state (single-flight)
    pending_doc = {}

    # --- Router wiring ---
    rt = Router(name="app")

    @rt.message(Command("status"))
    async def _status(message: Message):
        await cmd_status(message, gen_pool=gen_pool, emb_pool=emb_pool)

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

    @rt.message(F.photo | F.document)
    async def _media(message: Message):
        # Check confirm timeout
        if timeout_checker.is_expired():
            timeout_checker.clear()
            media_handler.clear_pending()
            if pending_doc.get("tmp_path"):
                file_store.delete_tmp(pending_doc["tmp_path"])
            pending_doc.clear()
            await message.answer("Попереднє підтвердження протерміноване — можеш надіслати нове зображення.")

        intake = await media_handler.handle_media(message)
        if intake is None:
            return

        # Dedup check
        existing = archive_svc.lookup_duplicate(
            user_id=settings.owner_user_id,
            file_unique_id=intake["file_unique_id"],
        )
        if existing is not None:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

            kb = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Відкрити старий", callback_data=f"dedup_open:{existing['id']}"),
                InlineKeyboardButton(text="Все одно зберегти", callback_data="dedup_force"),
            ]])
            media_handler.clear_pending()
            pending_doc.update(intake)
            pending_doc["dedup_existing"] = existing
            await message.answer("Цей файл вже є в архіві.", reply_markup=kb)
            return

        await _run_ocr(message, intake)

    async def _run_ocr(message: Message, intake: dict):
        await message.answer("Розпізнаю…")

        try:
            raw_io = await message.bot.download(intake["file_id"])
            image_bytes = raw_io.read() if hasattr(raw_io, "read") else raw_io
        except Exception:
            await message.answer("Помилка завантаження файлу.")
            media_handler.clear_pending()
            return

        # Save actual bytes to tmp
        import os
        tmp_path = intake["tmp_path"]
        with open(tmp_path, "wb") as f:
            f.write(image_bytes)

        quota_result = await quota_handler.with_retry(
            fn=lambda: gateway.extract_document(image_bytes, intake["mime"], tmp_path),
            max_wait=5.0,
        )
        if quota_result.exhausted:
            await message.answer(quota_result.message)
            media_handler.clear_pending()
            file_store.delete_tmp(tmp_path)
            return

        model_text = quota_result.value
        result = doc_structurer.parse(model_text)

        if result.status == ParseStatus.NEEDS_RETRY:
            quota_result2 = await quota_handler.with_retry(
                fn=lambda: gateway.extract_document(image_bytes, intake["mime"], tmp_path),
                max_wait=5.0,
            )
            if quota_result2.exhausted:
                await message.answer(quota_result2.message)
                media_handler.clear_pending()
                file_store.delete_tmp(tmp_path)
                return
            result = doc_structurer.parse(quota_result2.value, is_retry=True)

        if result.doc is None or result.doc.is_empty:
            await message.answer(
                "Не вдалося розпізнати текст. Спробуй надіслати чіткіше зображення."
            )
            media_handler.clear_pending()
            file_store.delete_tmp(tmp_path)
            return

        card = doc_structurer.to_card(result.doc)
        timeout_checker.mark_pending()
        pending_doc.update(intake)
        pending_doc["doc"] = result.doc

        doc = result.doc
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

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Зберегти", callback_data="confirm_save"),
            InlineKeyboardButton(text="Відхилити", callback_data="confirm_reject"),
        ]])
        await message.answer(full_text, reply_markup=kb)

    @rt.callback_query(F.data == "confirm_save")
    async def _save(callback: CallbackQuery):
        doc = pending_doc.get("doc")
        if doc is None:
            await callback.answer("Немає активного підтвердження.")
            return

        save_result = await archive_svc.save(
            title=doc.title,
            summary=doc.summary,
            key_value_pairs=doc.key_value_pairs,
            raw_text=doc.raw_text,
            tmp_path=pending_doc.get("tmp_path", ""),
            ext=pending_doc.get("ext", ".jpg"),
            user_id=settings.owner_user_id,
            telegram_file_id=pending_doc.get("file_id", ""),
            file_unique_id=pending_doc.get("file_unique_id", ""),
            file_name=pending_doc.get("file_name"),
            mime=pending_doc.get("mime", "image/jpeg"),
            source=pending_doc.get("source", "photo"),
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

        warehouse_msg = ""
        if save_result.success:
            try:
                warehouse_msg = _save_to_warehouse(
                    warehouse_db, file_store, doc, pending_doc, save_result.doc_id
                )
            except Exception as exc:
                logger.warning("Warehouse save failed: %s", exc)
                warehouse_msg = "\n⚠️ Помилка збереження в складську таблицю."

        media_handler.clear_pending()
        timeout_checker.clear()
        pending_doc.clear()

        if save_result.success:
            text = f"Збережено (id: <code>{save_result.doc_id}</code>)."
            if save_result.disk_warning:
                text += "\n⚠️ Локальна копія не збережена, але документ в архіві."
            if warehouse_msg:
                text += "\n" + warehouse_msg
            await callback.message.answer(text)
        else:
            await callback.message.answer(
                f"Помилка збереження: {save_result.error}"
            )
        await callback.answer()

    @rt.callback_query(F.data == "confirm_reject")
    async def _reject(callback: CallbackQuery):
        tmp = pending_doc.get("tmp_path")
        if tmp:
            file_store.delete_tmp(tmp)
        media_handler.clear_pending()
        timeout_checker.clear()
        pending_doc.clear()
        await callback.message.answer("Відхилено — тимчасовий файл видалено.")
        await callback.answer()

    @rt.callback_query(F.data.startswith("dedup_open:"))
    async def _dedup_open(callback: CallbackQuery):
        doc_id = callback.data.split(":", 1)[1]
        existing = pending_doc.get("dedup_existing")
        meta = existing.get("metadata", {}) if existing else {}
        if not meta:
            doc = vector_store.get(doc_id)
            if doc:
                meta = doc.get("metadata", {})
        if meta:
            await send_archive_file(
                message=callback.message,
                file_store=file_store,
                doc_id=doc_id,
                metadata=meta,
                error_text="Не вдалося надіслати оригінал.",
            )
        else:
            await callback.message.answer("Не вдалося надіслати оригінал.")
        pending_doc.clear()
        await callback.answer()

    @rt.callback_query(F.data == "dedup_force")
    async def _dedup_force(callback: CallbackQuery):
        intake = {k: v for k, v in pending_doc.items() if k != "dedup_existing"}
        pending_doc.clear()
        media_handler._pending = True
        await callback.answer()
        await _run_ocr(callback.message, intake)

    @rt.callback_query(F.data.startswith("file:"))
    async def _send_file(callback: CallbackQuery):
        doc_id = callback.data.split(":", 1)[1]
        doc = vector_store.get(doc_id)
        if doc:
            await send_archive_file(
                message=callback.message,
                file_store=file_store,
                doc_id=doc_id,
                metadata=doc.get("metadata", {}),
                error_text="Не вдалося надіслати файл.",
            )
        else:
            await callback.message.answer("Не вдалося надіслати файл.")
        await callback.answer()

    @rt.callback_query(F.data.startswith("del_yes:"))
    async def _del_confirm(callback: CallbackQuery):
        doc_id = callback.data.split(":", 1)[1]
        result = await list_delete.delete_doc(
            doc_id=doc_id, user_id=settings.owner_user_id
        )
        if result.success:
            await callback.message.answer("Видалено.")
        else:
            await callback.message.answer(result.error or "Помилка.")
        await callback.answer()

    @rt.callback_query(F.data == "del_no")
    async def _del_cancel(callback: CallbackQuery):
        await callback.message.answer("Скасовано.")
        await callback.answer()

    @rt.message(~Command("start", "help", "status", "list", "delete"))
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

        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
    access = AccessMiddleware(owner_user_id=settings.owner_user_id)
    dp.message.middleware(access)
    dp.callback_query.middleware(access)
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

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

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


async def run(use_qwen3_vl: bool = False, use_gmodel: bool = False) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        dp, bot, settings = build_app(use_qwen3_vl=use_qwen3_vl, use_gmodel=use_gmodel)
    except ConfigError as exc:
        logger.error("Config error: %s", exc)
        raise SystemExit(2) from exc

    web_server = dp.workflow_data.get("web_server")
    if web_server:
        await web_server.start()

    ocr_name = "gmodel" if settings.use_gmodel else ("qwen3-vl" if settings.use_qwen3_vl else "unlimited-ocr")
    logger.info("kolobot starting for owner_user_id=%s, ocr=%s",
                settings.owner_user_id, ocr_name)
    try:
        await dp.start_polling(bot)
    finally:
        if web_server:
            await web_server.stop()


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="kolobot")
    parser.add_argument("--qwen3-vl", action="store_true", default=False,
                        help="Use Qwen3-VL-2B instead of Unlimited-OCR for text recognition")
    parser.add_argument("--gmodel", action="store_true", default=False,
                        help="Use Gemini API for OCR instead of local models")
    args = parser.parse_args()
    try:
        asyncio.run(run(use_qwen3_vl=args.qwen3_vl, use_gmodel=args.gmodel))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()

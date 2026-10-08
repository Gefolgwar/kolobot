"""Writing a recognised document into the warehouse: items, transactions, status.

The warehouse half of the ingestion path, and nothing else - no bot, no
Telegram types, no network. ``_detect_doc_type_and_op`` classifies a
recognised document as a requirement or a waybill from its header, title,
summary or full text, and ``_save_to_warehouse`` persists it, its
nomenclature and its transactions in one place.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from kolobot.file_store import FileStore
from kolobot.m11_matcher import compare_items, find_best_match
from kolobot.messages import unaccounted_notice_uk
from kolobot.warehouse_db import WarehouseDB



def _detect_doc_type_and_op(doc: Any) -> tuple[str, str]:
    """
    Returns (doc_type_label, default_op).
    doc_type_label: 'ВИМОГА М-11', 'ВИМОГА', 'НАКЛАДНА', or custom uppercase string.
    default_op: 'expense', 'income', or ''.
    """
    raw_doc_type = (getattr(doc, "doc_type", "") or "").strip().lower()
    title = (getattr(doc, "title", "") or "").strip().lower()
    summary = (getattr(doc, "summary", "") or "").strip().lower()
    raw_text = (getattr(doc, "raw_text", "") or "").strip()

    # Priority 0: M-11 detection before existing ВИМОГА/НАКЛАДНА checks
    if (
        re.search(r"типова\s+форма\s*№?\s*м[\s-]*11", raw_text, re.IGNORECASE)
        or re.search(r"типова\s+форма\s*№?\s*м[\s-]*11", title, re.IGNORECASE)
        or raw_doc_type in ("вимога м-11", "м-11")
    ):
        return "ВИМОГА М-11", ""

    header_lines = "\n".join(raw_text.lower().splitlines()[:5])

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


def match_m11_document(wdb: WarehouseDB, m11_doc_id: int) -> Optional[Dict[str, Any]]:
    """Match a single M-11 document against all existing classic ВИМОГА documents.

    If a match is found ('full' or 'partial'):
      - Detects conflicts: needs_review = 1 if matched ВИМОГА already has another M-11 linked.
      - Creates a row in document_links.
      - Returns link dict.
    If 'none' or no candidates:
      - Does not create document_links row.
      - Returns None.
    """
    m11_items = wdb.get_m11_items_by_document(m11_doc_id)
    if not m11_items:
        return None

    candidates = wdb.get_all_vimoga_documents_with_items(exclude_doc_id=m11_doc_id)
    if not candidates:
        return None

    best_doc_id, match_status = find_best_match(m11_items, candidates)
    if match_status == "none" or best_doc_id is None:
        return None

    existing_links = wdb.get_document_links_for_vimoga(best_doc_id)
    has_conflict = any(link["m11_doc_id"] != m11_doc_id for link in existing_links)
    needs_review = 1 if has_conflict else 0

    link_id = wdb.add_document_link(
        m11_doc_id=m11_doc_id,
        vimoga_doc_id=best_doc_id,
        match_status=match_status,
        needs_review=needs_review,
    )
    return {
        "id": link_id,
        "m11_doc_id": m11_doc_id,
        "vimoga_doc_id": best_doc_id,
        "match_status": match_status,
        "needs_review": needs_review,
    }


def match_vimoga_document(wdb: WarehouseDB, vimoga_doc_id: int) -> List[Dict[str, Any]]:
    """Match a classic ВИМОГА document against all unlinked M-11 documents.

    For each matching unlinked M-11 ('full' or 'partial'):
      - Detects conflicts: needs_review = 1 if matched ВИМОГА already has another M-11 linked.
      - Creates a row in document_links.
    If 'none':
      - M-11 stays unlinked (no document_links row).
    Returns list of created link dicts.
    """
    vimoga_items = wdb.get_vimoga_items(vimoga_doc_id)
    if not vimoga_items:
        return []

    unlinked_m11_docs = wdb.get_unlinked_m11_documents()
    if not unlinked_m11_docs:
        return []

    matches = []
    for m11_doc in unlinked_m11_docs:
        m11_id = m11_doc["id"]
        m11_items = wdb.get_m11_items_by_document(m11_id)
        if not m11_items:
            continue
        status = compare_items(m11_items, vimoga_items)
        if status in ("full", "partial"):
            matches.append({
                "m11_doc_id": m11_id,
                "match_status": status,
            })

    if not matches:
        return []

    # Process 'full' matches before 'partial' matches
    matches.sort(key=lambda m: (0 if m["match_status"] == "full" else 1, m["m11_doc_id"]))

    created_links = []
    for m in matches:
        m11_id = m["m11_doc_id"]
        match_status = m["match_status"]

        existing_links = wdb.get_document_links_for_vimoga(vimoga_doc_id)
        has_conflict = any(link["m11_doc_id"] != m11_id for link in existing_links)
        needs_review = 1 if has_conflict else 0

        link_id = wdb.add_document_link(
            m11_doc_id=m11_id,
            vimoga_doc_id=vimoga_doc_id,
            match_status=match_status,
            needs_review=needs_review,
        )
        created_links.append({
            "id": link_id,
            "m11_doc_id": m11_id,
            "vimoga_doc_id": vimoga_doc_id,
            "match_status": match_status,
            "needs_review": needs_review,
        })

    return created_links


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
        # Повторна обробка: транзакції попереднього проходу прибираємо ДО запису нових,
        # щоб прихід не подвоївся. Обидва записи йдуть однією транзакцією БД.
        # Позначку ручного редагування скидаємо: значення документа знову машинні.
        wdb.clear_document_transactions(existing_doc_id)
        wdb.delete_m11_items_by_document(existing_doc_id)
        wdb.delete_document_links_by_document(existing_doc_id)
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
            requested_by=getattr(doc, "requested_by", ""),
            requested_via=getattr(doc, "requested_via", ""),
            manual_edited=0,
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
            requested_by=getattr(doc, "requested_by", ""),
            requested_via=getattr(doc, "requested_via", ""),
        )

    items_list = getattr(doc, "items", []) or []

    if doc_type_label == "ВИМОГА М-11":
        m11_count = 0
        if items_list:
            for it in items_list:
                name = it.get("name", "").strip() if isinstance(it, dict) else getattr(it, "name", "").strip()
                if not name:
                    continue
                qty_raw = it.get("quantity", "") if isinstance(it, dict) else getattr(it, "quantity", "")
                qty_str = str(qty_raw or "").strip().replace(" ", "").replace(",", ".")
                try:
                    qty = float(qty_str) if qty_str else 0.0
                except ValueError:
                    qty = 0.0
                unit = str((it.get("unit", "") if isinstance(it, dict) else getattr(it, "unit", "")) or "").strip()
                sku = str((it.get("nomenclature_number", "") if isinstance(it, dict) else getattr(it, "nomenclature_number", "")) or "").strip()
                wdb.add_m11_item(
                    document_id=wh_doc_id,
                    name=name,
                    quantity=qty,
                    unit=unit,
                    nomenclature_number=sku,
                )
                m11_count += 1
        elif getattr(doc, "item_name", ""):
            name = doc.item_name.strip()
            if name:
                qty_raw = getattr(doc, "quantity", None)
                if qty_raw is None:
                    inc = getattr(doc, "incoming", "") or ""
                    out = getattr(doc, "outgoing", "") or ""
                    qty_str = str(inc or out or "").strip().replace(" ", "").replace(",", ".")
                else:
                    qty_str = str(qty_raw).strip().replace(" ", "").replace(",", ".")
                try:
                    qty = float(qty_str) if qty_str else 0.0
                except ValueError:
                    qty = 0.0
                unit = getattr(doc, "unit", "") or ""
                sku = str(getattr(doc, "nomenclature_number", "") or "").strip()
                wdb.add_m11_item(
                    document_id=wh_doc_id,
                    name=name,
                    quantity=qty,
                    unit=unit,
                    nomenclature_number=sku,
                )
                m11_count += 1

        match_result = match_m11_document(wdb, wh_doc_id)

        parts = []
        if m11_count:
            parts.append(f"{m11_count} позицій М-11")
        summary = "📋 Вимога М-11: " + ", ".join(parts) + "." if parts else "📋 Вимога М-11 збережена."

        if match_result:
            vid = match_result["vimoga_doc_id"]
            if match_result["match_status"] == "full":
                match_line = f"✅ Повне співпадіння з Вимогою #{vid}."
            else:
                match_line = f"⚠️ Часткове співпадіння з Вимогою #{vid}."
            if match_result.get("needs_review"):
                match_line += " (потребує перегляду)"
        else:
            match_line = "ℹ️ Співпадінь з існуючими вимогами не знайдено."

        return "\n\n".join(block for block in (summary, match_line) if block)

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

    if doc_type_label == "ВИМОГА":
        match_vimoga_document(wdb, wh_doc_id)

    parts = []
    if created:
        parts.append(f"{created} нових позицій")
    if updated:
        parts.append(f"{updated} оновлено")
    if txs:
        parts.append(f"{txs} транзакцій")
    summary = "📦 Склад: " + ", ".join(parts) + "." if parts else ""

    # Документ із нерозпізнаними обовʼязковими полями в облік не йде. Читаємо записаний
    # рядок, щоб повідомлення й таблиця документів не розходились у тому, що вважати повним.
    saved_doc = wdb.get_document(wh_doc_id)
    notice = unaccounted_notice_uk(saved_doc) if saved_doc else ""

    return "\n\n".join(block for block in (summary, notice) if block)

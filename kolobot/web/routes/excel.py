"""Excel in and out: the upload that becomes a document, and the export."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Tuple

from aiohttp import web

from kolobot.warehouse_db import WarehouseDB
from kolobot.web.context import WebContext
from kolobot.web.router import route

logger = logging.getLogger("kolobot.web_server")


@route("POST", "/api/warehouse/import")
async def import_excel(ctx: WebContext, request: web.Request) -> web.Response:
    from kolobot.excel_service import parse_excel

    reader = await request.multipart()
    field = await reader.next()
    if field is None or field.name != "file":
        return web.json_response({"error": "Файл не надано"}, status=400)

    filename = field.filename or "import.xlsx"
    data = await field.read()

    logger.info("[Excel Import] Отримано файл: %s (%d байт)", filename, len(data))

    # The upload is staged next to the other files, parsed, then moved into place.
    tmp_dir = os.path.join(ctx.files._base, "tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tmp_path = os.path.join(tmp_dir, f"import_{int(time.time())}_{filename}")
    with open(tmp_path, "wb") as f:
        f.write(data)

    logger.info("[Excel Import] Парсинг файлу...")
    try:
        doc_type, rows = parse_excel(tmp_path)
    except Exception as exc:
        logger.error("[Excel Import] Помилка парсингу: %s", exc)
        os.remove(tmp_path)
        return web.json_response({"error": f"Помилка парсингу: {exc}"}, status=400)

    if not rows:
        os.remove(tmp_path)
        logger.warning("[Excel Import] Файл порожній або структура не розпізнана")
        return web.json_response({"error": "Файл порожній або структура не розпізнана"}, status=400)

    logger.info("[Excel Import] Тип документу: %s, рядків: %d", doc_type or "не визначено", len(rows))

    final_path = os.path.join(str(ctx.files._base), f"excel_{int(time.time())}_{filename}")
    os.replace(tmp_path, final_path)

    doc_id = ctx.db.add_document(
        filename=filename,
        file_type="excel",
        file_path=final_path,
        doc_type=doc_type,
    )

    items_created, items_updated, transactions_created = _apply_rows(ctx.db, doc_id, doc_type, rows)

    logger.info("[Excel Import] Завершено: %d нових, %d оновлено, %d транзакцій",
                items_created, items_updated, transactions_created)

    return web.json_response({
        "success": True,
        "doc_type": doc_type,
        "items_created": items_created,
        "items_updated": items_updated,
        "transactions_created": transactions_created,
    })


@route("GET", "/api/warehouse/export")
async def export_excel(ctx: WebContext, request: web.Request) -> web.Response:
    from kolobot.excel_service import export_excel as build_workbook

    items = ctx.db.get_items_with_balance()
    data = build_workbook(items)
    return web.Response(
        body=data,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="warehouse_export.xlsx"'},
    )


def _apply_rows(
    db: WarehouseDB,
    doc_id: int,
    doc_type: str,
    rows: List[Dict[str, Any]],
) -> Tuple[int, int, int]:
    """Turn parsed rows into items and transactions. ``(created, updated, transactions)``."""
    items_created = 0
    items_updated = 0
    transactions_created = 0

    is_nakladna = doc_type == "НАКЛАДНА"
    is_vymoha = doc_type == "ВИМОГА"

    for i, row in enumerate(rows, 1):
        logger.info("[Excel Import] Обробка рядка %d/%d: %s", i, len(rows), row.get("name", ""))
        min_bal_val = row.get("min_balance")
        min_bal = float(min_bal_val) if min_bal_val is not None else 0.0
        existing = db.find_item(sku=row.get("sku", ""), name=row["name"])
        if existing:
            item_id = existing["id"]
            items_updated += 1
            update_kwargs: dict[str, Any] = {
                "sku": row.get("sku", ""),
                "unit": row.get("unit", ""),
                "supplier": row.get("supplier", ""),
                "notes": row.get("notes", ""),
            }
            if min_bal_val is not None:
                update_kwargs["min_balance"] = min_bal
            db.update_item(
                item_id,
                **update_kwargs,
            )
        else:
            item_id = db.add_item(
                name=row["name"],
                sku=row.get("sku", ""),
                unit=row.get("unit", ""),
                supplier=row.get("supplier", ""),
                notes=row.get("notes", ""),
                min_balance=min_bal,
            )
            items_created += 1

        source_row = row.get("source_row", "")
        row_doc_type = row.get("doc_type", "") or doc_type

        income = row.get("income")
        expense = row.get("expense")
        balance = row.get("balance")

        if is_nakladna or row_doc_type == "НАКЛАДНА":
            qty = 0.0
            if income and float(income) > 0:
                qty = float(income)
            elif expense and float(expense) > 0:
                qty = float(expense)
            elif balance and float(balance) > 0:
                qty = float(balance)
            db.add_transaction(
                item_id=item_id, document_id=doc_id,
                operation_type="income", quantity=qty,
                doc_number=row.get("doc_number", ""),
                doc_date=row.get("doc_date", ""),
                source_row=source_row,
            )
            transactions_created += 1
        elif is_vymoha or row_doc_type == "ВИМОГА":
            qty = 0.0
            if expense and float(expense) > 0:
                qty = float(expense)
            elif income and float(income) > 0:
                qty = float(income)
            elif balance and float(balance) > 0:
                qty = float(balance)
            db.add_transaction(
                item_id=item_id, document_id=doc_id,
                operation_type="expense", quantity=qty,
                doc_number=row.get("doc_number", ""),
                doc_date=row.get("doc_date", ""),
                source_row=source_row,
            )
            transactions_created += 1
        else:
            created_any = False
            if income and float(income) > 0:
                db.add_transaction(
                    item_id=item_id, document_id=doc_id,
                    operation_type="income", quantity=float(income),
                    doc_number=row.get("doc_number", ""),
                    doc_date=row.get("doc_date", ""),
                    source_row=source_row,
                )
                transactions_created += 1
                created_any = True
            if expense and float(expense) > 0:
                db.add_transaction(
                    item_id=item_id, document_id=doc_id,
                    operation_type="expense", quantity=float(expense),
                    doc_number=row.get("doc_number", ""),
                    doc_date=row.get("doc_date", ""),
                    source_row=source_row,
                )
                transactions_created += 1
                created_any = True

            if not created_any:
                bal_qty = float(balance) if balance else 0.0
                db.add_transaction(
                    item_id=item_id, document_id=doc_id,
                    operation_type="income", quantity=max(bal_qty, 0.0),
                    doc_number=row.get("doc_number", ""),
                    doc_date=row.get("doc_date", ""),
                    source_row=source_row,
                )
                transactions_created += 1

    return items_created, items_updated, transactions_created

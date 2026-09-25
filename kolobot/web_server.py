"""Embedded aiohttp web server: warehouse inventory UI with two tabs + REST API.

Also the frontend's public surface: ``PAGE`` is the document served at ``GET /``
and ``JS`` the sources of the modules it runs. Both come from ``kolobot/web/ui/``.
"""

from __future__ import annotations

__all__ = ["WebServer", "PAGE", "JS"]

import asyncio
import datetime
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from aiohttp import web

from kolobot.file_store import FileStore
from kolobot.log_service import LogBuffer, LogEntry, get_global_log_buffer, setup_logging_capture
from kolobot.vector_store import VectorStore
from kolobot.warehouse_db import WarehouseDB, missing_doc_fields
from kolobot.web.assets import JS, PAGE

logger = logging.getLogger(__name__)


class WebServer:

    def __init__(
        self,
        warehouse_db: WarehouseDB,
        file_store: FileStore,
        vector_store: Optional[VectorStore],
        owner_user_id: int,
        host: str = "127.0.0.1",
        port: int = 8000,
        log_buffer: Optional[LogBuffer] = None,
        queue_service: Optional[Any] = None,
    ) -> None:
        self._db = warehouse_db
        self._fs = file_store
        self._vs = vector_store
        self._owner_id = owner_user_id
        self._host = host
        self._port = port
        self._log_buffer = log_buffer or get_global_log_buffer()
        self._queue_service = queue_service
        setup_logging_capture(buffer=self._log_buffer)

        self._app = web.Application(client_max_size=50 * 1024 * 1024)
        self._setup_routes()
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    def _setup_routes(self) -> None:
        self._app.router.add_get("/", self._index)
        self._app.router.add_get("/api/warehouse/items", self._api_items)
        self._app.router.add_get("/api/warehouse/items/{item_id}/transactions", self._api_item_transactions)
        self._app.router.add_post("/api/warehouse/items/{item_id}/edit", self._api_edit_item)
        self._app.router.add_patch("/api/warehouse/items/{item_id}", self._api_edit_item)
        self._app.router.add_post("/api/warehouse/items/{item_id}", self._api_edit_item)
        self._app.router.add_get("/api/warehouse/documents", self._api_documents)
        self._app.router.add_post("/api/warehouse/documents/{doc_id}/edit", self._api_edit_document)
        self._app.router.add_post("/api/warehouse/documents/{doc_id}/retry", self._api_retry_document)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/impact", self._api_document_impact)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/ocr", self._api_document_ocr)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/view", self._api_document_view)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/download", self._api_document_download)
        self._app.router.add_get("/api/warehouse/documents/{doc_id}/preview", self._api_document_preview)
        self._app.router.add_delete("/api/warehouse/documents/{doc_id}", self._api_delete_document)
        self._app.router.add_post("/api/warehouse/import", self._api_import_excel)
        self._app.router.add_get("/api/warehouse/export", self._api_export_excel)
        self._app.router.add_get("/api/logs", self._api_logs)
        self._app.router.add_post("/api/logs/clear", self._api_clear_logs)
        self._app.router.add_delete("/api/logs", self._api_clear_logs)
        self._app.router.add_get("/api/logs/stream", self._api_stream_logs)

    async def _index(self, request: web.Request) -> web.Response:
        return web.Response(text=PAGE, content_type="text/html")

    async def _api_items(self, request: web.Request) -> web.Response:
        items = self._db.get_items_with_balance()
        return web.json_response(items)

    async def _api_item_transactions(self, request: web.Request) -> web.Response:
        item_id = int(request.match_info["item_id"])
        txs = self._db.get_item_transactions(item_id)
        return web.json_response(txs)

    async def _api_edit_item(self, request: web.Request) -> web.Response:
        try:
            item_id = int(request.match_info["item_id"])
        except (KeyError, ValueError):
            return web.json_response({"error": "Некоректний ID позиції"}, status=400)

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Некоректний JSON"}, status=400)

        if not isinstance(data, dict):
            return web.json_response({"error": "Тіло запиту має бути JSON об'єктом"}, status=400)

        field = data.get("field")
        value = data.get("value")
        comment = data.get("comment", "")

        allowed_fields = {"name", "sku", "unit", "supplier", "notes", "balance", "quantity", "min_balance"}
        if not field:
            matching_fields = [k for k in data.keys() if k in allowed_fields]
            if len(matching_fields) == 1:
                field = matching_fields[0]
                value = data[field]
            else:
                return web.json_response({"error": "Не вказано поле для редагування ('field')"}, status=400)

        if field not in allowed_fields:
            return web.json_response(
                {"error": f"Непідтримуване поле: {field}. Дозволені: {sorted(allowed_fields)}"},
                status=400,
            )

        if value is None or (isinstance(value, str) and not value.strip() and field in {"balance", "quantity"}):
            return web.json_response({"error": "Значення ('value') не може бути порожнім/null"}, status=400)

        item = self._db.get_item(item_id)
        if not item:
            return web.json_response({"error": "Позицію не знайдено"}, status=404)

        if field == "min_balance":
            try:
                min_val = float(value) if value not in (None, "") else 0.0
                if min_val < 0:
                    min_val = 0.0
            except (ValueError, TypeError):
                return web.json_response({"error": "Значення мінімального залишку має бути числом"}, status=400)

            try:
                result = self._db.adjust_item_field(
                    item_id=item_id,
                    field="min_balance",
                    new_value=min_val,
                    comment=str(comment or ""),
                )
            except Exception as exc:
                logger.error("Error adjusting item min_balance: %s", exc)
                return web.json_response({"error": f"Помилка оновлення: {exc}"}, status=400)

            if not result:
                return web.json_response({"error": "Позицію не знайдено"}, status=404)

            return web.json_response(result)

        if field in {"balance", "quantity"}:
            try:
                target_qty = float(value)
            except (ValueError, TypeError):
                return web.json_response({"error": "Значення кількості має бути числом"}, status=400)

            try:
                result = self._db.adjust_item_quantity(
                    item_id=item_id,
                    target_quantity=target_qty,
                    comment=str(comment or ""),
                )
            except Exception as exc:
                logger.error("Error adjusting item quantity: %s", exc)
                return web.json_response({"error": f"Помилка оновлення кількості: {exc}"}, status=400)

            if not result:
                return web.json_response({"error": "Позицію не знайдено"}, status=404)

            updated_item = self._db.get_item(item_id)
            if updated_item:
                updated_item["balance"] = target_qty
                result["item"] = updated_item

            return web.json_response(result)

        try:
            result = self._db.adjust_item_field(
                item_id=item_id,
                field=field,
                new_value=str(value),
                comment=str(comment or ""),
            )
        except Exception as exc:
            logger.error("Error adjusting item field: %s", exc)
            return web.json_response({"error": f"Помилка оновлення: {exc}"}, status=400)

        if not result:
            return web.json_response({"error": "Позицію не знайдено"}, status=404)

        return web.json_response(result)

    async def _api_documents(self, request: web.Request) -> web.Response:
        docs = self._db.get_documents()
        return web.json_response(docs)

    async def _api_edit_document(self, request: web.Request) -> web.Response:
        """Ручне дозаповнення одного з пʼяти полів розпізнавання документа."""
        try:
            doc_id = int(request.match_info["doc_id"])
        except (KeyError, ValueError):
            return web.json_response({"error": "Некоректний ID документа"}, status=400)

        try:
            data = await request.json()
        except Exception:
            return web.json_response({"error": "Некоректний JSON"}, status=400)

        if not isinstance(data, dict):
            return web.json_response({"error": "Тіло запиту має бути JSON об'єктом"}, status=400)

        field = data.get("field")
        if not field:
            return web.json_response({"error": "Не вказано поле для редагування ('field')"}, status=400)

        if "value" not in data:
            return web.json_response({"error": "Не вказано значення ('value')"}, status=400)

        comment = str(data.get("comment") or "").strip()
        try:
            result = self._db.edit_document_field(
                doc_id=doc_id,
                field=str(field),
                value=data.get("value"),
            )
        except ValueError as exc:
            return web.json_response({"error": str(exc)}, status=400)

        if not result:
            return web.json_response({"error": "Документ не знайдено"}, status=404)

        logger.info(
            "[Документ %d] Ручна правка [%s]: '%s' → '%s'%s (транзакцій оновлено: %d)",
            doc_id,
            result["label"],
            result["old_value"],
            result["new_value"],
            f", коментар: {comment}" if comment else "",
            result["transactions_updated"],
        )
        return web.json_response(result)

    async def _api_retry_document(self, request: web.Request) -> web.Response:
        try:
            doc_id = int(request.match_info["doc_id"])
        except (KeyError, ValueError):
            return web.json_response({"error": "Некоректний ID документа"}, status=400)

        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)

        # Reset status to queued in DB
        self._db.update_document(doc_id, status="queued", error_message="")

        if self._queue_service:
            try:
                await self._queue_service.retry_document(doc_id)
            except Exception as exc:
                logger.error("Error re-enqueuing document %d: %s", doc_id, exc)

        updated_doc = self._db.get_document(doc_id)
        return web.json_response({
            "success": True,
            "status": "queued",
            "document": updated_doc,
        })

    async def _api_document_impact(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        impact = self._db.get_document_impact(doc_id)
        return web.json_response(impact)

    async def _api_document_ocr(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)
        impact = self._db.get_document_impact(doc_id)
        raw_text = ""
        # 1. Try reading from .txt file on disk via FileStore or direct file_path
        stems_to_try: list[str] = []
        if doc.get("file_path"):
            stems_to_try.append(os.path.splitext(os.path.basename(doc["file_path"]))[0])
            txt_direct = os.path.splitext(doc["file_path"])[0] + ".txt"
            if os.path.exists(txt_direct):
                try:
                    with open(txt_direct, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                except Exception:
                    pass
        if not raw_text and doc.get("filename"):
            stems_to_try.append(os.path.splitext(os.path.basename(doc["filename"]))[0])
        stems_to_try.append(str(doc_id))

        if not raw_text:
            for stem in stems_to_try:
                if stem:
                    try:
                        t = self._fs.read_text(stem)
                        if isinstance(t, str) and t:
                            raw_text = t
                            break
                    except Exception:
                        pass

        # 2. Fallback to DB raw_text
        if not raw_text:
            raw_text = doc.get("raw_text", "")
            if not isinstance(raw_text, str):
                raw_text = str(raw_text or "")

        return web.json_response({
            "id": doc["id"],
            "filename": doc["filename"],
            "file_type": doc["file_type"],
            # Усі пʼять полів розпізнавання присутні завжди: порожнє — порожній рядок, а не пропущений ключ.
            "doc_type": doc.get("doc_type") or "",
            "doc_number": doc.get("doc_number") or "",
            "doc_date": doc.get("doc_date") or "",
            "requested_by": doc.get("requested_by") or "",
            "requested_via": doc.get("requested_via") or "",
            # Той самий перелік, що й у таблиці: рахує спільний помічник, не фронтенд.
            "missing_fields": missing_doc_fields(doc),
            "raw_text": raw_text,
            "impact": impact,
            "status": doc.get("status", "completed"),
            "error_message": doc.get("error_message", ""),
        })

    async def _api_document_view(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)
        file_path = doc["file_path"]
        if not file_path or not os.path.exists(file_path):
            return web.json_response({"error": "Файл відсутній на диску"}, status=404)
        ct = "image/jpeg"
        if file_path.endswith(".png"):
            ct = "image/png"
        elif file_path.endswith(".pdf"):
            ct = "application/pdf"
        elif file_path.endswith(".xlsx"):
            ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return web.FileResponse(path=file_path, headers={"Content-Type": ct})

    async def _api_document_download(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)
        file_path = doc["file_path"]
        if not file_path or not os.path.exists(file_path):
            return web.json_response({"error": "Файл відсутній"}, status=404)
        return web.FileResponse(
            path=file_path,
            headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'},
        )

    async def _api_delete_document(self, request: web.Request) -> web.Response:
        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)

        file_path = doc.get("file_path", "")

        ok = self._db.delete_document(doc_id)
        if not ok:
            return web.json_response({"error": "Документ не знайдено"}, status=404)

        if file_path:
            chroma_doc_id = os.path.splitext(os.path.basename(file_path))[0]
            if self._vs and len(chroma_doc_id) == 10:
                try:
                    self._vs.delete(chroma_doc_id)
                except Exception:
                    pass
            try:
                os.remove(file_path)
            except FileNotFoundError:
                pass

        return web.json_response({"success": True})

    async def _api_document_preview(self, request: web.Request) -> web.Response:
        from kolobot.excel_service import preview_excel

        doc_id = int(request.match_info["doc_id"])
        doc = self._db.get_document(doc_id)
        if not doc:
            return web.json_response({"error": "Документ не знайдено"}, status=404)
        file_path = doc["file_path"]
        if not file_path or not os.path.exists(file_path):
            return web.json_response({"error": "Файл відсутній на диску"}, status=404)
        try:
            max_rows = 100
            highlight_param = request.query.get("highlight", "")
            if highlight_param:
                try:
                    highlight_nums = [int(x) for x in highlight_param.split(",") if x.strip()]
                    if highlight_nums:
                        max_rows = max(max_rows, max(highlight_nums) + 5)
                except ValueError:
                    pass
            data = preview_excel(file_path, max_rows=max_rows)
            return web.json_response(data)
        except Exception as exc:
            return web.json_response({"error": f"Помилка читання: {exc}"}, status=400)

    async def _api_import_excel(self, request: web.Request) -> web.Response:
        from kolobot.excel_service import parse_excel

        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "file":
            return web.json_response({"error": "Файл не надано"}, status=400)

        filename = field.filename or "import.xlsx"
        data = await field.read()

        logger.info("[Excel Import] Отримано файл: %s (%d байт)", filename, len(data))

        tmp_dir = os.path.join(self._fs._base, "tmp")
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

        final_path = os.path.join(str(self._fs._base), f"excel_{int(time.time())}_{filename}")
        os.replace(tmp_path, final_path)

        doc_id = self._db.add_document(
            filename=filename,
            file_type="excel",
            file_path=final_path,
            doc_type=doc_type,
        )

        items_created = 0
        items_updated = 0
        transactions_created = 0

        is_nakladna = doc_type == "НАКЛАДНА"
        is_vymoha = doc_type == "ВИМОГА"

        for i, row in enumerate(rows, 1):
            logger.info("[Excel Import] Обробка рядка %d/%d: %s", i, len(rows), row.get("name", ""))
            min_bal_val = row.get("min_balance")
            min_bal = float(min_bal_val) if min_bal_val is not None else 0.0
            existing = self._db.find_item(sku=row.get("sku", ""), name=row["name"])
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
                self._db.update_item(
                    item_id,
                    **update_kwargs,
                )
            else:
                item_id = self._db.add_item(
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
                self._db.add_transaction(
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
                self._db.add_transaction(
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
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="income", quantity=float(income),
                        doc_number=row.get("doc_number", ""),
                        doc_date=row.get("doc_date", ""),
                        source_row=source_row,
                    )
                    transactions_created += 1
                    created_any = True
                if expense and float(expense) > 0:
                    self._db.add_transaction(
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
                    self._db.add_transaction(
                        item_id=item_id, document_id=doc_id,
                        operation_type="income", quantity=max(bal_qty, 0.0),
                        doc_number=row.get("doc_number", ""),
                        doc_date=row.get("doc_date", ""),
                        source_row=source_row,
                    )
                    transactions_created += 1

        logger.info("[Excel Import] Завершено: %d нових, %d оновлено, %d транзакцій",
                    items_created, items_updated, transactions_created)

        return web.json_response({
            "success": True,
            "doc_type": doc_type,
            "items_created": items_created,
            "items_updated": items_updated,
            "transactions_created": transactions_created,
        })

    async def _api_export_excel(self, request: web.Request) -> web.Response:
        from kolobot.excel_service import export_excel

        items = self._db.get_items_with_balance()
        data = export_excel(items)
        return web.Response(
            body=data,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="warehouse_export.xlsx"'},
        )

    async def _api_logs(self, request: web.Request) -> web.Response:
        try:
            since_id = int(request.query.get("since_id", 0))
        except ValueError:
            since_id = 0
        try:
            limit = int(request.query.get("limit", 1000))
        except ValueError:
            limit = 1000
        level = request.query.get("level")
        query = request.query.get("q")

        entries, total, last_id = self._log_buffer.get_logs(
            since_id=since_id,
            limit=limit,
            level=level,
            query=query,
        )
        return web.json_response({
            "logs": [e.to_dict() for e in entries],
            "total_count": total,
            "last_id": last_id,
        })

    async def _api_clear_logs(self, request: web.Request) -> web.Response:
        count = self._log_buffer.clear()
        return web.json_response({"success": True, "cleared_count": count})

    async def _api_stream_logs(self, request: web.Request) -> web.StreamResponse:
        resp = web.StreamResponse(
            status=200,
            reason="OK",
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
        await resp.prepare(request)

        queue = self._log_buffer.subscribe()
        try:
            # Send initial ping comment
            await resp.write(b": ping\n\n")
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=15.0)
                    data_str = json.dumps(entry.to_dict(), ensure_ascii=False)
                    payload = f"data: {data_str}\n\n"
                    await resp.write(payload.encode("utf-8"))
                except asyncio.TimeoutError:
                    # Heartbeat comment to prevent client timeout
                    await resp.write(b": ping\n\n")
        except (asyncio.CancelledError, ConnectionResetError):
            pass
        finally:
            self._log_buffer.unsubscribe(queue)

        return resp

    async def start(self) -> None:
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()
        logger.info("WebServer running on http://%s:%s", self._host, self._port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            logger.info("WebServer stopped.")

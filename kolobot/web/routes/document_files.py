"""One document's files: its recognised text, and the file on disk."""

from __future__ import annotations

import logging
import os

from aiohttp import web

from kolobot.warehouse_db import missing_doc_fields
from kolobot.web.context import WebContext
from kolobot.web.router import route

logger = logging.getLogger("kolobot.web_server")


@route("GET", "/api/warehouse/documents/{doc_id}/ocr")
async def document_ocr(ctx: WebContext, request: web.Request) -> web.Response:
    doc_id = int(request.match_info["doc_id"])
    doc = ctx.db.get_document(doc_id)
    if not doc:
        return web.json_response({"error": "Документ не знайдено"}, status=404)
    impact = ctx.db.get_document_impact(doc_id)
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
                    t = ctx.files.read_text(stem)
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


@route("GET", "/api/warehouse/documents/{doc_id}/view")
async def document_view(ctx: WebContext, request: web.Request) -> web.Response:
    doc_id = int(request.match_info["doc_id"])
    doc = ctx.db.get_document(doc_id)
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


@route("GET", "/api/warehouse/documents/{doc_id}/download")
async def document_download(ctx: WebContext, request: web.Request) -> web.Response:
    doc_id = int(request.match_info["doc_id"])
    doc = ctx.db.get_document(doc_id)
    if not doc:
        return web.json_response({"error": "Документ не знайдено"}, status=404)
    file_path = doc["file_path"]
    if not file_path or not os.path.exists(file_path):
        return web.json_response({"error": "Файл відсутній"}, status=404)
    return web.FileResponse(
        path=file_path,
        headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'},
    )


@route("GET", "/api/warehouse/documents/{doc_id}/preview")
async def document_preview(ctx: WebContext, request: web.Request) -> web.Response:
    from kolobot.excel_service import preview_excel

    doc_id = int(request.match_info["doc_id"])
    doc = ctx.db.get_document(doc_id)
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


@route("DELETE", "/api/warehouse/documents/{doc_id}")
async def delete_document(ctx: WebContext, request: web.Request) -> web.Response:
    doc_id = int(request.match_info["doc_id"])
    doc = ctx.db.get_document(doc_id)
    if not doc:
        return web.json_response({"error": "Документ не знайдено"}, status=404)

    file_path = doc.get("file_path", "")

    ok = ctx.db.delete_document(doc_id)
    if not ok:
        return web.json_response({"error": "Документ не знайдено"}, status=404)

    if file_path:
        chroma_doc_id = os.path.splitext(os.path.basename(file_path))[0]
        if ctx.vectors and len(chroma_doc_id) == 10:
            try:
                ctx.vectors.delete(chroma_doc_id)
            except Exception:
                pass
        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass

    return web.json_response({"success": True})

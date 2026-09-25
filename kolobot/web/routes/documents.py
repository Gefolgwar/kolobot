"""Warehouse documents: the list, one field of one document, retry, impact."""

from __future__ import annotations

import logging

from aiohttp import web

from kolobot.web.context import WebContext
from kolobot.web.router import route

logger = logging.getLogger("kolobot.web_server")


@route("GET", "/api/warehouse/documents")
async def documents(ctx: WebContext, request: web.Request) -> web.Response:
    return web.json_response(ctx.db.get_documents())


@route("POST", "/api/warehouse/documents/{doc_id}/edit")
async def edit_document(ctx: WebContext, request: web.Request) -> web.Response:
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
        result = ctx.db.edit_document_field(
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


@route("POST", "/api/warehouse/documents/{doc_id}/retry")
async def retry_document(ctx: WebContext, request: web.Request) -> web.Response:
    try:
        doc_id = int(request.match_info["doc_id"])
    except (KeyError, ValueError):
        return web.json_response({"error": "Некоректний ID документа"}, status=400)

    doc = ctx.db.get_document(doc_id)
    if not doc:
        return web.json_response({"error": "Документ не знайдено"}, status=404)

    # Reset status to queued in DB
    ctx.db.update_document(doc_id, status="queued", error_message="")

    if ctx.queue:
        try:
            await ctx.queue.retry_document(doc_id)
        except Exception as exc:
            logger.error("Error re-enqueuing document %d: %s", doc_id, exc)

    updated_doc = ctx.db.get_document(doc_id)
    return web.json_response({
        "success": True,
        "status": "queued",
        "document": updated_doc,
    })


@route("GET", "/api/warehouse/documents/{doc_id}/impact")
async def document_impact(ctx: WebContext, request: web.Request) -> web.Response:
    doc_id = int(request.match_info["doc_id"])
    impact = ctx.db.get_document_impact(doc_id)
    return web.json_response(impact)

"""Routes for M-11 documents."""

from __future__ import annotations

import logging

from aiohttp import web

from kolobot.web.context import WebContext
from kolobot.web.router import route

logger = logging.getLogger("kolobot.web_server")


@route("GET", "/api/warehouse/m11")
async def get_m11(ctx: WebContext, request: web.Request) -> web.Response:
    """Return all M-11 documents with item count, match status, and link data."""
    docs = ctx.db.get_m11_documents()
    return web.json_response(docs)


@route("POST", "/api/m11/links/{link_id}/confirm")
async def confirm_link(ctx: WebContext, request: web.Request) -> web.Response:
    """Confirm a document link (changes match_status to 'full', needs_review to 0)."""
    try:
        link_id = int(request.match_info["link_id"])
    except (KeyError, ValueError):
        return web.json_response({"error": "Некоректний ID зв'язку"}, status=400)

    link = ctx.db.get_document_link(link_id)
    if not link:
        return web.json_response({"error": "Зв'язок не знайдено"}, status=404)

    ok = ctx.db.confirm_link(link_id)
    if not ok:
        return web.json_response({"error": "Не вдалося підтвердити зв'язок"}, status=500)

    logger.info("[M-11] Підтверджено зв'язок #%d", link_id)
    return web.json_response({
        "success": True,
        "link_id": link_id,
        "match_status": "full",
        "needs_review": 0,
    })


@route("DELETE", "/api/m11/links/{link_id}")
async def delete_link(ctx: WebContext, request: web.Request) -> web.Response:
    """Delete a document link (unlinking M-11 and classic vimoga)."""
    try:
        link_id = int(request.match_info["link_id"])
    except (KeyError, ValueError):
        return web.json_response({"error": "Некоректний ID зв'язку"}, status=400)

    link = ctx.db.get_document_link(link_id)
    if not link:
        return web.json_response({"error": "Зв'язок не знайдено"}, status=404)

    ok = ctx.db.delete_link(link_id)
    if not ok:
        return web.json_response({"error": "Не вдалося видалити зв'язок"}, status=500)

    logger.info("[M-11] Видалено зв'язок #%d", link_id)
    return web.json_response({"success": True})


@route("POST", "/api/m11/{doc_id}/bind")
async def bind_m11(ctx: WebContext, request: web.Request) -> web.Response:
    """Manually bind an M-11 document to a classic ВИМОГА document."""
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

    vimoga_doc_id = data.get("vimoga_doc_id")
    if vimoga_doc_id is None:
        return web.json_response({"error": "Не вказано 'vimoga_doc_id'"}, status=400)

    try:
        vimoga_doc_id = int(vimoga_doc_id)
    except (ValueError, TypeError):
        return web.json_response({"error": "Некоректний vimoga_doc_id"}, status=400)

    m11_doc = ctx.db.get_document(doc_id)
    if not m11_doc:
        return web.json_response({"error": "Документ М-11 не знайдено"}, status=404)

    vimoga_doc = ctx.db.get_document(vimoga_doc_id)
    if not vimoga_doc:
        return web.json_response({"error": "Документ ВИМОГА не знайдено"}, status=404)

    link_id = ctx.db.create_manual_link(m11_doc_id=doc_id, vimoga_doc_id=vimoga_doc_id)
    logger.info(
        "[M-11] Документ #%d вручну прив'язано до ВИМОГИ #%d (link #%d)",
        doc_id,
        vimoga_doc_id,
        link_id,
    )
    return web.json_response({
        "success": True,
        "link_id": link_id,
        "m11_doc_id": doc_id,
        "vimoga_doc_id": vimoga_doc_id,
        "match_status": "manual",
    })


@route("GET", "/api/m11/available-vimogas")
async def get_available_vimogas(ctx: WebContext, request: web.Request) -> web.Response:
    """Return all classic ВИМОГА documents (unlinked first, already-linked below)."""
    docs = ctx.db.get_available_vimogas()
    return web.json_response(docs)

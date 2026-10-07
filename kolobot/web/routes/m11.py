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

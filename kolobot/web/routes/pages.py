"""``GET /`` — the one HTML document."""

from __future__ import annotations

import logging

from aiohttp import web

from kolobot.web.context import WebContext
from kolobot.web.router import route

logger = logging.getLogger("kolobot.web_server")


@route("GET", "/")
async def index(ctx: WebContext, request: web.Request) -> web.Response:
    return web.Response(text=ctx.frontend.html(), content_type="text/html")

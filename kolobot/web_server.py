"""Embedded aiohttp web server: warehouse inventory UI with two tabs + REST API.

The public surface is exactly three names:

    WebServer   — the server: build it, start it, stop it.
    PAGE        — the finished HTML document served at ``GET /``.
    JS          — the page's JS module sources, in the order they are served.

Nothing else is public. The server itself lives in ``kolobot/web/server.py``,
its routes in ``kolobot/web/routes/``, and the page in ``kolobot/web/ui/``.
"""

from __future__ import annotations

__all__ = ["WebServer", "PAGE", "JS"]

from kolobot.web.assets import JS, PAGE
from kolobot.web.server import WebServer

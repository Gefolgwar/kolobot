"""``WebServer``: assemble the application, start it, stop it.

The application's routes are not listed here — ``discover()`` walks the route
package and registers what it finds. The context is built once, here, and bound
to every handler on the way in.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from aiohttp import web

from kolobot.file_store import FileStore
from kolobot.log_service import LogBuffer, get_global_log_buffer, setup_logging_capture
from kolobot.vector_store import VectorStore
from kolobot.warehouse_db import WarehouseDB
from kolobot.web.context import WebContext
from kolobot.web.frontend import Frontend
from kolobot.web.router import discover

logger = logging.getLogger("kolobot.web_server")

#: The package the routes live in. Dropping a module into it is the whole
#: registration procedure — this string is the only place that names it.
ROUTES_PACKAGE = "kolobot.web.routes"


class WebServer:
    """The embedded HTTP server. ``app`` is what a test drives with aiohttp."""

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
        self._host = host
        self._port = port
        log_buffer = log_buffer or get_global_log_buffer()
        setup_logging_capture(buffer=log_buffer)

        self.app = web.Application(client_max_size=50 * 1024 * 1024)
        discover(
            ROUTES_PACKAGE,
            WebContext(
                db=warehouse_db,
                files=file_store,
                vectors=vector_store,
                logs=log_buffer,
                queue=queue_service,
                owner_user_id=owner_user_id,
                frontend=Frontend(),
            ),
            self.app,
        )
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None

    async def start(self) -> None:
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()
        logger.info("WebServer running on http://%s:%s", self._host, self._port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            logger.info("WebServer stopped.")

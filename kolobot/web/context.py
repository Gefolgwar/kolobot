"""``WebContext``: everything a handler is allowed to touch.

A handler is a plain function ``async def h(ctx, request)``. The context is the
only door to the database, the files, the vector store, the log ring and the
queue — which is why a route module never imports another route module, and
never imports ``WebServer``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from kolobot.file_store import FileStore
from kolobot.log_service import LogBuffer
from kolobot.vector_store import VectorStore
from kolobot.warehouse_db import WarehouseDB
from kolobot.web.frontend import Frontend

logger = logging.getLogger("kolobot.web_server")


@dataclass(frozen=True)
class WebContext:
    """Built once by ``WebServer``, bound to every handler by ``discover()``."""

    db: WarehouseDB
    files: FileStore
    vectors: Optional[VectorStore]
    logs: LogBuffer
    queue: Optional[Any]
    owner_user_id: int
    frontend: Frontend

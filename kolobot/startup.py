"""Startup housekeeping that runs once, before polling begins.

Reconciles ChromaDB with the warehouse: a vector record whose file stem has
no row in the warehouse is an orphan, so the record and any local copies of
it are removed. Keeps the two stores from drifting apart across restarts.
"""

from __future__ import annotations

import logging
import os

from kolobot.file_store import FileStore
from kolobot.vector_store import VectorStore
from kolobot.warehouse_db import WarehouseDB


logger = logging.getLogger(__name__)


def _sync_chroma_with_warehouse(
    vs: VectorStore,
    wdb: WarehouseDB,
    fs: FileStore,
    owner_user_id: int,
) -> None:
    chroma_ids = vs.list_all_ids(owner_user_id)
    if not chroma_ids:
        return

    wh_docs = wdb.get_documents()
    known_chroma_ids = set()
    for doc in wh_docs:
        fp = doc.get("file_path", "")
        if fp:
            stem = os.path.splitext(os.path.basename(fp))[0]
            if len(stem) == 10:
                known_chroma_ids.add(stem)

    orphans = [cid for cid in chroma_ids if cid not in known_chroma_ids]
    for cid in orphans:
        vs.delete(cid)
        for ext in (".jpg", ".png", ".webp", ".pdf"):
            fs.delete_final(cid, ext=ext)
    if orphans:
        logger.info("Startup sync: removed %d orphaned ChromaDB records.", len(orphans))

"""DocumentIntakeService: accept incoming Telegram media into local storage and the warehouse DB."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict

from kolobot.file_store import FileStore
from kolobot.warehouse_db import WarehouseDB

logger = logging.getLogger(__name__)

QUEUED_MESSAGE_TEMPLATE = "📥 Збережено. В черзі (#{doc_id})"


@dataclass
class IntakeResult:
    doc_id: int
    file_path: str
    filename: str
    file_type: str
    message: str


class DocumentIntakeService:
    """
    Deep module for media intake: pull the file bytes from Telegram at once,
    persist them locally and register the document as `queued` so it is
    visible in the web panel before OCR starts.
    """

    def __init__(
        self,
        file_store: FileStore,
        warehouse_db: WarehouseDB,
    ) -> None:
        self._fs = file_store
        self._db = warehouse_db

    async def accept(self, intake: Dict[str, Any], bot: Any) -> IntakeResult:
        raw = await bot.download(intake["file_id"])
        data = raw.read() if hasattr(raw, "read") else raw
        if not data:
            raise ValueError(f"Empty download for file_id={intake['file_id']}")

        ext = intake.get("ext") or ".jpg"
        file_path = self._fs.save_tmp(data, ext=ext)

        mime = intake.get("mime") or "image/jpeg"
        file_type = "photo" if mime.startswith("image/") else "pdf"
        filename = intake.get("file_name") or file_path.replace("\\", "/").rsplit("/", 1)[-1]

        doc_id = self._db.add_document(
            filename=filename,
            file_type=file_type,
            file_path=file_path,
            status="queued",
            file_id=intake.get("file_id", ""),
            chat_id=intake.get("chat_id", 0),
            user_id=intake.get("user_id", 0),
        )
        logger.info("Intake accepted file_id=%s as queued document #%d", intake["file_id"], doc_id)

        return IntakeResult(
            doc_id=doc_id,
            file_path=file_path,
            filename=filename,
            file_type=file_type,
            message=QUEUED_MESSAGE_TEMPLATE.format(doc_id=doc_id),
        )

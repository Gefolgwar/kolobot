"""Sending an archived original back to Telegram.

One file, two ways out: the stored ``telegram_file_id`` first, the local
copy under ``downloads/`` as the fallback. Nothing here knows about
routing or queueing - callers hand it a message and the archive metadata.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram.types import FSInputFile, Message

from kolobot.file_store import FileStore, _ext_from_mime


logger = logging.getLogger(__name__)


async def send_archive_file(
    message: Message,
    file_store: FileStore,
    doc_id: str,
    metadata: dict[str, Any],
    error_text: str = "Не вдалося надіслати файл.",
) -> bool:
    """
    Send an archived document or photo to Telegram.
    Tries telegram_file_id first (answer_photo for photos, answer_document for documents).
    Falls back to local storage using FSInputFile if file_id is invalid, expired, or missing.
    Reports failure only if both methods fail.
    """
    fid = metadata.get("telegram_file_id") or ""
    source = metadata.get("source") or ""
    mime = metadata.get("mime") or ""

    if fid:
        try:
            if source == "photo":
                await message.answer_photo(fid)
            else:
                await message.answer_document(fid)
            return True
        except Exception as exc:
            logger.warning("Failed to send via telegram_file_id=%s: %s", fid, exc)

    ext = _ext_from_mime(mime)
    file_path = file_store.get_final_path(doc_id, ext)
    if not file_path:
        for candidate in (".jpg", ".png", ".webp"):
            if candidate != ext:
                file_path = file_store.get_final_path(doc_id, candidate)
                if file_path:
                    break

    if file_path:
        try:
            input_file = FSInputFile(file_path)
            if source == "photo":
                await message.answer_photo(input_file)
            else:
                await message.answer_document(input_file)
            return True
        except Exception as exc:
            logger.warning("Failed to send local file %s via FSInputFile: %s", file_path, exc)

    await message.answer(error_text)
    return False

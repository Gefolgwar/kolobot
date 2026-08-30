"""Media intake handler: image-only, album reject, single-flight."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from kolobot.file_store import FileStore

ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_FILE_SIZE = 20_000_000


class MediaHandler:
    """
    Accept owner photos and image documents, reject albums/non-images/oversize.
    Enforce single-flight: one pending confirm at a time.
    """

    def __init__(self, file_store: FileStore, owner_user_id: int) -> None:
        self._file_store = file_store
        self._owner = owner_user_id
        self._pending: bool = False
        self._album_seen: Dict[str, float] = {}
        self._album_debounce = 3.0

    async def handle_media(self, message: Any) -> Optional[Dict[str, Any]]:
        if getattr(message, "media_group_id", None):
            return await self._reject_album(message)

        if self._pending:
            await message.answer(
                "Спочатку заверши поточний документ — "
                "Зберегти або Відхилити."
            )
            return None

        photo = getattr(message, "photo", None)
        doc = getattr(message, "document", None)

        if photo:
            best = max(photo, key=lambda p: getattr(p, "file_size", 0) or 0)
            file_id = best.file_id
            file_unique_id = best.file_unique_id
            file_size = getattr(best, "file_size", 0) or 0
            mime = "image/jpeg"
            file_name = None
            ext = ".jpg"
        elif doc:
            mime = getattr(doc, "mime_type", "") or ""
            if mime not in ALLOWED_MIMES:
                await message.answer(
                    "Підтримуються лише зображення (jpeg, png, webp) та PDF документи."
                )
                return None
            file_id = doc.file_id
            file_unique_id = doc.file_unique_id
            file_size = getattr(doc, "file_size", 0) or 0
            file_name = getattr(doc, "file_name", None)
            ext = _ext_from_mime(mime)
        else:
            return None

        if file_size > MAX_FILE_SIZE:
            await message.answer(
                "Файл завеликий (>20 МБ). Надішли менше зображення."
            )
            return None

        self._pending = True
        tmp_path = self._file_store.save_tmp(b"", ext=ext)

        return {
            "file_id": file_id,
            "file_unique_id": file_unique_id,
            "file_size": file_size,
            "mime": mime,
            "file_name": file_name,
            "ext": ext,
            "tmp_path": tmp_path,
            "source": "photo" if photo else "document",
        }

    def clear_pending(self) -> None:
        self._pending = False

    @property
    def is_pending(self) -> bool:
        return self._pending

    async def _reject_album(self, message: Any) -> None:
        gid = message.media_group_id
        now = time.time()
        last = self._album_seen.get(gid, 0)
        if now - last > self._album_debounce:
            self._album_seen[gid] = now
            await message.answer(
                "Надсилай по одному зображенню за раз, без альбомів."
            )
        return None


def _ext_from_mime(mime: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }.get(mime, ".jpg")

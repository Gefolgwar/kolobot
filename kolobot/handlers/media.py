"""Media intake handler: accepts photos, image documents, PDFs, and media albums."""

from __future__ import annotations

from typing import Any, Dict, Optional

ALLOWED_MIMES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_FILE_SIZE = 20_000_000


class MediaHandler:
    """
    Accept owner photos, image documents, PDFs, and media albums.
    Validates MIME type and file size (<20MB) and normalizes file metadata.
    """

    def __init__(self, owner_user_id: int) -> None:
        self._owner = owner_user_id

    async def handle_media(self, message: Any) -> Optional[Dict[str, Any]]:
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

        return {
            "file_id": file_id,
            "file_unique_id": file_unique_id,
            "file_size": file_size,
            "mime": mime,
            "file_name": file_name,
            "ext": ext,
            "source": "photo" if photo else "document",
        }

    def clear_pending(self) -> None:
        """Compatibility no-op (single-flight is deprecated in favor of DocumentQueueService)."""
        pass

    @property
    def is_pending(self) -> bool:
        """Compatibility property."""
        return False


def _ext_from_mime(mime: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "application/pdf": ".pdf",
    }.get(mime, ".jpg")

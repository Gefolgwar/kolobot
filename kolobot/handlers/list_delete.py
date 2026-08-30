"""/list + /delete handler: list recent, delete cascade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from kolobot.file_store import FileStore
from kolobot.vector_store import VectorStore


@dataclass
class DeleteResult:
    success: bool
    error: str = ""


class ListDeleteHandler:
    """List latest docs, delete with Chroma + disk cascade."""

    def __init__(
        self,
        vector_store: VectorStore,
        file_store: FileStore,
        owner_user_id: int,
    ) -> None:
        self._vs = vector_store
        self._fs = file_store
        self._owner = owner_user_id

    async def handle_list(self, message: Any, user_id: int) -> None:
        docs = self._vs.list_recent(user_id=user_id, limit=10)
        if not docs:
            await message.answer("Архів порожній — поки немає збережених документів.")
            return

        import html
        lines = ["<b>Останні документи:</b>\n"]
        for doc in docs:
            meta = doc["metadata"]
            name = meta.get("file_name") or doc["id"]
            safe_name = html.escape(str(name))
            lines.append(f"• <code>{doc['id']}</code> — {safe_name}")
        await message.answer("\n".join(lines))

    async def delete_doc(self, doc_id: str, user_id: int) -> DeleteResult:
        existing = self._vs.get(doc_id)
        if existing is None:
            return DeleteResult(success=False, error="Документ не знайдено.")

        self._vs.delete(doc_id)

        meta = existing.get("metadata", {})
        mime = meta.get("mime", "image/jpeg")
        ext = _ext_from_mime(mime)
        self._fs.delete_final(doc_id, ext=ext)

        return DeleteResult(success=True)


def _ext_from_mime(mime: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(mime, ".jpg")

"""ArchiveService: orchestrate save (embed → Chroma → disk) and dedup lookup."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from kolobot.file_store import FileStore
from kolobot.gemini_gateway import GeminiGateway
from kolobot.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class SaveResult:
    success: bool
    doc_id: str = ""
    disk_warning: bool = False
    error: str = ""


def _supports_status_update(fn: Any) -> bool:
    target = getattr(fn, "side_effect", None) or fn
    try:
        sig = inspect.signature(target)
        for param in sig.parameters.values():
            if param.kind == inspect.Parameter.VAR_KEYWORD or param.name == "on_status_update":
                return True
        return False
    except (ValueError, TypeError):
        return False


DEFAULT_SAVE_RETRY_DELAYS = (10.0, 30.0, 60.0)


class ArchiveService:
    """
    Orchestrate ingest: assign doc_id, embed (with exponential retry), upsert Chroma (SoT),
    best-effort promote disk.
    """

    def __init__(
        self,
        gateway: GeminiGateway,
        vector_store: VectorStore,
        file_store: FileStore,
        retry_delays: tuple[float, ...] = DEFAULT_SAVE_RETRY_DELAYS,
    ) -> None:
        self._gw = gateway
        self._vs = vector_store
        self._fs = file_store
        self._retry_delays = tuple(float(d) for d in retry_delays)

    async def save(
        self,
        *,
        title: str,
        summary: str,
        key_value_pairs: List[Dict[str, str]],
        raw_text: str,
        tmp_path: str,
        ext: str,
        user_id: int,
        telegram_file_id: str,
        file_unique_id: str,
        file_name: Optional[str],
        mime: str,
        source: str,
        doc_number: str = "",
        doc_date: str = "",
        items: Optional[List[Dict[str, Any]]] = None,
        totals: Optional[Dict[str, Any]] = None,
        item_name: str = "",
        incoming: str = "",
        outgoing: str = "",
        balance: str = "",
        unit: str = "",
        supplier: str = "",
        notes: str = "",
        on_status_update: Optional[Callable[[str], Awaitable[None]]] = None,
    ) -> SaveResult:
        doc_id = uuid.uuid4().hex[:10]

        blob = self._build_blob(title, summary, key_value_pairs, raw_text, items, totals)

        max_retries = len(self._retry_delays)
        total_attempts = 1 + max_retries
        last_error = ""
        embedding = None

        for attempt in range(total_attempts):
            if attempt > 0:
                delay = self._retry_delays[attempt - 1]
                status_text = (
                    f"🔄 Помилка збереження. Спроба {attempt}/{max_retries}. "
                    f"Повтор через {int(delay)}с..."
                )
                if on_status_update:
                    try:
                        await on_status_update(status_text)
                    except Exception as exc:
                        logger.warning("Error in on_status_update callback: %s", exc)
                await asyncio.sleep(delay)

            try:
                emb_kwargs: Dict[str, Any] = {"texts": [blob]}
                if _supports_status_update(self._gw.embed_texts):
                    emb_kwargs["on_status_update"] = on_status_update

                embeddings = await self._gw.embed_texts(**emb_kwargs)
                if embeddings and len(embeddings) > 0 and len(embeddings[0]) > 0:
                    embedding = embeddings[0]
                    break
                else:
                    raise ValueError("Embeddings returned empty result")
            except Exception as exc:
                last_error = str(exc)
                if attempt < max_retries:
                    logger.warning(
                        "Attempt %d/%d to embed document %s failed: %s. Retrying...",
                        attempt + 1,
                        total_attempts,
                        doc_id,
                        exc,
                    )
                else:
                    logger.error(
                        "All %d attempts to embed document %s exhausted: %s",
                        total_attempts,
                        doc_id,
                        exc,
                    )

        if embedding is None:
            return SaveResult(success=False, doc_id=doc_id, error=last_error)

        structured = {
            "doc_number": doc_number,
            "doc_date": doc_date,
            "items": items or [],
            "totals": totals or {},
            "item_name": item_name,
            "incoming": incoming,
            "outgoing": outgoing,
            "balance": balance,
            "unit": unit,
            "supplier": supplier,
            "notes": notes,
        }
        total_with_vat = (totals or {}).get("total_with_vat", "")

        metadata: Dict[str, Any] = {
            "user_id": user_id,
            "telegram_file_id": telegram_file_id,
            "file_unique_id": file_unique_id,
            "file_name": file_name or "",
            "mime": mime,
            "source": source,
            "created_at": time.time(),
            "doc_number": doc_number,
            "doc_date": doc_date,
            "total_amount": total_with_vat,
            "structured_json": json.dumps(structured, ensure_ascii=False),
        }

        try:
            self._vs.upsert(
                doc_id=doc_id,
                document=blob,
                embedding=embedding,
                metadata=metadata,
            )
        except Exception as exc:
            return SaveResult(success=False, doc_id=doc_id, error=str(exc))

        disk_warning = False
        try:
            self._fs.promote(tmp_path, doc_id=doc_id, ext=ext)
            if raw_text:
                try:
                    self._fs.save_text(doc_id=doc_id, text=raw_text)
                except Exception:
                    pass
        except Exception:
            disk_warning = True

        return SaveResult(success=True, doc_id=doc_id, disk_warning=disk_warning)

    def lookup_duplicate(
        self, user_id: int, file_unique_id: str
    ) -> Optional[Dict[str, Any]]:
        return self._vs.find_by_file_unique_id(
            user_id=user_id, file_unique_id=file_unique_id
        )

    @staticmethod
    def _build_blob(
        title: str,
        summary: str,
        key_value_pairs: List[Dict[str, str]],
        raw_text: str,
        items: Optional[List[Dict[str, Any]]] = None,
        totals: Optional[Dict[str, Any]] = None,
    ) -> str:
        parts = []
        if title:
            parts.append(f"Title: {title}")
        if summary:
            parts.append(f"Summary: {summary}")
        for kv in key_value_pairs:
            parts.append(f"{kv['key']}: {kv['value']}")
        if items:
            parts.append("Items:")
            for it in items:
                parts.append(
                    f"  {it.get('num', '')}. {it.get('name', '')} | {it.get('quantity', '')} {it.get('unit', '')} | ціна: {it.get('price_no_vat', '')} | сума: {it.get('total_no_vat', '')}"
                )
        if totals:
            if totals.get("total_no_vat"):
                parts.append(f"Всього без ПДВ: {totals['total_no_vat']}")
            if totals.get("vat"):
                parts.append(f"ПДВ: {totals['vat']}")
            if totals.get("total_with_vat"):
                parts.append(f"Всього з ПДВ: {totals['total_with_vat']}")
        if raw_text:
            parts.append(raw_text)
        return "\n".join(parts)

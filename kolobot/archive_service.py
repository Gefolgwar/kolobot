"""ArchiveService: orchestrate save (embed → Chroma → disk) and dedup lookup."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from kolobot.file_store import FileStore
from kolobot.gemini_gateway import GeminiGateway
from kolobot.vector_store import VectorStore


@dataclass
class SaveResult:
    success: bool
    doc_id: str = ""
    disk_warning: bool = False
    error: str = ""


class ArchiveService:
    """
    Orchestrate ingest: assign doc_id, embed, upsert Chroma (SoT),
    best-effort promote disk.
    """

    def __init__(
        self,
        gateway: GeminiGateway,
        vector_store: VectorStore,
        file_store: FileStore,
    ) -> None:
        self._gw = gateway
        self._vs = vector_store
        self._fs = file_store

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
    ) -> SaveResult:
        doc_id = uuid.uuid4().hex[:10]

        blob = self._build_blob(title, summary, key_value_pairs, raw_text, items, totals)

        try:
            embeddings = await self._gw.embed_texts([blob])
            embedding = embeddings[0]
        except Exception as exc:
            return SaveResult(success=False, doc_id=doc_id, error=str(exc))

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

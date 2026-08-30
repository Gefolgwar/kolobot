"""RagService: embed query, short-circuit, cutoff, generate answer, source buttons."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from kolobot.gemini_gateway import GeminiGateway
from kolobot.vector_store import VectorStore

TRIVIAL_PATTERN = re.compile(
    r"^(\s*|ок|ok|дякую|дяка|спасибо|👍|👌|🙏|lol|ахах|хаха|ага|угу|ну|так|yes|no|ні)+$",
    re.IGNORECASE,
)

MAX_SOURCE_BUTTONS = 3


@dataclass
class RagResult:
    answer: str = ""
    sources: List[Dict[str, Any]] = field(default_factory=list)
    trivial: bool = False
    empty_archive: bool = False
    not_found: bool = False


class RagService:
    """
    Deep module: embed query → short-circuit empty/trivial → query →
    cutoff → generate answer → ≤3 source buttons.
    """

    def __init__(
        self,
        gateway: GeminiGateway,
        vector_store: VectorStore,
        *,
        top_k: int = 3,
        max_distance: float = 1.2,
    ) -> None:
        self._gw = gateway
        self._vs = vector_store
        self._top_k = top_k
        self._max_distance = max_distance

    async def answer(self, user_id: int, question: str) -> RagResult:
        if not question or TRIVIAL_PATTERN.match(question):
            return RagResult(trivial=True)

        if self._vs.count(user_id=user_id) == 0:
            return RagResult(empty_archive=True)

        embeddings = await self._gw.embed_texts([question])
        query_emb = embeddings[0]

        hits = self._vs.query(
            user_id=user_id,
            query_embedding=query_emb,
            top_k=self._top_k,
        )

        good_hits = [h for h in hits if h["distance"] <= self._max_distance]
        if not good_hits:
            return RagResult(not_found=True)

        contexts = [h["document"] for h in good_hits]
        answer_text = await self._gw.answer_with_context(question, contexts)

        sources = self._dedupe_sources(good_hits)

        return RagResult(answer=answer_text, sources=sources)

    @staticmethod
    def _dedupe_sources(hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        result = []
        for hit in hits:
            uid = hit["metadata"].get("file_unique_id", hit["id"])
            if uid in seen:
                continue
            seen.add(uid)
            result.append({
                "doc_id": hit["id"],
                "telegram_file_id": hit["metadata"].get("telegram_file_id", ""),
                "file_unique_id": uid,
            })
            if len(result) >= MAX_SOURCE_BUTTONS:
                break
        return result

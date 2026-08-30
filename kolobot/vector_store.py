"""VectorStore: Chroma PersistentClient wrapper with user_id isolation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import chromadb


class VectorStore:
    """
    Deep module: upsert/get/query/list_recent/delete/count/find_by_file_unique_id.
    Chroma PersistentClient; always filter by user_id.
    """

    COLLECTION = "kolobot_archive"

    def __init__(self, chroma_path: str) -> None:
        self._client = chromadb.PersistentClient(path=chroma_path)
        self._col = self._client.get_or_create_collection(
            name=self.COLLECTION,
            metadata={"hnsw:space": "l2"},
        )

    def upsert(
        self,
        doc_id: str,
        document: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        try:
            self._col.upsert(
                ids=[doc_id],
                documents=[document],
                embeddings=[embedding],
                metadatas=[metadata],
            )
        except Exception as exc:
            if "dimension" in str(exc).lower():
                if self._col.count() == 0:
                    self._client.delete_collection(self.COLLECTION)
                    self._col = self._client.create_collection(
                        name=self.COLLECTION,
                        metadata={"hnsw:space": "l2"},
                    )
                    self._col.upsert(
                        ids=[doc_id],
                        documents=[document],
                        embeddings=[embedding],
                        metadatas=[metadata],
                    )
                    return
            raise

    def get(self, doc_id: str) -> Optional[Dict[str, Any]]:
        result = self._col.get(ids=[doc_id], include=["documents", "metadatas"])
        if not result["ids"]:
            return None
        return {
            "id": result["ids"][0],
            "document": result["documents"][0],
            "metadata": result["metadatas"][0],
        }

    def delete(self, doc_id: str) -> None:
        try:
            self._col.delete(ids=[doc_id])
        except Exception:
            pass

    def count(self, user_id: int) -> int:
        result = self._col.get(
            where={"user_id": user_id},
            include=[],
        )
        return len(result["ids"])

    def list_recent(
        self, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        result = self._col.get(
            where={"user_id": user_id},
            include=["documents", "metadatas"],
        )
        items = []
        for i, doc_id in enumerate(result["ids"]):
            items.append({
                "id": doc_id,
                "document": result["documents"][i],
                "metadata": result["metadatas"][i],
            })
        items.sort(key=lambda x: x["metadata"].get("created_at", 0), reverse=True)
        return items[:limit]

    def list_all_ids(self, user_id: int) -> List[str]:
        result = self._col.get(
            where={"user_id": user_id},
            include=[],
        )
        return result["ids"]

    def find_by_file_unique_id(
        self, user_id: int, file_unique_id: str
    ) -> Optional[Dict[str, Any]]:
        result = self._col.get(
            where={"$and": [{"user_id": user_id}, {"file_unique_id": file_unique_id}]},
            include=["documents", "metadatas"],
        )
        if not result["ids"]:
            return None
        return {
            "id": result["ids"][0],
            "document": result["documents"][0],
            "metadata": result["metadatas"][0],
        }

    def query(
        self,
        user_id: int,
        query_embedding: List[float],
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        n = self.count(user_id)
        if n == 0:
            return []
        actual_k = min(top_k, n)
        result = self._col.query(
            query_embeddings=[query_embedding],
            n_results=actual_k,
            where={"user_id": user_id},
            include=["documents", "metadatas", "distances"],
        )
        items = []
        for i, doc_id in enumerate(result["ids"][0]):
            items.append({
                "id": doc_id,
                "document": result["documents"][0][i],
                "metadata": result["metadatas"][0][i],
                "distance": result["distances"][0][i],
            })
        return items

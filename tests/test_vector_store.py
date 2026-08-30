"""VectorStore: upsert, get, query, list_recent, delete, find_by_file_unique_id."""

from __future__ import annotations

import time

import pytest

from kolobot.vector_store import VectorStore


@pytest.fixture
def store(tmp_path) -> VectorStore:
    return VectorStore(chroma_path=str(tmp_path / "chroma"))


def test_upsert_and_get(store: VectorStore):
    store.upsert(
        doc_id="d001",
        document="some text",
        embedding=[0.1] * 768,
        metadata={"user_id": 42, "telegram_file_id": "fid1", "file_unique_id": "uid1", "created_at": 1000.0},
    )
    doc = store.get("d001")
    assert doc is not None
    assert doc["id"] == "d001"
    assert doc["document"] == "some text"
    assert doc["metadata"]["user_id"] == 42


def test_get_missing_returns_none(store: VectorStore):
    assert store.get("nonexistent") is None


def test_delete_removes_record(store: VectorStore):
    store.upsert(
        doc_id="d002",
        document="bye",
        embedding=[0.2] * 768,
        metadata={"user_id": 42, "telegram_file_id": "fid2", "file_unique_id": "uid2", "created_at": 2000.0},
    )
    store.delete("d002")
    assert store.get("d002") is None


def test_delete_missing_no_error(store: VectorStore):
    store.delete("ghost")


def test_list_recent_returns_limit_ordered(store: VectorStore):
    for i in range(15):
        store.upsert(
            doc_id=f"d{i:03}",
            document=f"doc {i}",
            embedding=[float(i) / 100] * 768,
            metadata={"user_id": 42, "telegram_file_id": f"fid{i}", "file_unique_id": f"uid{i}", "created_at": float(1000 + i)},
        )
    recent = store.list_recent(user_id=42, limit=10)
    assert len(recent) == 10
    timestamps = [r["metadata"]["created_at"] for r in recent]
    assert timestamps == sorted(timestamps, reverse=True)


def test_find_by_file_unique_id(store: VectorStore):
    store.upsert(
        doc_id="d010",
        document="found me",
        embedding=[0.5] * 768,
        metadata={"user_id": 42, "telegram_file_id": "fid10", "file_unique_id": "target_uid", "created_at": 5000.0},
    )
    result = store.find_by_file_unique_id(user_id=42, file_unique_id="target_uid")
    assert result is not None
    assert result["id"] == "d010"


def test_find_by_file_unique_id_missing(store: VectorStore):
    assert store.find_by_file_unique_id(user_id=42, file_unique_id="nope") is None


def test_count(store: VectorStore):
    assert store.count(user_id=42) == 0
    store.upsert(
        doc_id="d100",
        document="x",
        embedding=[0.0] * 768,
        metadata={"user_id": 42, "telegram_file_id": "f", "file_unique_id": "u", "created_at": 1.0},
    )
    assert store.count(user_id=42) == 1


def test_query_returns_results_with_distances(store: VectorStore):
    store.upsert(
        doc_id="d200",
        document="machine learning overview",
        embedding=[1.0] + [0.0] * 767,
        metadata={"user_id": 42, "telegram_file_id": "f200", "file_unique_id": "u200", "created_at": 1.0},
    )
    results = store.query(
        user_id=42,
        query_embedding=[1.0] + [0.0] * 767,
        top_k=3,
    )
    assert len(results) >= 1
    assert "distance" in results[0]
    assert results[0]["id"] == "d200"

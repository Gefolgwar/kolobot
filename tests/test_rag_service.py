"""RagService: empty, cutoff, trivial, source dedupe ≤3."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from kolobot.rag_service import RagService, RagResult


@pytest.fixture
def deps():
    gateway = AsyncMock()
    gateway.embed_texts = AsyncMock(return_value=[[0.5] * 768])
    gateway.answer_with_context = AsyncMock(return_value="Сума 1234 грн.")
    vector_store = MagicMock()
    vector_store.count = MagicMock(return_value=5)
    vector_store.query = MagicMock(return_value=[
        {"id": "d1", "document": "doc1 text", "metadata": {"telegram_file_id": "fid1", "file_unique_id": "u1"}, "distance": 0.3},
        {"id": "d2", "document": "doc2 text", "metadata": {"telegram_file_id": "fid2", "file_unique_id": "u2"}, "distance": 0.5},
        {"id": "d3", "document": "doc3 text", "metadata": {"telegram_file_id": "fid1", "file_unique_id": "u1"}, "distance": 0.6},
    ])
    return gateway, vector_store


@pytest.fixture
def service(deps):
    gw, vs = deps
    return RagService(gateway=gw, vector_store=vs, top_k=3, max_distance=1.0)


@pytest.mark.asyncio
async def test_successful_rag_returns_answer_and_sources(service, deps):
    result = await service.answer(user_id=42, question="Яка сума?")
    assert result.answer == "Сума 1234 грн."
    assert len(result.sources) <= 3


@pytest.mark.asyncio
async def test_source_buttons_deduped_by_file_unique_id(service, deps):
    result = await service.answer(user_id=42, question="test")
    file_uids = [s["file_unique_id"] for s in result.sources]
    assert len(file_uids) == len(set(file_uids))
    assert len(result.sources) == 2  # fid1/u1 and fid2/u2


@pytest.mark.asyncio
async def test_empty_archive_short_circuits(deps):
    gw, vs = deps
    vs.count.return_value = 0
    svc = RagService(gateway=gw, vector_store=vs, top_k=3, max_distance=1.0)
    result = await svc.answer(user_id=42, question="anything")
    assert result.empty_archive
    gw.embed_texts.assert_not_awaited()
    gw.answer_with_context.assert_not_awaited()


@pytest.mark.asyncio
async def test_hard_distance_cutoff_yields_not_found(deps):
    gw, vs = deps
    vs.query.return_value = [
        {"id": "d1", "document": "far", "metadata": {"telegram_file_id": "f", "file_unique_id": "u"}, "distance": 2.5},
    ]
    svc = RagService(gateway=gw, vector_store=vs, top_k=3, max_distance=1.0)
    result = await svc.answer(user_id=42, question="test")
    assert result.not_found
    gw.answer_with_context.assert_not_awaited()


@pytest.mark.asyncio
async def test_trivial_messages_ignored():
    gw = AsyncMock()
    vs = MagicMock()
    svc = RagService(gateway=gw, vector_store=vs, top_k=3, max_distance=1.0)
    for trivial in ["ок", "дякую", "👍", "  ", ""]:
        result = await svc.answer(user_id=42, question=trivial)
        assert result.trivial
    gw.embed_texts.assert_not_awaited()


@pytest.mark.asyncio
async def test_max_3_sources_even_with_more_results(deps):
    gw, vs = deps
    vs.query.return_value = [
        {"id": f"d{i}", "document": f"doc{i}", "metadata": {"telegram_file_id": f"fid{i}", "file_unique_id": f"u{i}"}, "distance": 0.1 * i}
        for i in range(5)
    ]
    svc = RagService(gateway=gw, vector_store=vs, top_k=5, max_distance=2.0)
    result = await svc.answer(user_id=42, question="test")
    assert len(result.sources) <= 3

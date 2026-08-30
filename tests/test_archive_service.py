"""ArchiveService: save ordering embed→Chroma→disk, failure modes."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from kolobot.archive_service import ArchiveService, SaveResult


@pytest.fixture
def deps():
    gateway = AsyncMock()
    gateway.embed_texts = AsyncMock(return_value=[[0.1] * 768])
    vector_store = MagicMock()
    file_store = MagicMock()
    file_store.promote = MagicMock(return_value="/dl/abc123.jpg")
    return gateway, vector_store, file_store


@pytest.fixture
def service(deps):
    gateway, vector_store, file_store = deps
    return ArchiveService(
        gateway=gateway,
        vector_store=vector_store,
        file_store=file_store,
        retry_delays=(),
    )


@pytest.mark.asyncio
async def test_save_success_calls_embed_then_chroma_then_disk(service, deps):
    gateway, vector_store, file_store = deps
    call_order = []
    gateway.embed_texts.side_effect = lambda *a, **kw: (
        call_order.append("embed") or [[0.1] * 768]
    )
    vector_store.upsert.side_effect = lambda **kw: call_order.append("chroma")
    file_store.promote.side_effect = lambda *a, **kw: (
        call_order.append("disk") or "/dl/x.jpg"
    )

    result = await service.save(
        title="Test",
        summary="Sum",
        key_value_pairs=[],
        raw_text="raw",
        tmp_path="/tmp/x.jpg",
        ext=".jpg",
        user_id=42,
        telegram_file_id="fid",
        file_unique_id="uid",
        file_name="img.jpg",
        mime="image/jpeg",
        source="photo",
    )

    assert result.success
    assert result.doc_id
    assert call_order == ["embed", "chroma", "disk"]


@pytest.mark.asyncio
async def test_save_disk_failure_still_success_with_warning(service, deps):
    gateway, vector_store, file_store = deps
    file_store.promote.side_effect = OSError("disk full")

    result = await service.save(
        title="Test",
        summary="Sum",
        key_value_pairs=[],
        raw_text="raw",
        tmp_path="/tmp/x.jpg",
        ext=".jpg",
        user_id=42,
        telegram_file_id="fid",
        file_unique_id="uid",
        file_name=None,
        mime="image/jpeg",
        source="photo",
    )

    assert result.success
    assert result.disk_warning


@pytest.mark.asyncio
async def test_save_embed_failure_is_hard_fail(service, deps):
    gateway, vector_store, file_store = deps
    gateway.embed_texts.side_effect = RuntimeError("embed failed")

    result = await service.save(
        title="Test",
        summary="Sum",
        key_value_pairs=[],
        raw_text="raw",
        tmp_path="/tmp/x.jpg",
        ext=".jpg",
        user_id=42,
        telegram_file_id="fid",
        file_unique_id="uid",
        file_name=None,
        mime="image/jpeg",
        source="photo",
    )

    assert not result.success
    assert not result.disk_warning
    vector_store.upsert.assert_not_called()
    file_store.promote.assert_not_called()


@pytest.mark.asyncio
async def test_save_chroma_failure_is_hard_fail_no_promote(service, deps):
    gateway, vector_store, file_store = deps
    vector_store.upsert.side_effect = RuntimeError("chroma down")

    result = await service.save(
        title="Test",
        summary="Sum",
        key_value_pairs=[],
        raw_text="raw",
        tmp_path="/tmp/x.jpg",
        ext=".jpg",
        user_id=42,
        telegram_file_id="fid",
        file_unique_id="uid",
        file_name=None,
        mime="image/jpeg",
        source="photo",
    )

    assert not result.success
    file_store.promote.assert_not_called()


@pytest.mark.asyncio
async def test_save_generates_doc_id(service, deps):
    result = await service.save(
        title="T",
        summary="S",
        key_value_pairs=[],
        raw_text="r",
        tmp_path="/tmp/x.jpg",
        ext=".jpg",
        user_id=42,
        telegram_file_id="fid",
        file_unique_id="uid",
        file_name=None,
        mime="image/jpeg",
        source="photo",
    )
    assert result.doc_id
    assert 8 <= len(result.doc_id) <= 12


@pytest.mark.asyncio
async def test_lookup_duplicate_delegates_to_vector_store(deps):
    gateway, vector_store, file_store = deps
    vector_store.find_by_file_unique_id.return_value = {"id": "d001", "document": "x", "metadata": {}}
    svc = ArchiveService(gateway=gateway, vector_store=vector_store, file_store=file_store)
    found = svc.lookup_duplicate(user_id=42, file_unique_id="uid1")
    assert found is not None
    assert found["id"] == "d001"


@pytest.mark.asyncio
async def test_lookup_duplicate_returns_none_when_missing(deps):
    gateway, vector_store, file_store = deps
    vector_store.find_by_file_unique_id.return_value = None
    svc = ArchiveService(gateway=gateway, vector_store=vector_store, file_store=file_store)
    assert svc.lookup_duplicate(user_id=42, file_unique_id="nope") is None


@pytest.mark.asyncio
async def test_save_retry_success_after_transient_failures(deps):
    gateway, vector_store, file_store = deps
    attempts = 0

    async def flaky_embed(texts):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError(f"Embedding transient error attempt {attempts}")
        return [[0.1] * 768]

    gateway.embed_texts = AsyncMock(side_effect=flaky_embed)
    status_updates = []

    async def on_status_update(txt: str):
        status_updates.append(txt)

    svc = ArchiveService(
        gateway=gateway,
        vector_store=vector_store,
        file_store=file_store,
        retry_delays=(0.01, 0.02, 0.03),
    )

    result = await svc.save(
        title="Retry Test",
        summary="Sum",
        key_value_pairs=[],
        raw_text="raw",
        tmp_path="/tmp/x.jpg",
        ext=".jpg",
        user_id=42,
        telegram_file_id="fid",
        file_unique_id="uid",
        file_name="img.jpg",
        mime="image/jpeg",
        source="photo",
        on_status_update=on_status_update,
    )

    assert result.success is True
    assert attempts == 3
    assert len(status_updates) == 2
    assert "Спроба 1/3" in status_updates[0]
    assert "Спроба 2/3" in status_updates[1]
    vector_store.upsert.assert_called_once()
    file_store.promote.assert_called_once()


@pytest.mark.asyncio
async def test_save_retry_exhausted_failures_returns_error(deps):
    gateway, vector_store, file_store = deps
    error_msg = "Недійсний API ключ для ембеддінгів (GEMINI_KEYS_EMBED). Перевірте ключ у файлі .env."
    gateway.embed_texts = AsyncMock(side_effect=RuntimeError(error_msg))
    status_updates = []

    async def on_status_update(txt: str):
        status_updates.append(txt)

    svc = ArchiveService(
        gateway=gateway,
        vector_store=vector_store,
        file_store=file_store,
        retry_delays=(0.01, 0.02, 0.03),
    )

    result = await svc.save(
        title="Retry Fail Test",
        summary="Sum",
        key_value_pairs=[],
        raw_text="raw",
        tmp_path="/tmp/x.jpg",
        ext=".jpg",
        user_id=42,
        telegram_file_id="fid",
        file_unique_id="uid",
        file_name="img.jpg",
        mime="image/jpeg",
        source="photo",
        on_status_update=on_status_update,
    )

    assert result.success is False
    assert error_msg in result.error
    assert len(status_updates) == 3
    assert "Спроба 1/3" in status_updates[0]
    assert "Спроба 2/3" in status_updates[1]
    assert "Спроба 3/3" in status_updates[2]
    vector_store.upsert.assert_not_called()
    file_store.promote.assert_not_called()

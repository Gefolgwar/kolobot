"""DocumentIntakeService: immediate download, local save and `queued` registration."""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from kolobot.file_store import FileStore
from kolobot.intake_service import DocumentIntakeService
from kolobot.warehouse_db import WarehouseDB


@pytest.fixture
def intake_env(tmp_path):
    fs = FileStore(downloads_path=str(tmp_path / "downloads"))
    db = WarehouseDB(db_path=str(tmp_path / "warehouse.db"))
    db.init_db()
    try:
        yield fs, db
    finally:
        db.close()


def _bot(payload: bytes = b"image-bytes"):
    return SimpleNamespace(download=AsyncMock(return_value=payload))


def _photo_intake(**overrides):
    intake = {
        "file_id": "photo_fid_123",
        "file_unique_id": "photo_uid_123",
        "file_size": 11,
        "mime": "image/jpeg",
        "file_name": None,
        "ext": ".jpg",
        "source": "photo",
    }
    intake.update(overrides)
    return intake


@pytest.mark.asyncio
async def test_accept_saves_downloaded_bytes_to_storage(intake_env):
    fs, db = intake_env
    svc = DocumentIntakeService(file_store=fs, warehouse_db=db)
    bot = _bot(b"image-bytes")

    result = await svc.accept(_photo_intake(), bot)

    bot.download.assert_awaited_once_with("photo_fid_123")
    assert result.file_path
    assert os.path.exists(result.file_path)
    with open(result.file_path, "rb") as f:
        assert f.read() == b"image-bytes"


@pytest.mark.asyncio
async def test_accept_registers_document_as_queued_with_saved_file_path(intake_env):
    fs, db = intake_env
    svc = DocumentIntakeService(file_store=fs, warehouse_db=db)

    result = await svc.accept(_photo_intake(file_name="nakladna_1.jpg"), _bot())

    doc = db.get_document(result.doc_id)
    assert doc["status"] == "queued"
    assert doc["error_message"] == ""
    assert doc["filename"] == "nakladna_1.jpg"
    assert doc["file_type"] == "photo"
    assert doc["file_path"] == result.file_path
    assert os.path.exists(doc["file_path"])

    docs = db.get_documents()
    assert [d["id"] for d in docs] == [result.doc_id]
    assert docs[0]["status"] == "queued"


@pytest.mark.asyncio
async def test_accept_reports_queued_position_in_bot_message(intake_env):
    fs, db = intake_env
    svc = DocumentIntakeService(file_store=fs, warehouse_db=db)

    first = await svc.accept(_photo_intake(), _bot())
    second = await svc.accept(_photo_intake(file_id="photo_fid_456"), _bot())

    assert first.message == f"📥 Збережено. В черзі (#{first.doc_id})"
    assert second.message == f"📥 Збережено. В черзі (#{second.doc_id})"


@pytest.mark.asyncio
async def test_accept_treats_pdf_document_as_pdf(intake_env):
    fs, db = intake_env
    svc = DocumentIntakeService(file_store=fs, warehouse_db=db)

    result = await svc.accept(_photo_intake(
        file_id="doc_fid_789",
        mime="application/pdf",
        ext=".pdf",
        source="document",
        file_name="nakladna.pdf",
    ), _bot(b"%PDF-1.4"))

    doc = db.get_document(result.doc_id)
    assert doc["file_type"] == "pdf"
    assert doc["filename"] == "nakladna.pdf"
    assert doc["file_path"].endswith(".pdf")

"""Tests for the M-11 web tab and GET /api/warehouse/m11 endpoint (Issue #49)."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from kolobot.warehouse_db import WarehouseDB
from kolobot.web.assets import JS, PAGE
from kolobot.web_server import WebServer


@pytest.fixture
def warehouse_env(tmp_path):
    db_path = str(tmp_path / "warehouse.db")
    db = WarehouseDB(db_path=db_path)
    db.init_db()

    fs = MagicMock()
    fs._base = str(tmp_path)

    vs = MagicMock()
    vs.list_all_ids.return_value = []

    return db, fs, vs


@pytest.mark.asyncio
async def test_get_m11_empty(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/m11")
        assert resp.status == 200
        data = await resp.json()
        assert data == []
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_m11_only_returns_m11_documents(warehouse_env):
    db, fs, vs = warehouse_env

    # Add regular documents
    db.add_document(
        filename="nakladna.pdf",
        file_type="pdf",
        doc_type="НАКЛАДНА",
        doc_number="Н-101",
        doc_date="2026-03-01",
    )
    db.add_document(
        filename="vimoga.pdf",
        file_type="pdf",
        doc_type="ВИМОГА",
        doc_number="В-202",
        doc_date="2026-03-02",
    )
    # Add M-11 document
    m11_id = db.add_document(
        filename="m11_doc.pdf",
        file_type="pdf",
        doc_type="ВИМОГА М-11",
        doc_number="М11-001",
        doc_date="2026-03-03",
        requested_by="Іванов І.І.",
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/m11")
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["id"] == m11_id
        assert item["doc_number"] == "М11-001"
        assert item["doc_date"] == "2026-03-03"
        assert item["requested_by"] == "Іванов І.І."
        assert item["item_count"] == 0
        assert item["match_status"] == "none"
        assert item["linked_vimoga"] is None
        assert item["needs_review"] == 0
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_m11_with_items_and_linked_vimoga(warehouse_env):
    db, fs, vs = warehouse_env

    # Add classic vimoga
    vimoga_id = db.add_document(
        filename="classic_vimoga.pdf",
        file_type="pdf",
        doc_type="ВИМОГА",
        doc_number="В-777",
        doc_date="2026-03-10",
    )

    # Add M-11 document
    m11_id = db.add_document(
        filename="form_m11.pdf",
        file_type="pdf",
        doc_type="ВИМОГА М-11",
        doc_number="М11-999",
        doc_date="2026-03-11",
        requested_by="Петренко П.П.",
    )

    # Add M-11 items
    db.add_m11_item(document_id=m11_id, name="Кабель ВВГ", quantity=100.0, unit="м")
    db.add_m11_item(document_id=m11_id, name="Розетка", quantity=10.0, unit="шт")

    # Add link
    db.add_document_link(
        m11_doc_id=m11_id,
        vimoga_doc_id=vimoga_id,
        match_status="full",
        needs_review=0,
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/m11")
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["id"] == m11_id
        assert item["doc_number"] == "М11-999"
        assert item["doc_date"] == "2026-03-11"
        assert item["requested_by"] == "Петренко П.П."
        assert item["item_count"] == 2
        assert item["match_status"] == "full"
        assert item["needs_review"] == 0

        linked = item["linked_vimoga"]
        assert linked is not None
        assert linked["id"] == vimoga_id
        assert linked["number"] == "В-777"
        assert linked["doc_number"] == "В-777"
        assert linked["date"] == "2026-03-10"
        assert linked["doc_date"] == "2026-03-10"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_get_m11_with_conflict_needs_review(warehouse_env):
    db, fs, vs = warehouse_env

    vimoga_id = db.add_document(
        filename="vimoga_conflict.pdf",
        file_type="pdf",
        doc_type="ВИМОГА",
        doc_number="В-500",
        doc_date="2026-03-15",
    )

    m11_id = db.add_document(
        filename="m11_conflict.pdf",
        file_type="pdf",
        doc_type="ВИМОГА М-11",
        doc_number="М11-500",
        doc_date="2026-03-15",
    )

    db.add_document_link(
        m11_doc_id=m11_id,
        vimoga_doc_id=vimoga_id,
        match_status="partial",
        needs_review=1,
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/m11")
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["match_status"] == "partial"
        assert item["needs_review"] == 1
        assert item["linked_vimoga"]["id"] == vimoga_id
    finally:
        await client.close()


def test_m11_tab_navigation_in_shell():
    """Verify 'Вимоги М-11' tab button appears in navigation between 'Документи' and 'Log'."""
    docs_idx = PAGE.find('id="tab-documents"')
    m11_idx = PAGE.find('id="tab-m11"')
    logs_idx = PAGE.find('id="tab-logs"')

    assert docs_idx != -1, "tab-documents not found"
    assert m11_idx != -1, "tab-m11 not found"
    assert logs_idx != -1, "tab-logs not found"

    # Must be positioned between Документи and Log
    assert docs_idx < m11_idx < logs_idx, "tab-m11 must appear between tab-documents and tab-logs"

    # Tab contains text 'Вимоги М-11' and badge element
    tab_html = PAGE[m11_idx:logs_idx]
    assert "Вимоги М-11" in tab_html
    assert 'id="m11-badge"' in tab_html


def test_m11_panel_and_table_structure_in_page():
    """Verify panel-m11 container and required table columns exist in PAGE."""
    assert 'id="panel-m11"' in PAGE
    assert 'id="m11-tbody"' in PAGE

    # Verify table headers
    for th in ("№ М-11", "Дата", "Підстава/Кому", "Позицій", "Статус", "Пов'язана ВИМОГА", "Дії"):
        assert f">{th}</th>" in PAGE or f">{th} </th>" in PAGE


def test_m11_js_module_exists_and_reaches_page():
    """Verify 18-m11.js is loaded and includes essential functions."""
    assert "18-m11" in JS or "m11" in JS
    js_content = JS.get("18-m11", JS.get("m11", ""))
    assert "fetchM11Docs" in js_content
    assert "renderM11Table" in js_content
    assert "isM11Problematic" in js_content
    assert "updateM11Badge" in js_content
    assert "renderM11Status" in js_content
    assert "renderLinkedVimoga" in js_content

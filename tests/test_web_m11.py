"""Tests for the M-11 web tab and GET /api/warehouse/m11 endpoint (Issue #49)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
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
    """Verify panel-m11 container, chevron column, restructured headers, and colspan in PAGE."""
    assert 'id="panel-m11"' in PAGE
    assert 'id="m11-tbody"' in PAGE

    # Chevron header exists as first column
    assert '<th class="py-3 px-3 w-14"></th>' in PAGE

    # Verify restructured table headers: Статус (OCR) and Збіг (matching)
    for th in ("№ М-11", "Дата", "Підстава/Кому", "Позицій", "Статус", "Збіг", "Пов'язана ВИМОГА", "Дії"):
        assert f">{th}</th>" in PAGE or f">{th} </th>" in PAGE

    # Verify empty state row has colspan 9
    assert 'colspan="9"' in PAGE


def test_m11_js_module_exists_and_reaches_page():
    """Verify 18-m11.js is loaded and includes essential functions and accordion support."""
    assert "18-m11" in JS or "m11" in JS
    js_content = JS.get("18-m11", JS.get("m11", ""))
    assert "fetchM11Docs" in js_content
    assert "renderM11Table" in js_content
    assert "toggleM11Accordion" in js_content
    assert "isM11Problematic" in js_content
    assert "updateM11Badge" in js_content
    assert "renderM11Status" in js_content
    assert "renderLinkedVimoga" in js_content
    assert "confirmM11Link" in js_content
    assert "unbindM11Link" in js_content
    assert "openBindModal" in js_content
    assert "closeBindModal" in js_content
    assert "selectVimogaForBind" in js_content
    assert "filterAvailableVimogas" in js_content

    # Accordion markers in JS render
    assert "m11-chevron-" in js_content
    assert "m11-impact-row-" in js_content
    assert "m11-impact-content-" in js_content
    assert "docStatusBadge(doc)" in js_content
    assert 'colspan="9"' in js_content
    assert "event.stopPropagation()" in js_content


NODE = shutil.which("node")


@pytest.mark.skipif(not NODE, reason="node not available")
def test_render_m11_status_badges():
    """Verify renderM11Status outputs green checkmarks for full and manual, suppressed on review."""
    m11_js = JS.get("18-m11", JS.get("m11", ""))
    script = f"""
    let switchTab = () => {{}};
    let refreshAll = () => {{}};
    let document = {{ getElementById: () => ({{ classList: {{ add() {{}}, remove() {{}} }} }}) }};
    {m11_js}
    const full = renderM11Status({{ match_status: "full", needs_review: 0 }});
    const manual = renderM11Status({{ match_status: "manual", needs_review: 0 }});
    const manualReview = renderM11Status({{ match_status: "manual", needs_review: 1 }});
    const fullReview = renderM11Status({{ match_status: "full", needs_review: 1 }});
    const partial = renderM11Status({{ match_status: "partial", needs_review: 0 }});
    const none = renderM11Status({{ match_status: "none", needs_review: 0 }});
    console.log(JSON.stringify({{ full, manual, manualReview, fullReview, partial, none }}));
    """
    proc = subprocess.run([NODE, "-e", script], capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)

    # 1. Full status: green checkmark
    assert "fa-check" in data["full"]
    assert "text-emerald-400" in data["full"]
    assert "Повний" in data["full"]

    # 2. Manual status: green checkmark
    assert "fa-check" in data["manual"]
    assert "text-emerald-400" in data["manual"]
    assert "Вручну" in data["manual"]
    assert "fa-link" not in data["manual"]

    # 3. Manual with needs_review: suppressed checkmark, amber warning shown
    assert "fa-check" not in data["manualReview"]
    assert "fa-triangle-exclamation" in data["manualReview"]
    assert "text-amber-400" in data["manualReview"]
    assert "Потребує перевірки" in data["manualReview"]

    # 4. Full with needs_review: suppressed checkmark, amber warning shown
    assert "fa-check" not in data["fullReview"]
    assert "fa-triangle-exclamation" in data["fullReview"]
    assert "text-amber-400" in data["fullReview"]

    # 5. Partial status: amber exclamation, no checkmark
    assert "fa-check" not in data["partial"]
    assert "fa-exclamation" in data["partial"]
    assert "text-amber-400" in data["partial"]
    assert "Частковий" in data["partial"]

    # 6. None status: rose circle, no checkmark
    assert "fa-check" not in data["none"]
    assert "fa-circle" in data["none"]
    assert "text-rose-400" in data["none"]
    assert "Без збігу" in data["none"]


def test_m11_bind_modal_in_page():
    """Verify manual bind modal markup exists in PAGE."""
    assert 'id="m11-bind-modal"' in PAGE
    assert 'id="m11-bind-search"' in PAGE
    assert 'id="m11-bind-list"' in PAGE


@pytest.mark.asyncio
async def test_api_confirm_link(warehouse_env):
    """POST /api/m11/links/{link_id}/confirm sets match_status=full and needs_review=0."""
    db, fs, vs = warehouse_env

    m11_id = db.add_document(filename="m11.pdf", file_type="pdf", doc_type="ВИМОГА М-11")
    vimoga_id = db.add_document(filename="v.pdf", file_type="pdf", doc_type="ВИМОГА")
    link_id = db.add_document_link(
        m11_doc_id=m11_id,
        vimoga_doc_id=vimoga_id,
        match_status="partial",
        needs_review=1,
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # Success
        resp = await client.post(f"/api/m11/links/{link_id}/confirm")
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["match_status"] == "full"
        assert data["needs_review"] == 0

        # DB updated
        link = db.get_document_link(link_id)
        assert link["match_status"] == "full"
        assert link["needs_review"] == 0

        # 404 for unknown link
        resp404 = await client.post("/api/m11/links/999999/confirm")
        assert resp404.status == 404

        # 400 for invalid id
        resp400 = await client.post("/api/m11/links/abc/confirm")
        assert resp400.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_api_delete_link(warehouse_env):
    """DELETE /api/m11/links/{link_id} unbinds documents and deletes the link."""
    db, fs, vs = warehouse_env

    m11_id = db.add_document(
        filename="m11.pdf", file_type="pdf", doc_type="ВИМОГА М-11", doc_number="М11-01"
    )
    vimoga_id = db.add_document(
        filename="v.pdf", file_type="pdf", doc_type="ВИМОГА", doc_number="В-01"
    )
    link_id = db.add_document_link(
        m11_doc_id=m11_id,
        vimoga_doc_id=vimoga_id,
        match_status="partial",
        needs_review=1,
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # Success
        resp = await client.delete(f"/api/m11/links/{link_id}")
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True

        # DB record removed
        assert db.get_document_link(link_id) is None

        # M-11 is now unlinked in warehouse list
        m11_resp = await client.get("/api/warehouse/m11")
        m11_docs = await m11_resp.json()
        assert len(m11_docs) == 1
        assert m11_docs[0]["match_status"] == "none"
        assert m11_docs[0]["linked_vimoga"] is None
        assert m11_docs[0]["link_id"] is None

        # 404 for already deleted or nonexistent
        resp404 = await client.delete(f"/api/m11/links/{link_id}")
        assert resp404.status == 404

        # 400 for bad id
        resp400 = await client.delete("/api/m11/links/invalid")
        assert resp400.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_api_bind_manually(warehouse_env):
    """POST /api/m11/{doc_id}/bind links M-11 to vimoga with match_status=manual."""
    db, fs, vs = warehouse_env

    m11_id = db.add_document(
        filename="m11.pdf", file_type="pdf", doc_type="ВИМОГА М-11", doc_number="М11-100"
    )
    vimoga_id = db.add_document(
        filename="v.pdf", file_type="pdf", doc_type="ВИМОГА", doc_number="В-200"
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # Success
        resp = await client.post(
            f"/api/m11/{m11_id}/bind",
            json={"vimoga_doc_id": vimoga_id},
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["m11_doc_id"] == m11_id
        assert data["vimoga_doc_id"] == vimoga_id
        assert data["match_status"] == "manual"
        link_id = data["link_id"]

        # Check DB
        link = db.get_document_link(link_id)
        assert link["match_status"] == "manual"
        assert link["needs_review"] == 0

        # Check warehouse list
        m11_resp = await client.get("/api/warehouse/m11")
        m11_docs = await m11_resp.json()
        assert m11_docs[0]["match_status"] == "manual"
        assert m11_docs[0]["linked_vimoga"]["id"] == vimoga_id
        assert m11_docs[0]["linked_vimoga"]["doc_number"] == "В-200"

        # 404 for unknown M-11 doc
        resp_nom11 = await client.post(
            "/api/m11/999999/bind",
            json={"vimoga_doc_id": vimoga_id},
        )
        assert resp_nom11.status == 404

        # 404 for unknown vimoga doc
        resp_novim = await client.post(
            f"/api/m11/{m11_id}/bind",
            json={"vimoga_doc_id": 999999},
        )
        assert resp_novim.status == 404

        # 400 for missing vimoga_doc_id
        resp_bad = await client.post(f"/api/m11/{m11_id}/bind", json={})
        assert resp_bad.status == 400

        # 400 for non-numeric id
        resp_bad_id = await client.post("/api/m11/abc/bind", json={"vimoga_doc_id": vimoga_id})
        assert resp_bad_id.status == 400
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_api_available_vimogas(warehouse_env):
    """GET /api/m11/available-vimogas returns unlinked first, already-linked below."""
    db, fs, vs = warehouse_env

    v1_id = db.add_document(
        filename="v1.pdf", file_type="pdf", doc_type="ВИМОГА", doc_number="В-1", doc_date="2026-03-01"
    )
    v2_id = db.add_document(
        filename="v2.pdf", file_type="pdf", doc_type="ВИМОГА", doc_number="В-2", doc_date="2026-03-02"
    )
    m11_id = db.add_document(
        filename="m11.pdf", file_type="pdf", doc_type="ВИМОГА М-11", doc_number="М11-01"
    )

    db.add_document_link(
        m11_doc_id=m11_id,
        vimoga_doc_id=v2_id,
        match_status="full",
        needs_review=0,
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/m11/available-vimogas")
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 2

        # First item is unlinked v1
        assert data[0]["id"] == v1_id
        assert data[0]["doc_number"] == "В-1"
        assert data[0]["is_linked"] is False
        assert data[0]["linked_m11_doc_id"] is None

        # Second item is linked v2
        assert data[1]["id"] == v2_id
        assert data[1]["doc_number"] == "В-2"
        assert data[1]["is_linked"] is True
        assert data[1]["linked_m11_doc_id"] == m11_id
        assert data[1]["linked_m11_doc_number"] == "М11-01"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_m11_document_impact_and_ocr(warehouse_env):
    """M-11 items are included in get_document_impact and returned by GET /api/warehouse/documents/{id}/ocr."""
    db, fs, vs = warehouse_env

    m11_id = db.add_document(
        filename="m11_with_items.jpg",
        file_type="photo",
        doc_type="ВИМОГА М-11",
        doc_number="М11-77",
        doc_date="2026-03-20",
        raw_text="Вимога М-11 № 77",
    )
    db.add_m11_item(
        document_id=m11_id,
        name="Кабель силовий",
        quantity=50.0,
        unit="м",
        nomenclature_number="KBL-01",
    )
    db.add_m11_item(
        document_id=m11_id,
        name="Автомат 16А",
        quantity=3.0,
        unit="шт",
        nomenclature_number="AVT-16",
    )

    # 1. DB get_document_impact
    impact = db.get_document_impact(m11_id)
    assert len(impact) == 2
    assert impact[0]["name"] == "Кабель силовий"
    assert impact[0]["quantity"] == 50.0
    assert impact[0]["unit"] == "м"
    assert impact[0]["sku"] == "KBL-01"
    assert impact[0]["operation_type"] == "expense"

    # 2. HTTP GET /ocr endpoint
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get(f"/api/warehouse/documents/{m11_id}/ocr")
        assert resp.status == 200
        ocr_data = await resp.json()
        assert ocr_data["id"] == m11_id
        assert ocr_data["doc_type"] == "ВИМОГА М-11"
        assert ocr_data["doc_number"] == "М11-77"
        assert len(ocr_data["impact"]) == 2
        assert ocr_data["impact"][0]["name"] == "Кабель силовий"
        assert ocr_data["impact"][1]["name"] == "Автомат 16А"
    finally:
        await client.close()


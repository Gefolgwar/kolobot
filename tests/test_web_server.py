"""Tests for embedded WebServer routes and warehouse API."""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from unittest.mock import MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from kolobot.warehouse_db import REQUIRED_DOC_FIELDS, WarehouseDB
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
async def test_web_server_index(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/")
        assert resp.status == 200
        text = await resp.text()
        assert "kolobot" in text
        assert "edit-modal" in text
        assert "edit-new-value" in text
        assert "edit-comment" in text
        assert "openEditModal" in text
        assert "submitEditField" in text
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_items_empty(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/items")
        assert resp.status == 200
        data = await resp.json()
        assert data == []
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_documents_empty(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/documents")
        assert resp.status == 200
        data = await resp.json()
        assert data == []
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_documents_with_doc_type(warehouse_env):
    db, fs, vs = warehouse_env
    doc_id = db.add_document(
        filename="test.xlsx", file_type="excel", doc_type="НАКЛАДНА",
    )
    item_id = db.add_item(name="Болт М8", sku="12345")
    db.add_transaction(
        item_id=item_id, document_id=doc_id,
        operation_type="income", quantity=10,
        source_row="Рядок 3: 12345 | Болт М8",
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/documents")
        data = await resp.json()
        assert len(data) == 1
        assert data[0]["doc_type"] == "НАКЛАДНА"
        assert data[0]["transaction_count"] == 1

        resp2 = await client.get(f"/api/warehouse/documents/{doc_id}/impact")
        impacts = await resp2.json()
        assert len(impacts) == 1
        assert impacts[0]["source_row"] == "Рядок 3: 12345 | Болт М8"

        resp3 = await client.get(f"/api/warehouse/items/{item_id}/transactions")
        txs = await resp3.json()
        assert len(txs) == 1
        assert txs[0]["doc_type"] == "НАКЛАДНА"
        assert txs[0]["source_row"] == "Рядок 3: 12345 | Болт М8"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_delete_document(warehouse_env):
    db, fs, vs = warehouse_env
    doc_id = db.add_document(filename="del.xlsx", file_type="excel")

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.delete(f"/api/warehouse/documents/{doc_id}")
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True

        resp2 = await client.delete(f"/api/warehouse/documents/{doc_id}")
        assert resp2.status == 404
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_documents_panel_renders_queued_status_column(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/")
        html = await resp.text()
        assert ">Статус <i" in html  # #25: у заголовку колонки тепер ще й індикатор сортування
        assert "⏳ В черзі" in html
        assert "Документ у черзі на розпізнавання" in html
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_queued_document_exposes_status_and_preview(warehouse_env, tmp_path):
    db, fs, vs = warehouse_env
    image_path = tmp_path / "queued.jpg"
    image_path.write_bytes(b"\xff\xd8queued-image")
    doc_id = db.add_document(
        filename="queued.jpg",
        file_type="photo",
        file_path=str(image_path),
        status="queued",
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/documents")
        data = await resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "queued"
        assert data[0]["file_path"] == str(image_path)

        view = await client.get(f"/api/warehouse/documents/{doc_id}/view")
        assert view.status == 200
        assert await view.read() == b"\xff\xd8queued-image"

        ocr = await client.get(f"/api/warehouse/documents/{doc_id}/ocr")
        ocr_data = await ocr.json()
        assert ocr_data["status"] == "queued"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_completed_document_reports_completed_status(warehouse_env):
    db, fs, vs = warehouse_env
    doc_id = db.add_document(filename="done.jpg", file_type="photo", raw_text="текст")

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        ocr = await client.get(f"/api/warehouse/documents/{doc_id}/ocr")
        data = await ocr.json()
        assert data["status"] == "completed"
        assert data["raw_text"] == "текст"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_web_server_processing_status_badges(warehouse_env):
    """Issue #13: Web UI exposes processing_ocr and processing_emb statuses and badges."""
    db, fs, vs = warehouse_env
    doc1 = db.add_document(filename="d1.jpg", file_type="photo", status="processing_ocr")
    doc2 = db.add_document(filename="d2.jpg", file_type="photo", status="processing_emb")

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/documents")
        docs = await resp.json()
        docs_by_id = {d["id"]: d for d in docs}
        assert docs_by_id[doc1]["status"] == "processing_ocr"
        assert docs_by_id[doc2]["status"] == "processing_emb"

        html_resp = await client.get("/")
        html = await html_resp.text()
        assert "🔄 Розпізнавання" in html
        assert "🧠 Embeddings" in html
    finally:
        await client.close()
        db.close()



@pytest.mark.asyncio
async def test_api_document_ocr(warehouse_env):
    db, fs, vs = warehouse_env
    doc_id = db.add_document(
        filename="scan1.jpg",
        file_type="photo",
        doc_type="НАКЛАДНА",
        doc_number="0002143",
        doc_date="03.08.2026",
        raw_text="НАКЛАДНА № 0002143\nКОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В",
    )
    item_id = db.add_item(name="КОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В", sku="288410091721")
    db.add_transaction(
        item_id=item_id,
        document_id=doc_id,
        operation_type="income",
        quantity=250,
        doc_number="0002143",
        doc_date="03.08.2026",
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get(f"/api/warehouse/documents/{doc_id}/ocr")
        assert resp.status == 200
        data = await resp.json()
        assert data["doc_number"] == "0002143"
        assert data["doc_date"] == "03.08.2026"
        assert data["doc_type"] == "НАКЛАДНА"
        assert "НАКЛАДНА № 0002143" in data["raw_text"]
        assert len(data["impact"]) == 1
        assert data["impact"][0]["name"] == "КОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_document_ocr_from_txt_file(warehouse_env, tmp_path):
    db, fs, vs = warehouse_env
    # Document has empty raw_text in db, but .txt file exists
    txt_file = tmp_path / "abc1234567.txt"
    txt_file.write_text("ВИМОГА № 0000555\nТЕКСТ З ФАЙЛУ ДИСКУ", encoding="utf-8")
    fs.read_text.return_value = "ВИМОГА № 0000555\nТЕКСТ З ФАЙЛУ ДИСКУ"

    doc_id = db.add_document(
        filename="abc1234567.jpg",
        file_type="photo",
        file_path=str(tmp_path / "abc1234567.jpg"),
        doc_type="ВИМОГА",
        doc_number="0000555",
        doc_date="15.08.2026",
        raw_text="",  # Empty in DB
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get(f"/api/warehouse/documents/{doc_id}/ocr")
        assert resp.status == 200
        data = await resp.json()
        assert data["doc_number"] == "0000555"
        assert data["doc_date"] == "15.08.2026"
        assert data["doc_type"] == "ВИМОГА"
        assert "ВИМОГА № 0000555" in data["raw_text"]
        assert "ТЕКСТ З ФАЙЛУ ДИСКУ" in data["raw_text"]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_item_metadata_post(warehouse_env):
    db, fs, vs = warehouse_env
    doc_id = db.add_document(filename="items.xlsx", file_type="excel")
    item_id = db.add_item(name="Резистор 10к", sku="RES-10K", unit="шт", supplier="ПромЕлектро", notes="0.25Вт")
    db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=100)

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # Edit name via POST /api/warehouse/items/{id}/edit
        payload = {"field": "name", "value": "Резистор 10кОм 0.5Вт", "comment": "Уточнення потужності"}
        resp = await client.post(f"/api/warehouse/items/{item_id}/edit", json=payload)
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["item"]["name"] == "Резистор 10кОм 0.5Вт"
        assert data["old_value"] == "Резистор 10к"
        assert data["new_value"] == "Резистор 10кОм 0.5Вт"
        assert "Змінено [Найменування]: 'Резистор 10к' → 'Резистор 10кОм 0.5Вт'" in data["source_row"]

        # Verify DB transactions
        txs = db.get_item_transactions(item_id)
        assert len(txs) == 2
        assert txs[1]["quantity"] == 0.0
        assert txs[1]["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"

        # Verify items list endpoint shows updated name with same balance
        items_resp = await client.get("/api/warehouse/items")
        items = await items_resp.json()
        assert items[0]["name"] == "Резистор 10кОм 0.5Вт"
        assert items[0]["balance"] == 100.0
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_item_metadata_patch(warehouse_env):
    db, fs, vs = warehouse_env
    item_id = db.add_item(name="Кабель ВВГ", sku="OLD-SKU")
    doc_id = db.add_document(filename="init.xlsx", file_type="excel")
    db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=25)

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # Edit SKU via PATCH /api/warehouse/items/{id}
        payload = {"field": "sku", "value": "CAB-VVG-3x2.5"}
        resp = await client.patch(f"/api/warehouse/items/{item_id}", json=payload)
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["item"]["sku"] == "CAB-VVG-3x2.5"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_item_errors(warehouse_env):
    db, fs, vs = warehouse_env
    item_id = db.add_item(name="Дріт мідний")

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # 404 for nonexistent item
        resp = await client.post("/api/warehouse/items/99999/edit", json={"field": "name", "value": "Test"})
        assert resp.status == 404
        data = await resp.json()
        assert "error" in data

        # 400 for invalid JSON / empty body
        resp = await client.post(f"/api/warehouse/items/{item_id}/edit", data="not json", headers={"Content-Type": "application/json"})
        assert resp.status == 400

        # 400 for missing field
        resp = await client.post(f"/api/warehouse/items/{item_id}/edit", json={"value": "Test"})
        assert resp.status == 400

        # 400 for disallowed field
        resp = await client.post(f"/api/warehouse/items/{item_id}/edit", json={"field": "unsupported", "value": "Val"})
        assert resp.status == 400
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_adjust_item_quantity_success_income(warehouse_env):
    db, fs, vs = warehouse_env
    doc_id = db.add_document(filename="init.xlsx", file_type="excel")
    item_id = db.add_item(name="Кабель ВВГ", sku="CAB-01", unit="м")
    db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=50)

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # Increase balance from 50 to 75 (delta = +25)
        payload = {"field": "balance", "value": 75, "comment": "Інвентаризація"}
        resp = await client.post(f"/api/warehouse/items/{item_id}/edit", json=payload)
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["old_balance"] == 50.0
        assert data["target_quantity"] == 75.0
        assert data["delta"] == 25.0
        assert data["operation_type"] == "income"
        assert data["transaction_id"] is not None
        assert "Змінено 'Кількість': 50 → 75 (Інвентаризація)" in data["source_row"]

        # Verify item list returns updated balance
        items_resp = await client.get("/api/warehouse/items")
        items = await items_resp.json()
        assert items[0]["balance"] == 75.0
        assert items[0]["total_income"] == 75.0
        assert items[0]["total_expense"] == 0.0

        # Verify transactions endpoint returns adjustment transaction with badge info
        txs_resp = await client.get(f"/api/warehouse/items/{item_id}/transactions")
        txs = await txs_resp.json()
        assert len(txs) == 2
        assert txs[1]["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"
        assert txs[1]["filename"] == "Ручне редагування (Користувач)"
        assert txs[1]["quantity"] == 25.0
        assert txs[1]["running_balance"] == 75.0
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_adjust_item_quantity_success_expense(warehouse_env):
    db, fs, vs = warehouse_env
    doc_id = db.add_document(filename="init.xlsx", file_type="excel")
    item_id = db.add_item(name="Труба ПВХ", sku="TR-01", unit="м")
    db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=100)

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # Decrease balance from 100 to 70 (delta = -30)
        payload = {"field": "quantity", "value": "70", "comment": "Списання"}
        resp = await client.post(f"/api/warehouse/items/{item_id}/edit", json=payload)
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["old_balance"] == 100.0
        assert data["target_quantity"] == 70.0
        assert data["delta"] == -30.0
        assert data["operation_type"] == "expense"
        assert data["transaction_id"] is not None

        # Verify balance reconciliation
        items_resp = await client.get("/api/warehouse/items")
        items = await items_resp.json()
        assert items[0]["balance"] == 70.0
        assert items[0]["total_income"] == 100.0
        assert items[0]["total_expense"] == 30.0
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_adjust_item_quantity_invalid_number(warehouse_env):
    db, fs, vs = warehouse_env
    item_id = db.add_item(name="Гайка М6")

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        payload = {"field": "balance", "value": "not-a-number"}
        resp = await client.post(f"/api/warehouse/items/{item_id}/edit", json=payload)
        assert resp.status == 400
        data = await resp.json()
        assert "error" in data
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_adjust_item_quantity_and_excel_export_reconciliation(warehouse_env):
    import io
    import openpyxl

    db, fs, vs = warehouse_env
    doc_id = db.add_document(filename="init.xlsx", file_type="excel")
    item1_id = db.add_item(name="Кабель ВВГ", sku="CAB-01", unit="м")
    item2_id = db.add_item(name="Труба ПВХ", sku="TR-01", unit="м")
    db.add_transaction(item_id=item1_id, document_id=doc_id, operation_type="income", quantity=50)
    db.add_transaction(item_id=item2_id, document_id=doc_id, operation_type="income", quantity=100)

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # 1. Adjust item1 (+30 -> 80)
        resp1 = await client.post(f"/api/warehouse/items/{item1_id}/edit", json={"field": "balance", "value": 80, "comment": "Довезення"})
        assert resp1.status == 200

        # 2. Adjust item2 (-40 -> 60)
        resp2 = await client.post(f"/api/warehouse/items/{item2_id}/edit", json={"field": "quantity", "value": 60, "comment": "Списання"})
        assert resp2.status == 200

        # 3. Verify items API endpoint
        items_resp = await client.get("/api/warehouse/items")
        assert items_resp.status == 200
        items = await items_resp.json()
        cab = next(i for i in items if i["id"] == item1_id)
        pipe = next(i for i in items if i["id"] == item2_id)

        assert cab["total_income"] == 80.0
        assert cab["total_expense"] == 0.0
        assert cab["balance"] == 80.0

        assert pipe["total_income"] == 100.0
        assert pipe["total_expense"] == 40.0
        assert pipe["balance"] == 60.0

        # 4. Download Excel export and verify cell values
        export_resp = await client.get("/api/warehouse/export")
        assert export_resp.status == 200
        excel_bytes = await export_resp.read()

        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        ws = wb.active
        # Headers in row 1: sku, name, doc_date, income, expense, balance, unit, doc_number, supplier, notes
        rows = list(ws.iter_rows(values_only=True))
        assert len(rows) == 3  # Header + 2 items

        header = rows[0]
        income_idx = header.index("Прихід")
        expense_idx = header.index("Розхід")
        balance_idx = header.index("Залишок")
        name_idx = header.index("Найменування")

        cab_row = next(r for r in rows[1:] if r[name_idx] == "Кабель ВВГ")
        pipe_row = next(r for r in rows[1:] if r[name_idx] == "Труба ПВХ")

        assert cab_row[income_idx] == 80.0
        assert cab_row[expense_idx] == "" or cab_row[expense_idx] == 0.0  # exported as empty or 0
        assert cab_row[balance_idx] == 80.0

        assert pipe_row[income_idx] == 100.0
        assert pipe_row[expense_idx] == 40.0
        assert pipe_row[balance_idx] == 60.0
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_web_server_log_tab_html(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/")
        assert resp.status == 200
        text = await resp.text()
        assert "tab-logs" in text
        assert "panel-logs" in text
        assert "~/logs" in text
        assert "grep logs..." in text
        assert "lvl-info" in text
        assert "lvl-success" in text
        assert "lvl-warn" in text
        assert "lvl-err" in text
        assert "log-autoscroll" in text
        assert "clearLogsServer" in text
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_logs_and_clear(warehouse_env):
    from kolobot.log_service import LogBuffer

    db, fs, vs = warehouse_env
    log_buf = LogBuffer(maxlen=100)
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42, log_buffer=log_buf)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # Initial empty logs
        resp = await client.get("/api/logs")
        assert resp.status == 200
        data = await resp.json()
        assert "logs" in data
        assert "total_count" in data
        assert "last_id" in data

        # Add some log entries
        log_buf.add_entry(level="INFO", logger_name="kolobot.app", message="Bot started")
        log_buf.add_entry(level="WARN", logger_name="kolobot.key_pool", message="Key cooldown active")
        log_buf.add_entry(level="ERR", logger_name="kolobot.gateway", message="Gemini 500 error")

        # Fetch all
        resp = await client.get("/api/logs")
        assert resp.status == 200
        data = await resp.json()
        assert data["total_count"] == 3
        assert len(data["logs"]) == 3

        # Filter by since_id
        resp = await client.get("/api/logs?since_id=2")
        data = await resp.json()
        assert len(data["logs"]) == 1
        assert data["logs"][0]["level"] == "ERR"

        # Filter by level
        resp = await client.get("/api/logs?level=WARN")
        data = await resp.json()
        assert len(data["logs"]) == 1
        assert data["logs"][0]["level"] == "WARN"

        # Filter by query
        resp = await client.get("/api/logs?q=cooldown")
        data = await resp.json()
        assert len(data["logs"]) == 1
        assert "cooldown" in data["logs"][0]["message"].lower()

        # Clear via POST /api/logs/clear
        resp = await client.post("/api/logs/clear")
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["cleared_count"] == 3

        # Verify empty
        resp = await client.get("/api/logs")
        data = await resp.json()
        assert data["total_count"] == 0
        assert len(data["logs"]) == 0

        # Add one and clear via DELETE /api/logs
        log_buf.add_entry(level="INFO", logger_name="kolobot.app", message="Another log")
        del_resp = await client.delete("/api/logs")
        assert del_resp.status == 200
        data = await del_resp.json()
        assert data["success"] is True
        assert data["cleared_count"] == 1
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_logs_stream(warehouse_env):
    import asyncio
    from kolobot.log_service import LogBuffer

    db, fs, vs = warehouse_env
    log_buf = LogBuffer(maxlen=100)
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42, log_buffer=log_buf)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/logs/stream")
        assert resp.status == 200
        assert "text/event-stream" in resp.headers.get("Content-Type", "")

        # Read initial ping frame (: ping\n\n)
        line1 = await resp.content.readline()
        assert b"ping" in line1
        line2 = await resp.content.readline()
        assert line2 == b"\n"

        # Add a log entry and verify it's pushed to stream
        log_buf.add_entry(level="INFO", logger_name="kolobot.test", message="Stream event test")
        event_data = await resp.content.readline()
        assert b"data:" in event_data
        assert b"Stream event test" in event_data
    finally:
        await client.close()
        db.close()



@pytest.mark.asyncio
async def test_document_inspection_item_edit_integration(warehouse_env):
    """Integration test verifying editing item parameters from within document inspection context."""
    db, fs, vs = warehouse_env

    # 1. Ingest a document with OCR recognized items
    doc_id = db.add_document(
        filename="scan_invoice_101.jpg",
        file_type="photo",
        doc_type="НАКЛАДНА",
        doc_number="СФ-101",
        doc_date="28.08.2026",
        raw_text="РАХУНОК-ФАКТУРА СФ-101\n1. РЕЗИСТ0Р 10к (misrecognized OCR) - 100 шт",
    )
    # Misrecognized item created during OCR import
    item_id = db.add_item(name="РЕЗИСТ0Р 10к", sku="R-10K-MISREAD", unit="шт")
    db.add_transaction(
        item_id=item_id,
        document_id=doc_id,
        operation_type="income",
        quantity=100.0,
        doc_number="СФ-101",
        doc_date="28.08.2026",
        source_row="1. РЕЗИСТ0Р 10к - 100 шт",
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # 2. Inspect document via OCR endpoint (as done in OCR side-by-side modal & expanded impact)
        ocr_resp = await client.get(f"/api/warehouse/documents/{doc_id}/ocr")
        assert ocr_resp.status == 200
        ocr_data = await ocr_resp.json()
        assert len(ocr_data["impact"]) == 1
        imp = ocr_data["impact"][0]
        assert imp["item_id"] == item_id
        assert imp["name"] == "РЕЗИСТ0Р 10к"
        assert imp["sku"] == "R-10K-MISREAD"
        assert imp["quantity"] == 100.0

        # 3. User corrects OCR mistakes while inspecting the document (SKU and Name)
        edit_sku_resp = await client.post(
            f"/api/warehouse/items/{item_id}/edit",
            json={"field": "sku", "value": "R-10K-CORRECTED", "comment": "Виправлено помилку OCR"},
        )
        assert edit_sku_resp.status == 200
        sku_data = await edit_sku_resp.json()
        assert sku_data["success"] is True
        assert sku_data["item"]["sku"] == "R-10K-CORRECTED"

        edit_name_resp = await client.post(
            f"/api/warehouse/items/{item_id}/edit",
            json={"field": "name", "value": "Резистор 10кОм 0.25Вт", "comment": "Корекція назви за сканом"},
        )
        assert edit_name_resp.status == 200
        name_data = await edit_name_resp.json()
        assert name_data["success"] is True
        assert name_data["item"]["name"] == "Резистор 10кОм 0.25Вт"

        # 4. Re-inspect document OCR and Impact: the document items list reflects corrected values
        ocr_resp2 = await client.get(f"/api/warehouse/documents/{doc_id}/ocr")
        ocr_data2 = await ocr_resp2.json()
        assert len(ocr_data2["impact"]) == 1
        updated_imp = ocr_data2["impact"][0]
        assert updated_imp["item_id"] == item_id
        assert updated_imp["name"] == "Резистор 10кОм 0.25Вт"
        assert updated_imp["sku"] == "R-10K-CORRECTED"

        impact_resp = await client.get(f"/api/warehouse/documents/{doc_id}/impact")
        assert impact_resp.status == 200
        impact_data = await impact_resp.json()
        assert impact_data[0]["name"] == "Резистор 10кОм 0.25Вт"
        assert impact_data[0]["sku"] == "R-10K-CORRECTED"

        # 5. Verify HTML template contains pencil edit action triggers in OCR list and document impact
        index_resp = await client.get("/")
        assert index_resp.status == 200
        html = await index_resp.text()
        assert "openEditModal" in html
        # Check that openEditModal is hooked up to document impact rows and OCR items list
        assert "loadDocumentOcr" in html
        assert "toggleDocImpact" in html
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_document_inspection_quantity_edit_integration(warehouse_env):
    """Edit item balance from document inspection context and verify OCR/impact reflect the change."""
    db, fs, vs = warehouse_env

    doc_id = db.add_document(
        filename="scan_nakladna_200.jpg",
        file_type="photo",
        doc_type="НАКЛАДНА",
        doc_number="НКЛ-200",
        doc_date="29.08.2026",
        requested_by="начальник служби (ПІБ)",
        requested_via="7939 - (ПІБ)",
        raw_text="НАКЛАДНА НКЛ-200\nТРУБА ПВХ 32мм - 50 м",
    )
    item_id = db.add_item(name="Труба ПВХ 32мм", sku="PIPE-32", unit="м")
    db.add_transaction(
        item_id=item_id,
        document_id=doc_id,
        operation_type="income",
        quantity=50.0,
        doc_number="НКЛ-200",
        doc_date="29.08.2026",
        source_row="1. ТРУБА ПВХ 32мм - 50 м",
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # 1. Inspect document — see item with balance 50
        ocr_resp = await client.get(f"/api/warehouse/documents/{doc_id}/ocr")
        assert ocr_resp.status == 200
        ocr_data = await ocr_resp.json()
        assert ocr_data["impact"][0]["quantity"] == 50.0

        # 2. User corrects quantity from the document inspection view (OCR was 50, actual is 45)
        edit_resp = await client.post(
            f"/api/warehouse/items/{item_id}/edit",
            json={"field": "balance", "value": 45, "comment": "Перерахунок за сканом"},
        )
        assert edit_resp.status == 200
        data = await edit_resp.json()
        assert data["success"] is True
        assert data["old_balance"] == 50.0
        assert data["target_quantity"] == 45.0
        assert data["delta"] == -5.0
        assert data["operation_type"] == "expense"

        # 3. Verify warehouse items endpoint reflects the new balance
        items_resp = await client.get("/api/warehouse/items")
        items = await items_resp.json()
        pipe = next(i for i in items if i["id"] == item_id)
        assert pipe["balance"] == 45.0

        # 4. Verify audit trail in transactions
        txs_resp = await client.get(f"/api/warehouse/items/{item_id}/transactions")
        txs = await txs_resp.json()
        assert len(txs) == 2
        adj_tx = txs[1]
        assert adj_tx["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"
        assert adj_tx["quantity"] == 5.0
        assert adj_tx["operation_type"] == "expense"
        assert adj_tx["running_balance"] == 45.0
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_document_inspection_multi_item_edit_integration(warehouse_env):
    """Edit multiple items from a single document's inspection view."""
    db, fs, vs = warehouse_env

    doc_id = db.add_document(
        filename="scan_nakladna_300.jpg",
        file_type="photo",
        doc_type="НАКЛАДНА",
        doc_number="НКЛ-300",
        doc_date="30.08.2026",
        raw_text="НАКЛАДНА НКЛ-300\n1. Б0ЛТ М8 - 200 шт\n2. ГАЙКА М8 - 150 шт",
    )
    item1_id = db.add_item(name="Б0ЛТ М8", sku="BOLT-M8-BAD", unit="шт")
    item2_id = db.add_item(name="ГАЙКА М8", sku="NUT-M8", unit="шт")
    db.add_transaction(item_id=item1_id, document_id=doc_id, operation_type="income", quantity=200.0)
    db.add_transaction(item_id=item2_id, document_id=doc_id, operation_type="income", quantity=150.0)

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # 1. Inspect document — both items visible
        ocr_resp = await client.get(f"/api/warehouse/documents/{doc_id}/ocr")
        ocr = await ocr_resp.json()
        assert len(ocr["impact"]) == 2

        # 2. Fix OCR mistake in item1 name (Б0ЛТ -> Болт) and SKU
        resp1 = await client.post(
            f"/api/warehouse/items/{item1_id}/edit",
            json={"field": "name", "value": "Болт М8", "comment": "OCR помилка: 0 замість о"},
        )
        assert resp1.status == 200

        resp2 = await client.post(
            f"/api/warehouse/items/{item1_id}/edit",
            json={"field": "sku", "value": "BOLT-M8-FIXED"},
        )
        assert resp2.status == 200

        # 3. Edit item2 unit
        resp3 = await client.post(
            f"/api/warehouse/items/{item2_id}/edit",
            json={"field": "unit", "value": "компл", "comment": "Комплект, не штуки"},
        )
        assert resp3.status == 200

        # 4. Re-inspect document — all edits reflected
        ocr2_resp = await client.get(f"/api/warehouse/documents/{doc_id}/ocr")
        ocr2 = await ocr2_resp.json()
        assert len(ocr2["impact"]) == 2

        bolt = next(i for i in ocr2["impact"] if i["item_id"] == item1_id)
        nut = next(i for i in ocr2["impact"] if i["item_id"] == item2_id)
        assert bolt["name"] == "Болт М8"
        assert bolt["sku"] == "BOLT-M8-FIXED"
        assert nut["unit"] == "компл"

        # 5. Verify impact endpoint also matches
        impact_resp = await client.get(f"/api/warehouse/documents/{doc_id}/impact")
        impact = await impact_resp.json()
        bolt_imp = next(i for i in impact if i["item_id"] == item1_id)
        nut_imp = next(i for i in impact if i["item_id"] == item2_id)
        assert bolt_imp["name"] == "Болт М8"
        assert bolt_imp["sku"] == "BOLT-M8-FIXED"
        assert nut_imp["unit"] == "компл"

        # 6. Verify audit transactions: 2 edits for item1 (name, sku), 1 for item2 (unit)
        txs1 = db.get_item_transactions(item1_id)
        audit_txs1 = [t for t in txs1 if t["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"]
        assert len(audit_txs1) == 2
        assert all(t["quantity"] == 0.0 for t in audit_txs1)

        txs2 = db.get_item_transactions(item2_id)
        audit_txs2 = [t for t in txs2 if t["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"]
        assert len(audit_txs2) == 1
        assert "Змінено [Од. виміру]: 'шт' → 'компл'" in audit_txs2[0]["source_row"]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_web_server_index_min_balance_column_and_filter(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/")
        assert resp.status == 200
        text = await resp.text()
        assert "Мін. залишок" in text
        assert "filter-below-min" in text
        assert "filter-below-min-count" in text
        assert "Менше мінімального залишку" in text
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_min_balance_post_and_patch(warehouse_env):
    db, fs, vs = warehouse_env
    item_id = db.add_item(name="Кабель UTP", sku="UTP-5E", min_balance=0.0)
    doc_id = db.add_document(filename="init.xlsx", file_type="excel")
    db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=50)

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # 1. Edit min_balance via POST /api/warehouse/items/{id}/edit
        payload = {"field": "min_balance", "value": 20, "comment": "Встановлено мінімальний залишок"}
        resp = await client.post(f"/api/warehouse/items/{item_id}/edit", json=payload)
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["item"]["min_balance"] == 20.0
        assert "Змінено [Мінімальний залишок]: '0' → '20'" in data["source_row"]

        # 2. Check items API returns min_balance
        items_resp = await client.get("/api/warehouse/items")
        items = await items_resp.json()
        assert len(items) == 1
        assert items[0]["min_balance"] == 20.0
        assert items[0]["balance"] == 50.0

        # 3. Edit min_balance via PATCH
        patch_payload = {"field": "min_balance", "value": "35.5"}
        resp_patch = await client.patch(f"/api/warehouse/items/{item_id}", json=patch_payload)
        assert resp_patch.status == 200
        data_patch = await resp_patch.json()
        assert data_patch["success"] is True
        assert data_patch["item"]["min_balance"] == 35.5
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_min_balance_invalid_number(warehouse_env):
    db, fs, vs = warehouse_env
    item_id = db.add_item(name="Тестовий товар")

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.post(f"/api/warehouse/items/{item_id}/edit", json={"field": "min_balance", "value": "abc"})
        assert resp.status == 400
        data = await resp.json()
        assert "error" in data
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_min_balance_excel_export_and_import(warehouse_env, tmp_path):
    import io
    import openpyxl
    from kolobot.excel_service import parse_excel

    db, fs, vs = warehouse_env
    doc_id = db.add_document(filename="init.xlsx", file_type="excel")
    item1_id = db.add_item(name="Світильник 36W", sku="LIGHT-36", min_balance=15.0)
    db.add_transaction(item_id=item1_id, document_id=doc_id, operation_type="income", quantity=10.0)

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        # 1. Export Excel and check min_balance column
        export_resp = await client.get("/api/warehouse/export")
        assert export_resp.status == 200
        excel_bytes = await export_resp.read()

        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        assert len(rows) == 2
        header = rows[0]
        assert "Мін. залишок" in header
        min_idx = header.index("Мін. залишок")
        assert rows[1][min_idx] == 15.0

        # 2. Test parse_excel with minimum balance header
        test_file = tmp_path / "test_import.xlsx"
        wb_new = openpyxl.Workbook()
        ws_new = wb_new.active
        ws_new.append(["Найменування", "Номенклатурний номер", "Прихід", "Мінімальний залишок"])
        ws_new.append(["Автомат 16A", "AUTO-16", 20, 5])
        wb_new.save(str(test_file))
        wb_new.close()

        doc_type, parsed_rows = parse_excel(str(test_file))
        assert len(parsed_rows) == 1
        assert parsed_rows[0]["name"] == "Автомат 16A"
        assert parsed_rows[0]["min_balance"] == 5.0
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_documents_and_transactions_expose_requested_by(warehouse_env):
    """У "Документах" і в розгорнутому рядку "Складу" видно, хто затребував документ і через кого."""
    db, fs, vs = warehouse_env
    doc_id = db.add_document(
        filename="vymoha.jpg",
        file_type="photo",
        doc_type="ВИМОГА",
        raw_text="ВИМОГА № 0000215\nЧЕРЕЗ КОГО 7939 - (ПІБ)\nЗАТРЕБУВАВ: начальник служби (ПІБ)",
        requested_by="начальник служби (ПІБ)",
        requested_via="7939 - (ПІБ)",
    )
    item_id = db.add_item(name="Болт М8", sku="12345")
    db.add_transaction(
        item_id=item_id, document_id=doc_id,
        operation_type="expense", quantity=5,
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        docs = await (await client.get("/api/warehouse/documents")).json()
        assert docs[0]["requested_by"] == "начальник служби (ПІБ)"
        assert docs[0]["requested_via"] == "7939 - (ПІБ)"

        txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
        assert txs[0]["requested_by"] == "начальник служби (ПІБ)"
        assert txs[0]["requested_via"] == "7939 - (ПІБ)"

        ocr = await (await client.get(f"/api/warehouse/documents/{doc_id}/ocr")).json()
        assert ocr["requested_by"] == "начальник служби (ПІБ)"
        assert ocr["requested_via"] == "7939 - (ПІБ)"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_documents_table_has_requested_by_column(warehouse_env):
    """"Документи" мають однойменну колонку, "Склад" — колонку в таблиці транзакцій."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        html = await (await client.get("/")).text()
        docs_head = html.split('id="docs-tbody"')[0]
        assert docs_head.count("Затребував") == 1
        assert docs_head.count("Через кого") == 1
        assert "tx.requested_by" in html
        assert "tx.requested_via" in html
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_table_fields_wrap_instead_of_truncating(warehouse_env):
    """Табличні поля переносяться рядками, а не обрізаються трикрапкою."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        html = await (await client.get("/")).text()
        # "data.truncated" — прапорець обрізання OCR-тексту в API, не CSS-клас
        markup = html.replace("data.truncated", "")

        assert "truncate" not in markup
        for legacy_width in ("max-w-[105px]", "max-w-[160px]", "max-w-[170px]",
                             "max-w-[180px]", "max-w-[200px]", "max-w-[250px]"):
            assert legacy_width not in markup

        # перенос рядків у клітинках дозволено
        assert markup.count("break-words") >= 10

        # title-підказки, що лише компенсували обрізання, прибрані
        assert 'title="${esc(requestedBy)}"' not in html
        assert 'title="${esc(requestedVia)}"' not in html
        assert 'title="${esc(it.notes)}"' not in html
        assert 'title="${esc(imp.name)}"' not in html
        assert 'title="${esc(srcRow)}"' not in html
        assert 'title="${esc(tx.filename)}"' not in html

        # підказка з текстом помилки на бейджі статусу лишається
        assert 'title="${esc(doc.error_message)}"' in html
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_tables_use_compact_cells(warehouse_env):
    """Обидві таблиці компактизовано, а правила мають !important."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        html = await (await client.get("/")).text()

        # клас стоїть на обох таблицях («Склад» і «Документи»)
        assert html.count("border-collapse compact-table") == 2

        # tracking-wider прибрано саме із заголовків таблиць (у логах він лишається)
        assert html.count("uppercase tracking-wider border-b") == 0
        assert html.count("text-slate-400 text-xs font-semibold uppercase border-b border-slate-800") == 2

        # !important обов'язковий: Tailwind з CDN вставляє утиліти в <head> пізніше
        # за вбудований <style>, тому без нього правила мовчки програють px-3 / py-4
        assert ".compact-table > thead > tr > th" in html
        assert ".compact-table > tbody > tr > td:not([colspan])" in html
        assert "padding: 8px !important;" in html
        assert "font-size: 10px !important;" in html
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_documents_table_has_card_mode_markup(warehouse_env):
    """Картковий режим нижче 1000px: маркер-клас, data-label і адаптивний CSS."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        html = await (await client.get("/")).text()

        # маркер стоїть на обох таблицях — «Склад» доєднався у слайсі #22
        assert html.count("compact-table card-table") == 2

        # кожна клітинка рядка документа підписана текстом свого <th>
        for label in ("Превʼю", "Файл", "Тип", "Тип документу", "Статус",
                      "Дата завантаження", "№ документа", "Затребував",
                      "Через кого", "Позицій", "Дії"):
            assert f'data-label="{label}"' in html, label
        # рахунок обмежено тілом renderDocs, щоб підписи інших таблиць і CSS-селектори
        # з data-label="…" не впливали на число
        render_docs = html.split("function renderDocs(docs)")[1].split("tbody.innerHTML = html;")[0]
        assert render_docs.count(' data-label="') == 11

        # шеврон і повноширинні клітинки розгорнутих блоків підпису не отримують
        # (у клітинці шеврона живе ще й мітка «не в обліку» — #29)
        assert '<td class="py-4 px-3 whitespace-nowrap"><i id="doc-chevron-' in html
        assert '<td colspan="12" class="p-0">' in html  # рядок деталей — без data-label

        # перемикання таблиця/картки робить виключно CSS, без JS-розгалужень за шириною.
        # 999.98px, а не 1000px: межа мусить працювати в обидва боки —
        # при 1000px ще таблиця, при 999px уже картки.
        assert "@media (max-width: 999.98px)" in html
        assert "attr(data-label)" in html
        assert ".card-table thead { display: none; }" in html
        assert "innerWidth" not in html

        # шеврон у картці переїжджає у правий верхній кут, а не лишається порожнім рядком
        assert ".card-table > tbody > tr:not(.hidden) > td:first-child:not([colspan])" in html
        assert "white-space: nowrap;" in html  # числа й дати не рвуться посеред значення
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_warehouse_table_has_card_mode_markup(warehouse_env):
    """Слайс #22: таблиця «Склад» стає картками, олівці видимі й стоять біля значення."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        html = await (await client.get("/")).text()

        # кожна з дев'яти підписаних колонок складу підписується текстом свого <th>
        for label in ("Ном. номер", "Найменування", "Прихід", "Розхід", "Залишок",
                      "Мін. залишок", "Од.виміру", "Постачальник", "Примітки"):
            assert f'data-label="{label}"' in html, label

        # десята колонка — шеврон: підпису не має, як і рядок розгорнутих транзакцій
        assert '<td class="py-4 px-3"><i id="chevron-' in html
        assert '<td colspan="10" class="p-0">' in html

        # рахунок обмежено тілом renderItems: CSS-селектори з data-label="…" і підписи
        # вкладених таблиць не мають впливати на число
        render_items = html.split("function renderItems(items)")[1].split("tbody.innerHTML = html;")[0]
        assert render_items.count(' data-label="') == 9

        # олівці редагування: у картці вони opacity-1 без наведення, а justify-content
        # flex-start перебиває утиліту justify-between, тож олівець стоїть біля значення
        assert ".card-table > tbody > tr > td button { opacity: 1 !important; }" in html
        assert ".card-table > tbody > tr > td > span.flex { justify-content: flex-start !important; }" in html

        # підсвітка «нижче мінімуму»: правило картки специфічніше за утиліти Tailwind з CDN,
        # тому рамку й тло повертає окреме правило за маркером row-low
        assert "rowClass = 'row-low bg-rose-950/40" in html
        assert ".card-table > tbody > tr.row-low" in html
        assert "border-left: 4px solid #f43f5e !important;" in html

        # числові колонки складу не рвуться посеред значення
        for label in ("Прихід", "Розхід", "Залишок", "Мін. залишок"):
            assert f'.card-table > tbody > tr > td[data-label="{label}"]' in html, label
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_nested_tables_have_card_mode_markup(warehouse_env):
    """Слайс #23: історія транзакцій і позиції документа теж стають картками."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        html = await (await client.get("/")).text()

        # історія транзакцій: 10 підписів усередині самої таблиці
        tx_table = html.split('<table class="w-full card-table">')[1].split("</table>")[0]
        for label in ("Дата", "Тип", "Тип док.", "Кількість", "№ накл.",
                      "Залишок", "Документ", "Затребував", "Через кого", "Джерело"):
            assert f'data-label="{label}"' in tx_table, label
        assert tx_table.count(' data-label="') == 10

        # позиції документа: два окремі рендери — для фото й для Excel —
        # з однаковим набором із 6 колонок в обох
        item_tables = html.split('<table class="w-full text-xs card-table">')[1:]
        assert len(item_tables) == 2
        for body in (chunk.split("</table>")[0] for chunk in item_tables):
            for label in ("Ном. номер", "Найменування", "Тип", "Кількість", "Од.", "Джерело"):
                assert f'data-label="{label}"' in body, label
            assert body.count(' data-label="') == 6

        # перша клітинка вкладеної таблиці — змістовна колонка, а не шеврон,
        # тож правило правого верхнього кута з #21 для неї скасовується
        assert ".card-table .card-table > tbody > tr:not(.hidden) > td:first-child:not([colspan])" in html

        # порожній стан не став таблицею — це звичайний абзац, який картковий режим не чіпає
        assert '\'<p class="text-slate-500 py-2">Немає транзакцій.</p>\'' in html

        # дати, кількості й номери накладних не рвуться посеред значення
        for label in ("Дата", "Кількість", "№ накл."):
            assert f'.card-table > tbody > tr > td[data-label="{label}"]' in html, label
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_document_ocr_returns_all_recognition_fields(warehouse_env):
    """#27: серверна частина картки віддає всі пʼять полів розпізнавання, порожні — порожніми рядками."""
    db, fs, vs = warehouse_env
    partial_id = db.add_document(
        filename="vymoha.jpg",
        file_type="photo",
        doc_type="ВИМОГА",
        doc_number="0000215",
        doc_date="15.08.2026",
        requested_via="7939 - (ПІБ)",
        raw_text="ВИМОГА № 0000215",
    )
    empty_id = db.add_document(filename="scan.jpg", file_type="photo")

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    fields = ("doc_type", "doc_number", "doc_date", "requested_by", "requested_via")
    try:
        data = await (await client.get(f"/api/warehouse/documents/{partial_id}/ocr")).json()
        for key in fields:
            assert key in data, key
            assert isinstance(data[key], str), key
        assert data["requested_via"] == "7939 - (ПІБ)"
        # OCR прочитав «ЗАТРЕБУВАВ» як «ЧЕРЕЗ КОГО», тож поле лишається порожнім — але присутнім
        assert data["requested_by"] == ""

        # документ без жодного розпізнаного поля: ключі є, значення порожні
        empty = await (await client.get(f"/api/warehouse/documents/{empty_id}/ocr")).json()
        for key in fields:
            assert empty[key] == "", key
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_document_card_renders_all_recognition_fields(warehouse_env):
    """#27: розгорнута картка будує блок кожного з пʼяти полів — значенням або прочерком."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        html = await (await client.get("/")).text()
        card = html.split("async function reloadDocImpact", 1)[1].split("async function toggleDocImpact", 1)[0]

        # жодне з пʼяти полів не рендериться умовно
        for guard in ("if (data.doc_type)", "if (data.doc_number)", "if (data.doc_date)",
                      "if (data.requested_by)", "if (data.requested_via)"):
            assert guard not in card, guard

        # усі пʼять полів малюються завжди: заповнене — значенням, порожнє — прочерком
        for label in ("Тип", "№", "Дата", "Затребував", "Через кого"):
            assert f"metaField('{label}'" in card, label
        assert "metaDash" in card

        # у Excel-документа й системного документа розділу розпізнаних полів немає, як і раніше
        excel_branch = card.split("// Excel / other non-photo documents", 1)[1]
        assert "metaField(" not in excel_branch
    finally:
        await client.close()
        db.close()


# ---- Слайс #25: сортування таблиці документів ----

NODE = shutil.which("node")

DOC_SORT_BLOCK_START = "// ---- Сортування таблиці документів (#25) ----"
DOC_SORT_BLOCK_END = "// ---- Кінець сортування таблиці документів (#25) ----"

# Заголовок → ключ сортування. Девʼять колонок; превʼю, розгортання й дії не сортуються.
DOC_SORT_HEADERS = (
    ("Файл", "filename"),
    ("Тип", "file_type"),
    ("Тип документу", "doc_type"),
    ("Статус", "status"),
    ("Дата завантаження", "uploaded_at"),
    ("№ документа", "doc_number"),
    ("Затребував", "requested_by"),
    ("Через кого", "requested_via"),
    ("Позицій", "transaction_count"),
)

# Типовий (SQL) порядок — саме він: [1, 2, 3, 4].
DOC_SORT_DOCS = [
    # номер «9» і 9 позицій — менші за «10» лише числово, не текстово
    {"id": 1, "filename": "б.pdf", "file_type": "pdf", "doc_type": "НАКЛАДНА",
     "status": "completed", "uploaded_at": 999999999, "doc_number": "9",
     "requested_by": "Іваненко", "requested_via": "7939", "transaction_count": 9},
    # номер «10» і 10 позицій; дата на секунду новіша за id=1, але рядок довший
    {"id": 2, "filename": "а.pdf", "file_type": "pdf", "doc_type": "ВИМОГА",
     "status": "queued", "uploaded_at": 1000000000, "doc_number": "10",
     "requested_by": "Петренко", "requested_via": "8110", "transaction_count": 10},
    # порожні номер, кількість, дата й «через кого»
    {"id": 3, "filename": "в.pdf", "file_type": "pdf", "doc_type": "",
     "status": "error", "uploaded_at": None, "doc_number": "",
     "requested_by": "", "requested_via": "", "transaction_count": None},
    # номер із провідними нулями — числово це 2143, тобто після 10
    {"id": 4, "filename": "г.pdf", "file_type": "excel", "doc_type": "НАКЛАДНА",
     "status": "processing_ocr", "uploaded_at": 1000000001, "doc_number": "0002143",
     "requested_by": "Іваненко", "requested_via": "7939", "transaction_count": 12},
]

# Виконує справжній JS зі сторінки в node: у браузері працюють ті самі функції.
_DOC_SORT_DRIVER = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
const idOf = list => list.map(d => d.id);
if (payload.mode === 'sort') {
    docSort = { key: payload.sort.key, dir: payload.sort.dir };
    console.log(JSON.stringify(idOf(applyDocSort(payload.docs))));
} else {
    // DOM і рендер підмінюються: перевіряється стан сортування, а не розмітка
    globalThis.document = { getElementById: () => null };
    const rendered = [];
    globalThis.renderDocs = docs => rendered.push(idOf(applyDocSort(docs)));
    lastRenderedDocs = payload.docs;
    const states = [];
    payload.clicks.forEach(key => { toggleDocSort(key); states.push(docSort.key + ':' + docSort.dir); });
    // автооновлення: рендер без кліку не має скидати стан
    if (payload.refresh) rendered.push(idOf(applyDocSort(payload.docs)));
    console.log(JSON.stringify({ states: states, rendered: rendered }));
}
"""


def _run_doc_sort(html, payload):
    """Проганяє сортувальний блок сторінки через node і повертає розібраний результат."""
    block = html.split(DOC_SORT_BLOCK_START, 1)[1].split(DOC_SORT_BLOCK_END, 1)[0]
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "doc_sort.js")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(block + _DOC_SORT_DRIVER)
        proc = subprocess.run([NODE, script], input=json.dumps(payload),
                              capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _sorted_ids(html, key, direction, docs=None):
    return _run_doc_sort(html, {"mode": "sort", "docs": docs or DOC_SORT_DOCS,
                                "sort": {"key": key, "dir": direction}})


async def _documents_page(warehouse_env):
    """Піднімає сторінку й віддає HTML разом із клієнтом і базою для закриття."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()
    return client, db, await (await client.get("/")).text()


@pytest.mark.asyncio
async def test_documents_headers_are_clickable_and_sortable(warehouse_env):
    """#25: девʼять змістовних колонок сортуються кліком, превʼю/розгортання/дії — ні."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        head = html.split('id="docs-tbody"')[0]

        for label, key in DOC_SORT_HEADERS:
            assert f'id="doc-sort-{key}"' in head, key
            assert f"toggleDocSort('{key}')" in head, key
            assert f'id="doc-sort-icon-{key}"' in head, key
            assert label in head, label

        # рівно девʼять сортованих заголовків — і жодного зайвого
        assert head.count("toggleDocSort(") == 9

        # колонки без змістовного значення лишились неклікабельними
        # (колонку розгортання розширено під мітку «не в обліку» — #29)
        assert '<th class="py-4 px-3 w-14"></th>' in head
        assert '<th class="py-4 px-3">Превʼю</th>' in head
        assert '<th class="py-4 px-3 text-right">Дії</th>' in head
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_documents_sort_state_lives_in_page_memory_and_applies_on_every_render(warehouse_env):
    """#25: стан сортування — поряд зі станом фільтра, застосовується при кожному рендері."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        # стан оголошено на рівні сторінки, поряд зі станом фільтра
        assert "let activeFilter = '';" in html
        assert "let docSort = { key: null, dir: null };" in html
        docs_head = html.split('id="docs-tbody"')[0]
        assert "let docSort" not in docs_head  # не в розмітці, а в скрипті

        # сортується саме переданий список (результат пошуку й фільтрів), а не allDocs
        render_docs = html.split("function renderDocs(docs)")[1].split("tbody.innerHTML = html;")[0]
        assert "lastRenderedDocs = docs;" in render_docs
        assert "applyDocSort(docs)" in render_docs
        assert "applyDocSort(allDocs)" not in html

        # клік перемальовує саме той список, який показано зараз
        assert "renderDocs(lastRenderedDocs);" in html

        # стан живе лише в памʼяті сторінки — перезавантаження його скидає
        assert "localStorage" not in html
        assert "sessionStorage" not in html
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_documents_sort_numbers_put_10_after_9(warehouse_env):
    """#25: номер документа й кількість позицій порівнюються числово, не текстово."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        # 9 → 10 → 2143, порожній номер завжди в кінці
        assert _sorted_ids(html, "doc_number", "asc") == [1, 2, 4, 3]
        assert _sorted_ids(html, "doc_number", "desc") == [4, 2, 1, 3]

        # кількість позицій: 9 → 10 → 12, порожня кількість у кінці
        assert _sorted_ids(html, "transaction_count", "asc") == [1, 2, 4, 3]
        assert _sorted_ids(html, "transaction_count", "desc") == [4, 2, 1, 3]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_documents_sort_date_uses_real_time(warehouse_env):
    """#25: дата сортується за часом, а не за рядком (1000000000 новіша за 999999999)."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        assert _sorted_ids(html, "uploaded_at", "asc") == [1, 2, 4, 3]
        assert _sorted_ids(html, "uploaded_at", "desc") == [4, 2, 1, 3]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_documents_sort_status_follows_lifecycle(warehouse_env):
    """#25: статуси шикуються за життєвим циклом, а не за алфавітом."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        # Черга → OCR → Вектори → Завершено → Помилка
        assert _sorted_ids(html, "status", "asc") == [2, 4, 1, 3]
        assert _sorted_ids(html, "status", "desc") == [3, 1, 4, 2]
        assert "DOC_STATUS_ORDER = ['queued', 'processing_ocr', 'processing_emb', 'completed', 'error']" in html
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_documents_sort_text_columns_and_empty_values_last(warehouse_env):
    """#25: текстові колонки сортуються, порожнє значення завжди в кінці — в обидва боки."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        # порожній тип документу лишається останнім і за зростанням, і за спаданням
        assert _sorted_ids(html, "doc_type", "asc") == [2, 1, 4, 3]
        assert _sorted_ids(html, "doc_type", "desc") == [1, 4, 2, 3]
        assert _sorted_ids(html, "filename", "asc") == [2, 1, 3, 4]

        # порожній «через кого» — теж у кінці
        assert _sorted_ids(html, "requested_via", "asc") == [1, 4, 2, 3]
        assert _sorted_ids(html, "requested_via", "desc") == [2, 1, 4, 3]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_documents_sort_click_cycle_returns_to_default_order(warehouse_env):
    """#25: зростання → спадання → типовий порядок; сортується одна колонка за раз."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        result = _run_doc_sort(html, {"mode": "cycle", "docs": DOC_SORT_DOCS,
                                      "clicks": ["doc_number", "doc_number", "doc_number"],
                                      "refresh": True})
        assert result["states"] == ["doc_number:asc", "doc_number:desc", "null:null"]
        assert result["rendered"][:3] == [[1, 2, 4, 3], [4, 2, 1, 3], [1, 2, 3, 4]]
        # автооновлення після третього кліку: типовий порядок зберігся
        assert result["rendered"][3] == [1, 2, 3, 4]

        # перехід на іншу колонку скидає попередню й починає зі зростання
        switch = _run_doc_sort(html, {"mode": "cycle", "docs": DOC_SORT_DOCS,
                                      "clicks": ["doc_number", "filename"], "refresh": True})
        assert switch["states"] == ["doc_number:asc", "filename:asc"]
        assert switch["rendered"][-1] == [2, 1, 3, 4]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_documents_sort_applies_to_filtered_subset_only(warehouse_env):
    """#25: сортується результат пошуку й фільтрів, а не повний список."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        subset = [DOC_SORT_DOCS[2], DOC_SORT_DOCS[0]]  # «10» у підмножині немає
        assert _sorted_ids(html, "doc_number", "asc", docs=subset) == [1, 3]
        assert _sorted_ids(html, "doc_number", "desc", docs=subset) == [1, 3]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_documents_sort_indicator_shows_column_and_direction(warehouse_env):
    """#25: видно, яка колонка активна і в якому напрямку."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        indicators = html.split("function renderDocSortIndicators()")[1].split("\n}\n")[0]
        assert "fa-sort-up" in indicators
        assert "fa-sort-down" in indicators
        assert "fa-sort " in indicators          # нейтральний стан неактивної колонки
        assert "docSort.key === key" in indicators
        assert "docSort.dir === 'desc'" in indicators

        # індикатор оновлюється після кожного кліку
        toggle = html.split("function toggleDocSort(key)")[1].split("\n}\n")[0]
        assert "renderDocSortIndicators();" in toggle
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_documents_keeps_sql_order(warehouse_env):
    """#25: сортування клієнтське — порядок із бази не змінюється."""
    db, fs, vs = warehouse_env
    first = db.add_document(filename="a.pdf", file_type="pdf")
    second = db.add_document(filename="b.pdf", file_type="pdf")

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        data = await (await client.get("/api/warehouse/documents")).json()
        assert [d["id"] for d in data] == [d["id"] for d in db.get_documents()]
        assert {first, second} == {d["id"] for d in data}
    finally:
        await client.close()
        db.close()


# =========================================================================
# Слайс #31: ручне дозаповнення полів документа
# =========================================================================

RECOGNITION_FIELDS = ("doc_type", "doc_number", "doc_date", "requested_by", "requested_via")


def _partial_photo_doc(db, **overrides):
    """OCR-накладна, у якій не розпізнано «Затребував»."""
    fields = {
        "filename": "nakladna_0000215.jpg",
        "file_type": "photo",
        "doc_type": "НАКЛАДНА",
        "doc_number": "0000215",
        "doc_date": "15.08.2026",
        "requested_by": "",
        "requested_via": "7939 - (ПІБ)",
    }
    fields.update(overrides)
    return db.add_document(**fields)


def _doc_with_income(db, **overrides):
    """Неповністю розпізнаний документ із приходом на 10 одиниць; повертає (doc_id, item_id)."""
    doc_id = _partial_photo_doc(db, **overrides)
    doc = db.get_document(doc_id)
    item_id = db.add_item(name="Болт М8", sku="SKU-001", unit="шт")
    db.add_transaction(
        item_id=item_id, document_id=doc_id, operation_type="income", quantity=10.0,
        doc_number=doc["doc_number"], doc_date=doc["doc_date"],
    )
    return doc_id, item_id


async def _web_client(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()
    return client


async def _edit_field(client, doc_id, field, value, comment=None):
    body = {"field": field, "value": value}
    if comment is not None:
        body["comment"] = comment
    return await client.post(f"/api/warehouse/documents/{doc_id}/edit", json=body)


@pytest.mark.asyncio
async def test_api_edit_document_fills_the_empty_field(warehouse_env):
    """Порожнє поле дозаповнюється окремим endpointʼом: поле, значення, коментар."""
    db, fs, vs = warehouse_env
    doc_id, _ = _doc_with_income(db, requested_by="")
    client = await _web_client(warehouse_env)

    try:
        resp = await _edit_field(client, doc_id, "requested_by", "комірник (ПІБ)", "OCR не прочитав")
        assert resp.status == 200
        data = await resp.json()

        assert data["success"] is True
        assert data["field"] == "requested_by"
        assert data["old_value"] == ""
        assert data["new_value"] == "комірник (ПІБ)"
        assert data["document"]["requested_by"] == "комірник (ПІБ)"
        assert data["document"]["missing_fields"] == []

        # картка документа показує дозаповнене значення
        card = await (await client.get(f"/api/warehouse/documents/{doc_id}/ocr")).json()
        assert card["requested_by"] == "комірник (ПІБ)"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["filename", "file_path", "raw_text", "status", "manual_edited", "user_id"])
async def test_api_edit_document_rejects_fields_outside_the_five(warehouse_env, field):
    """Дозволені рівно пʼять полів розпізнавання; будь-яке інше відхиляється."""
    db, fs, vs = warehouse_env
    doc_id = _partial_photo_doc(db)
    before = db.get_document(doc_id)
    client = await _web_client(warehouse_env)

    try:
        resp = await _edit_field(client, doc_id, field, "щось інше")

        assert resp.status == 400
        assert "Непідтримуване поле" in (await resp.json())["error"]
        assert db.get_document(doc_id) == before
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", list(RECOGNITION_FIELDS))
async def test_api_edit_document_accepts_every_recognition_field(warehouse_env, field):
    """Кожне з пʼяти полів бланка приймається endpointʼом."""
    db, fs, vs = warehouse_env
    doc_id = _partial_photo_doc(db)
    value = "ВИМОГА" if field == "doc_type" else "0002199"
    client = await _web_client(warehouse_env)

    try:
        resp = await _edit_field(client, doc_id, field, value)

        assert resp.status == 200
        assert db.get_document(doc_id)[field] == value
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_document_requires_field_and_value(warehouse_env):
    """Без поля чи без значення правка не приймається."""
    db, fs, vs = warehouse_env
    doc_id = _partial_photo_doc(db)
    client = await _web_client(warehouse_env)

    try:
        no_field = await client.post(f"/api/warehouse/documents/{doc_id}/edit", json={"value": "1"})
        assert no_field.status == 400
        assert "field" in (await no_field.json())["error"]

        no_value = await client.post(f"/api/warehouse/documents/{doc_id}/edit", json={"field": "doc_number"})
        assert no_value.status == 400
        assert "value" in (await no_value.json())["error"]

        assert db.get_document(doc_id)["doc_number"] == "0000215"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_document_unknown_id_is_not_found(warehouse_env):
    db, fs, vs = warehouse_env
    client = await _web_client(warehouse_env)
    try:
        assert (await _edit_field(client, 404, "doc_number", "1")).status == 404
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("doc_type", ["НАКЛАДНА", "ВИМОГА"])
async def test_api_edit_document_type_accepts_the_two_form_values(warehouse_env, doc_type):
    """Для типу документа приймаються лише «НАКЛАДНА» і «ВИМОГА»."""
    db, fs, vs = warehouse_env
    doc_id = _partial_photo_doc(db)
    client = await _web_client(warehouse_env)

    try:
        resp = await _edit_field(client, doc_id, "doc_type", doc_type)

        assert resp.status == 200
        assert db.get_document(doc_id)["doc_type"] == doc_type
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("value", ["АКТ", "Рахунок", "", "РУЧНЕ_КОРИГУВАННЯ", "НАКЛАДНА-ВИМОГА"])
async def test_api_edit_document_type_rejects_any_other_value(warehouse_env, value):
    """Інше значення типу документа відхиляється, документ лишається без змін."""
    db, fs, vs = warehouse_env
    doc_id = _partial_photo_doc(db)
    client = await _web_client(warehouse_env)

    try:
        resp = await _edit_field(client, doc_id, "doc_type", value)

        assert resp.status == 400
        assert "тип документа" in (await resp.json())["error"]
        assert db.get_document(doc_id)["doc_type"] == "НАКЛАДНА"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_document_marks_the_edit_in_documents_and_warehouse_tabs(warehouse_env):
    """Позначку ручного редагування видно і в таблиці документів, і на рядку документа у «Складі»."""
    db, fs, vs = warehouse_env
    doc_id, item_id = _doc_with_income(db, requested_by="")
    client = await _web_client(warehouse_env)

    try:
        docs = {d["id"]: d for d in (await (await client.get("/api/warehouse/documents")).json())}
        txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
        assert docs[doc_id]["manual_edited"] is False
        assert txs[0]["manual_edited"] is False

        await _edit_field(client, doc_id, "requested_by", "комірник (ПІБ)")

        docs = {d["id"]: d for d in (await (await client.get("/api/warehouse/documents")).json())}
        txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
        assert docs[doc_id]["manual_edited"] is True
        assert docs[doc_id]["missing_fields"] == []
        assert txs[0]["manual_edited"] is True
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_document_number_and_date_change_the_item_history(warehouse_env):
    """Правка номера й дати документа видна в історії транзакцій позиції у вкладці «Склад»."""
    db, fs, vs = warehouse_env
    doc_id, item_id = _doc_with_income(db)
    client = await _web_client(warehouse_env)

    try:
        await _edit_field(client, doc_id, "doc_number", "0002199")
        await _edit_field(client, doc_id, "doc_date", "01.09.2026")

        txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
        assert txs[0]["doc_number"] == "0002199"
        assert txs[0]["doc_date"] == "01.09.2026"
        assert txs[0]["document_number"] == "0002199"
        assert txs[0]["document_date"] == "01.09.2026"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_document_type_flips_the_operation_direction(warehouse_env):
    """Зміна типу документа перераховує напрямок операцій усіх його транзакцій."""
    db, fs, vs = warehouse_env
    doc_id, item_id = _doc_with_income(db, requested_by="комірник (ПІБ)")
    client = await _web_client(warehouse_env)

    try:
        await _edit_field(client, doc_id, "doc_type", "ВИМОГА")

        txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
        assert txs[0]["operation_type"] == "expense"
        items = await (await client.get("/api/warehouse/items")).json()
        assert items[0]["balance"] == -10.0

        await _edit_field(client, doc_id, "doc_type", "НАКЛАДНА")

        txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
        assert txs[0]["operation_type"] == "income"
        items = await (await client.get("/api/warehouse/items")).json()
        assert items[0]["balance"] == 10.0
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_document_moves_it_in_and_out_of_the_balances(warehouse_env):
    """Дозаповнення останнього поля вводить документ в облік, стирання поля — виводить."""
    db, fs, vs = warehouse_env
    doc_id, item_id = _doc_with_income(db, requested_by="")
    client = await _web_client(warehouse_env)

    try:
        items = await (await client.get("/api/warehouse/items")).json()
        txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
        assert items[0]["balance"] == 0.0
        assert items[0]["doc_count"] == 0
        assert txs[0]["accounted"] is False

        filled = await _edit_field(client, doc_id, "requested_by", "комірник (ПІБ)")

        assert (await filled.json())["document"]["missing_fields"] == []
        items = await (await client.get("/api/warehouse/items")).json()
        txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
        assert items[0]["balance"] == 10.0
        assert items[0]["doc_count"] == 1
        assert txs[0]["accounted"] is True

        cleared = await _edit_field(client, doc_id, "requested_by", "")

        assert (await cleared.json())["document"]["missing_fields"] == ["Затребував"]
        items = await (await client.get("/api/warehouse/items")).json()
        txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
        assert items[0]["balance"] == 0.0
        assert items[0]["doc_count"] == 0
        assert txs[0]["accounted"] is False
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_edit_document_writes_a_line_to_the_system_log(warehouse_env, caplog):
    """Правка пише рядок у системний лог — із полем, значенням і коментарем."""
    db, fs, vs = warehouse_env
    doc_id, _ = _doc_with_income(db)
    client = await _web_client(warehouse_env)

    try:
        with caplog.at_level(logging.INFO):
            await _edit_field(client, doc_id, "doc_number", "0002199", "OCR помилився")

        records = [r for r in caplog.records if r.name == "kolobot.web_server"]
        assert records, "правка не залишила рядка в лог"
        message = records[-1].getMessage()
        assert "0000215" in message
        assert "0002199" in message
        assert "№ документа" in message
        assert "OCR помилився" in message
    finally:
        await client.close()
        db.close()


# Виконує справжній JS сторінки в node: картка малюється, а правки йдуть на endpoint.
# Оточення браузера підставляється до сторінки, сам сценарій — після неї.
_DOC_EDIT_STUBS = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const els = {};
function el(id) {
    if (!els[id]) {
        const classes = new Set();
        els[id] = {
            id: id, innerHTML: '', textContent: '', innerText: '', value: '', type: '', style: {},
            classList: {
                add: c => classes.add(c),
                remove: c => classes.delete(c),
                toggle: (c, on) => { on ? classes.add(c) : classes.delete(c); },
                contains: c => classes.has(c)
            },
            addEventListener() {}, removeAttribute() {}, setAttribute() {},
            focus() {}, select() {}
        };
    }
    return els[id];
}
globalThis.document = { getElementById: el, querySelectorAll: () => [], addEventListener() {} };
globalThis.window = { EventSource: null, addEventListener() {} };
globalThis.alert = () => {};
globalThis.setInterval = () => 0;

const requests = [];
globalThis.fetch = async (url, opts) => {
    if (opts && opts.method === 'POST') requests.push({ url: url, body: JSON.parse(opts.body) });
    const body = url.indexOf('/ocr') !== -1 ? payload.card
        : url.indexOf('/items') !== -1 ? payload.items
        : url.indexOf('/documents') !== -1 ? payload.docs
        : {};
    return { ok: true, status: 200, json: async () => body };
};
"""

_DOC_EDIT_DRIVER = """
(async () => {
    const docId = payload.card.id;
    await fetchDocs();
    await reloadDocImpact(docId);
    const card = els['doc-impact-content-' + docId].innerHTML;

    // тип документа обирається зі списку, а не вводиться текстом
    openDocFieldModal(docId, 'doc_type');
    const typeEditor = {
        selectVisible: !el('edit-doc-type').classList.contains('hidden'),
        inputHidden: el('edit-new-value').classList.contains('hidden'),
        preselected: el('edit-doc-type').value
    };

    // користувач нічого не обрав — правка не йде
    el('edit-doc-type').value = '';
    await submitDocField();
    const afterEmptyChoice = { requests: requests.length, error: el('edit-error').textContent };

    el('edit-doc-type').value = payload.choice;
    await submitDocField();

    // текстове поле редагується полем вводу
    openDocFieldModal(docId, 'requested_by');
    const textEditor = {
        selectHidden: el('edit-doc-type').classList.contains('hidden'),
        inputVisible: !el('edit-new-value').classList.contains('hidden'),
        currentValue: el('edit-new-value').value
    };
    el('edit-new-value').value = payload.text;
    el('edit-comment').value = payload.comment;
    await submitDocField();

    // правка позиції складу не має піти на endpoint документа
    openEditModal(7, 'name', 'Болт М8', 'Найменування');
    const itemEditor = { docField: currentEditDocId, selectHidden: el('edit-doc-type').classList.contains('hidden') };

    console.log(JSON.stringify({
        card: card, typeEditor: typeEditor, textEditor: textEditor,
        afterEmptyChoice: afterEmptyChoice, itemEditor: itemEditor, requests: requests
    }));
})();
"""


def _run_doc_edit(html, payload):
    """Проганяє сторінку в node: рендер картки й обидва шляхи правки."""
    page = html.split("<script>", 1)[1].split("</script>", 1)[0]
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "doc_edit.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(_DOC_EDIT_STUBS + page + _DOC_EDIT_DRIVER)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        proc = subprocess.run([NODE, script, payload_path],
                              capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


_DOC_EDIT_CARD = {
    "id": 1,
    "filename": "nakladna_0000215.jpg",
    "file_type": "photo",
    "doc_type": "НАКЛАДНА",
    "doc_number": "0000215",
    "doc_date": "15.08.2026",
    "requested_by": "",
    "requested_via": "7939 - (ПІБ)",
    "raw_text": "НАКЛАДНА № 0000215",
    "impact": [],
    "status": "completed",
    "error_message": "",
}

_DOC_EDIT_PAYLOAD = {
    "card": _DOC_EDIT_CARD,
    "docs": [dict(_DOC_EDIT_CARD, manual_edited=False, missing_fields=["Затребував"],
                  transaction_count=0, uploaded_at=1.0)],
    "items": [],
    "choice": "ВИМОГА",
    "text": "комірник (ПІБ)",
    "comment": "OCR не прочитав",
}


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_document_card_has_a_pencil_in_every_recognition_field(warehouse_env):
    """#31: у картці кожне з пʼяти полів має олівець — і заповнене, і порожнє."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        result = _run_doc_edit(html, _DOC_EDIT_PAYLOAD)
        card = result["card"]

        # олівець кожного поля відкриває редактор саме цього поля
        for field in RECOGNITION_FIELDS:
            assert f"openDocFieldModal(1, '{field}')" in card, field
        assert card.count("openDocFieldModal(") == 5

        # порожнє поле — прочерк з олівцем
        assert '—</span><button onclick="event.stopPropagation(); openDocFieldModal(1, \'requested_by\')"' in card
        # заповнене — значенням з олівцем
        assert '0000215</span><button onclick="event.stopPropagation(); openDocFieldModal(1, \'doc_number\')"' in card

        # усі пʼять полів бланка присутні в картці
        for label in ("Тип", "№", "Дата", "Затребував", "Через кого"):
            assert f"{label}:" in card, label
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_document_card_edits_go_to_the_document_endpoint(warehouse_env):
    """#31: тип документа обирається зі списку, текстові поля — полем вводу; обидва йдуть на свій endpoint."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        result = _run_doc_edit(html, _DOC_EDIT_PAYLOAD)

        # тип документа: список із двох значень, поточне значення вже обране
        assert result["typeEditor"] == {"selectVisible": True, "inputHidden": True, "preselected": "НАКЛАДНА"}
        # без обраного типу правка не йде
        assert result["afterEmptyChoice"]["requests"] == 0
        assert result["afterEmptyChoice"]["error"]
        # текстове поле: поле вводу замість списку, з поточним значенням
        assert result["textEditor"] == {"selectHidden": True, "inputVisible": True, "currentValue": ""}
        # правка позиції складу не перехоплюється редактором документа
        assert result["itemEditor"] == {"docField": None, "selectHidden": True}

        assert result["requests"] == [
            {"url": "/api/warehouse/documents/1/edit",
             "body": {"field": "doc_type", "value": "ВИМОГА", "comment": ""}},
            {"url": "/api/warehouse/documents/1/edit",
             "body": {"field": "requested_by", "value": "комірник (ПІБ)", "comment": "OCR не прочитав"}},
        ]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_document_type_editor_offers_exactly_the_two_form_values(warehouse_env):
    """#31: список типів документа містить рівно «НАКЛАДНА» і «ВИМОГА»."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        modal = html.split('id="edit-doc-type"', 1)[1].split("</select>", 1)[0]
        assert modal.count("<option") == 2
        assert '<option value="НАКЛАДНА">' in modal
        assert '<option value="ВИМОГА">' in modal
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_manual_edit_mark_is_rendered_in_documents_and_warehouse_rows(warehouse_env):
    """#31: обидва рядки малюють позначку ручного редагування."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        docs_row = html.split("function renderDocs(docs)")[1].split("tbody.innerHTML = html;")[0]
        assert "manualEditMark(doc.manual_edited)" in docs_row

        tx_row = html.split("async function reloadTransactions(itemId)")[1].split("function toggleTransactions")[0]
        assert "manualEditMark(tx.manual_edited)" in tx_row

        mark = html.split("function manualEditMark(isEdited)")[1].split("\n}")[0]
        assert "title=\"Правка вручну\"" in mark
    finally:
        await client.close()
        db.close()


# ---- Слайс #26: підсвічування дублів «№ документа» ----

# Нормалізація номера — одна на сортування й на дублі: другої такої функції бути не має.
DOC_DUP_KEY_HELPER = "function normalizeDocNumber("

# Оточення браузера для всієї сторінки: рендер малює справжню розмітку, DOM лише приймає її.
_DOC_DUP_STUBS = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const els = {};
globalThis.document = {
    getElementById: id => (els[id] = els[id] || { innerHTML: '', style: {}, textContent: '' }),
    addEventListener() {},
};
globalThis.window = { addEventListener() {} };
"""

_DOC_DUP_DRIVER = """
allDocs = payload.docs;
docSort = payload.sort || { key: null, dir: null };
const shown = payload.shown ? allDocs.filter(d => payload.shown.indexOf(d.id) !== -1) : allDocs;
renderDocs(shown);
console.log(JSON.stringify({ html: els['docs-tbody'].innerHTML, sort: docSort }));
"""


def _run_doc_render(html, payload):
    """Малює таблицю документів справжнім JS сторінки в node і повертає розмітку тіла."""
    page = html.split("<script>", 1)[1].split("</script>", 1)[0]
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "doc_dup.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(_DOC_DUP_STUBS + page + _DOC_DUP_DRIVER)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        proc = subprocess.run([NODE, script, payload_path],
                              capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["html"]


def _rendered_doc_rows(markup):
    """Розбирає розмітку тіла: {id: класи рядка, класи клітинки «№ документа», її вміст}."""
    rows = {}
    for chunk in markup.split("<tr ")[1:]:
        if "doc-chevron-" not in chunk:
            continue
        doc_id = int(chunk.split("doc-chevron-")[1].split('"')[0])
        rows[doc_id] = {
            "row_class": chunk.split('class="', 1)[1].split('"', 1)[0],
            "cell_class": chunk.split('data-label="№ документа">')[0].rsplit('<td class="', 1)[1].split('"', 1)[0],
            "cell": chunk.split('data-label="№ документа">')[1].split("</td>")[0],
        }
    return rows


def _dup_doc(doc_id, doc_number):
    return {"id": doc_id, "filename": f"f{doc_id}.pdf", "file_type": "pdf", "doc_type": "НАКЛАДНА",
            "status": "completed", "uploaded_at": doc_id, "doc_number": doc_number,
            "requested_by": "", "requested_via": "", "transaction_count": doc_id}


DOC_DUP_DOCS = [
    # «№ 1234», «n 1234» і «1234» з різними пробілами та регістром — один номер, троє документів
    _dup_doc(1, "№ 1234"),
    _dup_doc(2, "n 1234"),
    _dup_doc(3, " 1234 "),
    # порожній номер дублем не вважається — навіть коли порожніх документів кілька
    _dup_doc(4, ""),
    _dup_doc(5, "   "),
    # провідні нулі не прибираються: це різні номери
    _dup_doc(6, "0002143"),
    _dup_doc(7, "2143"),
    # єдине входження
    _dup_doc(8, "9"),
]


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_duplicate_document_numbers_are_highlighted_with_a_twin_tooltip(warehouse_env):
    """#26: однаковий нормалізований номер підсвічує клітинку й показує, скільки ще двійників."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        rows = _rendered_doc_rows(_run_doc_render(html, {"docs": DOC_DUP_DOCS}))

        for doc_id in (1, 2, 3):
            assert "doc-dup" in rows[doc_id]["cell_class"], doc_id
            assert "fa-clone" in rows[doc_id]["cell"]
            assert 'title="Такий самий номер ще в 2 документах"' in rows[doc_id]["cell"], doc_id

        # підсвічується клітинка, а не рядок: клас рядка в усіх документах однаковий
        for doc_id, row in rows.items():
            assert "doc-dup" not in row["row_class"], doc_id
            assert row["row_class"] == "hover:bg-slate-800/40 transition cursor-pointer"

        # порожній номер (і самотній, і в компанії іншого порожнього) — не дубль
        for doc_id in (4, 5):
            assert "doc-dup" not in rows[doc_id]["cell_class"], doc_id
            assert "fa-clone" not in rows[doc_id]["cell"], doc_id

        # «0002143» і «2143» — різні номери, як і одиничне «9»
        for doc_id in (6, 7, 8):
            assert "doc-dup" not in rows[doc_id]["cell_class"], doc_id
            assert "fa-clone" not in rows[doc_id]["cell"], doc_id
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_duplicate_highlight_does_not_depend_on_sorting(warehouse_env):
    """#26: підсвічування працює незалежно від того, чи застосовано сортування."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        def highlighted(sort):
            rows = _rendered_doc_rows(_run_doc_render(html, {"docs": DOC_DUP_DOCS, "sort": sort}))
            order = list(rows)
            return order, {d: ("doc-dup" in r["cell_class"], r["cell"]) for d, r in rows.items()}

        default_order, default_marks = highlighted({"key": None, "dir": None})
        asc_order, asc_marks = highlighted({"key": "doc_number", "dir": "asc"})
        desc_order, desc_marks = highlighted({"key": "doc_number", "dir": "desc"})

        # порядок рядків різний — а підсвічування те саме;
        # порожні номери лишаються в кінці в обох напрямках
        assert default_order == [1, 2, 3, 4, 5, 6, 7, 8]
        assert asc_order == [8, 1, 2, 3, 6, 7, 4, 5]
        assert desc_order == [6, 7, 1, 2, 3, 8, 4, 5]
        assert asc_marks == default_marks
        assert desc_marks == default_marks
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_duplicate_count_covers_the_whole_list_not_the_filtered_one(warehouse_env):
    """#26: двійники рахуються по всьому завантаженому списку, а не по показаному."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        # показано лише один документ із трійці — підказка все одно про двох двійників
        rows = _rendered_doc_rows(_run_doc_render(html, {"docs": DOC_DUP_DOCS, "shown": [2]}))
        assert list(rows) == [2]
        assert "doc-dup" in rows[2]["cell_class"]
        assert 'title="Такий самий номер ще в 2 документах"' in rows[2]["cell"]

        # єдиний показаний документ без двійників лишається не підсвіченим
        lonely = _rendered_doc_rows(_run_doc_render(html, {"docs": DOC_DUP_DOCS, "shown": [8]}))
        assert "doc-dup" not in lonely[8]["cell_class"]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_doc_number_normalisation_is_shared_with_sorting(warehouse_env):
    """#26: ключ порівняння номера один — і для сортування, і для пошуку дублів."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        assert html.count(DOC_DUP_KEY_HELPER) == 1

        key_helper = html.split(DOC_DUP_KEY_HELPER)[1].split("\n}")[0]
        assert r".replace(/[\s№n]/gi, '').toLowerCase()" in key_helper

        # сортування номера йде через той самий ключ
        assert "compareDocNumbers(a, b)" in html
        assert "compareNumericValues(normalizeDocNumber(a), normalizeDocNumber(b))" in html
        assert "doc_number:        { get: d => d.doc_number,            compare: compareDocNumbers }" in html

        # пошук дублів — теж через нього, і саме по allDocs
        dup_block = html.split("function docNumberTwinCounts()")[1].split("\n}")[0]
        assert "normalizeDocNumber(d.doc_number)" in dup_block
        assert "allDocs.forEach" in dup_block
        assert "if (!key) return;" in dup_block
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_duplicate_highlight_touches_only_the_documents_table(warehouse_env):
    """#26: у вкладці «Склад» дублі не підсвічуються."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        render_items = html.split("function renderItems(items)")[1].split("tbody.innerHTML = html;")[0]
        assert "doc-dup" not in render_items

        render_docs = html.split("function renderDocs(docs)")[1].split("tbody.innerHTML = html;")[0]
        assert "doc-dup" in render_docs

        # стиль підсвітки оголошено один раз — фіолетовим, як badge-emb
        assert html.count(".doc-dup {") == 1
        assert ".doc-dup { background: rgba(168,85,247,0.15); color: #d8b4fe; }" in html
    finally:
        await client.close()
        db.close()


# ---- Слайс #29: мітка «не в обліку» та її фільтр у вкладці «Документи» ----

DOC_UNACCOUNTED_BLOCK_START = "// ---- Мітка «Не в обліку» та її фільтр (#29) ----"
DOC_UNACCOUNTED_BLOCK_END = "// ---- Кінець фільтра «Не в обліку» (#29) ----"

# Назви обовʼязкових полів беруться з єдиного джерела — REQUIRED_DOC_FIELDS.
# Фронтенд їх не перелічує: готовий перелік приходить у missing_fields.
DOC_REQUIRED_LABELS = tuple(label for label, _ in REQUIRED_DOC_FIELDS)

# Оточення браузера для всієї сторінки: /documents — список, /documents/<id>/ocr — картка.
_DOC_UNACCOUNTED_STUBS = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const els = {};
function el(id) {
    if (!els[id]) {
        const classes = new Set();
        els[id] = {
            id: id, innerHTML: '', textContent: '', innerText: '', value: '', type: '', style: {},
            classList: {
                add: c => classes.add(c),
                remove: c => classes.delete(c),
                contains: c => classes.has(c)
            },
            addEventListener() {}
        };
    }
    return els[id];
}
globalThis.document = { getElementById: el, querySelectorAll: () => [], addEventListener() {} };
globalThis.window = { addEventListener() {} };
globalThis.setTimeout = () => 0;
globalThis.clearTimeout = () => {};
globalThis.alert = () => {};

globalThis.fetch = async url => {
    const m = String(url).match(/\\/documents\\/(\\d+)\\/ocr/);
    const body = m ? (payload.cards[m[1]] || {}) : payload.docs;
    return { ok: true, status: 200, json: async () => body };
};
"""

_DOC_UNACCOUNTED_DRIVER = """
(async () => {
    const body = () => els['docs-tbody'].innerHTML;

    const shownIds = () => {
        const out = [];
        const re = /doc-chevron-(\\d+)/g;
        let m;
        while ((m = re.exec(body()))) out.push(Number(m[1]));
        return out;
    };

    // Вміст першої колонки рядка: усе після шеврона розгортання і до кінця клітинки.
    const marks = () => {
        const out = {};
        body().split('<tr ').forEach(chunk => {
            const at = chunk.indexOf('doc-chevron-');
            if (at === -1) return;
            const id = Number(chunk.substring(at + 'doc-chevron-'.length).split('"')[0]);
            out[id] = chunk.substring(chunk.indexOf('</i>') + 4).split('</td>')[0];
        });
        return out;
    };

    const state = () => ({
        ids: shownIds(), marks: marks(),
        count: el('filter-not-accounted-count').textContent,
        active: el('filter-not-accounted').classList.contains('bg-blue-600/30')
    });

    allDocs = payload.docs;
    docSort = payload.sort || { key: null, dir: null };
    await fetchDocs();                              // автооновлення малює список
    const initial = state();
    initial.markup = body();

    setDocFilter('not-accounted');
    const filtered = state();

    await fetchDocs();                              // автооновлення не скидає фільтр
    const refreshed = state();

    toggleDocSort('filename');                      // сортування — вже по відфільтрованому
    const sorted = state();

    setDocFilter('not-accounted');                  // повторний клік знімає фільтр
    const cleared = state();

    const cards = {};
    for (const id of payload.cardDocIds) {
        await reloadDocImpact(id);
        cards[id] = els['doc-impact-content-' + id].innerHTML;
    }

    console.log(JSON.stringify({initial, filtered, refreshed, sorted, cleared, cards}));
})();
"""


def _run_doc_unaccounted(html, payload):
    """Проганяє сторінку в node: мітку рядка, фільтр і картку розгортання."""
    page = html.split("<script>", 1)[1].split("</script>", 1)[0]
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "doc_unaccounted.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(_DOC_UNACCOUNTED_STUBS + page + _DOC_UNACCOUNTED_DRIVER)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        proc = subprocess.run([NODE, script, payload_path],
                              capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _row_of(markup, doc_id):
    """Розмітка одного рядка таблиці документів."""
    for chunk in markup.split("<tr ")[1:]:
        if f'doc-chevron-{doc_id}"' in chunk:
            return chunk
    raise AssertionError(f"рядок документа {doc_id} не знайдено")


def _first_cell_of(markup, doc_id):
    """Перша клітинка рядка документа — та, у якій стоїть шеврон і мітка «не в обліку»."""
    return _row_of(markup, doc_id).split("</td>", 1)[0]


def _mark_tooltip(markup, doc_id):
    """Текст підказки мітки «не в обліку» — те, що побачить користувач при наведенні."""
    return _row_of(markup, doc_id).split('title="', 1)[1].split('"', 1)[0]


def _unaccounted_doc(doc_id, filename, missing, file_type="pdf"):
    return {"id": doc_id, "filename": filename, "file_type": file_type,
            "doc_type": "НАКЛАДНА", "status": "completed", "uploaded_at": doc_id,
            "doc_number": f"№ {doc_id}", "requested_by": "", "requested_via": "",
            "transaction_count": doc_id, "missing_fields": list(missing)}


# Типовий (SQL) порядок — [1, 2, 3, 8, 9]: саме він приходить зі списку документів.
DOC_UNACCOUNTED_DOCS = [
    # повністю розпізнаний — мітки немає
    _unaccounted_doc(1, "а.pdf", []),
    # бракує двох полів — саме вони й мають бути в підказці; імʼя «я.pdf»
    # ставить його після «б.pdf» при сортуванні за файлом
    _unaccounted_doc(2, "я.pdf", ["№ документа", "Дата документа"]),
    # бракує всіх пʼяти
    _unaccounted_doc(3, "б.pdf", [label for label, _ in REQUIRED_DOC_FIELDS]),
    # excel і системний ручний документ під правило обліку не підпадають
    _unaccounted_doc(8, "г.xlsx", [], file_type="excel"),
    _unaccounted_doc(9, "Ручне редагування (Користувач)", [], file_type="manual"),
]

DOC_UNACCOUNTED_CARDS = {
    "2": {"id": 2, "filename": "я.pdf", "file_type": "photo", "doc_type": "НАКЛАДНА",
          "doc_number": "", "doc_date": "", "requested_by": "Іваненко", "requested_via": "",
          "raw_text": "текст", "impact": [], "status": "completed", "error_message": "",
          "missing_fields": ["№ документа", "Дата документа"]},
    "9": {"id": 9, "filename": "Ручне редагування (Користувач)", "file_type": "manual",
          "doc_type": "РУЧНЕ_КОРИГУВАННЯ", "doc_number": "", "doc_date": "",
          "requested_by": "", "requested_via": "", "raw_text": "системний документ",
          "impact": [], "status": "completed", "error_message": "", "missing_fields": []},
}

DOC_UNACCOUNTED_WARNING = "Документ не в обліку. Не розпізнано: "


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_unaccounted_document_gets_a_triangle_with_its_missing_fields(warehouse_env):
    """#29: жовтий трикутник у першій колонці, підказка перелічує саме не розпізнані поля."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        result = _run_doc_unaccounted(html, {"docs": DOC_UNACCOUNTED_DOCS, "cards": {},
                                             "cardDocIds": []})
        markup = result["initial"]["markup"]

        # трикутник стоїть у першій колонці рядка — перед превʼю, файлом і рештою
        row = _row_of(markup, 2)
        assert "fa-triangle-exclamation" in _first_cell_of(markup, 2)
        assert "text-amber-400" in _first_cell_of(markup, 2)
        assert row.index("fa-triangle-exclamation") < row.index('data-label="Превʼю"')

        # підказка перелічує рівно ті поля, яких бракує, у порядку REQUIRED_DOC_FIELDS
        assert _mark_tooltip(markup, 2) == DOC_UNACCOUNTED_WARNING + "№ документа, Дата документа"
        assert _mark_tooltip(markup, 3) == DOC_UNACCOUNTED_WARNING + ", ".join(DOC_REQUIRED_LABELS)

        # повністю розпізнаний документ мітки не має
        assert "fa-triangle-exclamation" not in _first_cell_of(markup, 1)
        assert result["initial"]["marks"]["1"] == ""

        # excel і системний ручний документ під правило не підпадають
        for doc_id in (8, 9):
            assert "fa-triangle-exclamation" not in _first_cell_of(markup, doc_id), doc_id
            assert result["initial"]["marks"][str(doc_id)] == "", doc_id
    finally:
        await client.close()
        db.close()


MANUAL_EDIT_SPAN = '<span class="text-amber-400" title="Правка вручну">'


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_manual_edit_mark_stands_next_to_the_unaccounted_triangle(warehouse_env):
    """Позначка ручного редагування живе в тій самій колонці, що й трикутник «не в обліку»."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        docs = [
            # не в обліку і правлений вручну — обидві позначки поряд
            dict(_unaccounted_doc(1, "а.pdf", ["Затребував"]), manual_edited=True),
            # лише правлений вручну — трикутника немає, позначка на своєму місці
            dict(_unaccounted_doc(2, "б.pdf", []), manual_edited=True),
            # повністю розпізнаний і не правлений — колонка порожня
            dict(_unaccounted_doc(3, "в.pdf", []), manual_edited=False),
        ]
        result = _run_doc_unaccounted(html, {"docs": docs, "cards": {}, "cardDocIds": []})
        markup = result["initial"]["markup"]

        assert result["initial"]["marks"]["3"] == ""

        # обидві позначки — у першій колонці, трикутник перед олівцем і без нічого між ними
        both = result["initial"]["marks"]["1"]
        assert "fa-triangle-exclamation" in both
        assert "fa-pen" in both
        assert both.index("fa-triangle-exclamation") < both.index("fa-pen")
        triangle_end = both.index("</span>") + len("</span>")
        assert both[triangle_end:both.index(MANUAL_EDIT_SPAN)].strip() == ""

        # самотня позначка правки не тягне за собою трикутник
        alone = result["initial"]["marks"]["2"]
        assert MANUAL_EDIT_SPAN in alone
        assert "fa-triangle-exclamation" not in alone

        # у колонці «Файл» позначки більше немає
        assert MANUAL_EDIT_SPAN not in _row_of(markup, 1).split('data-label="Файл"')[1].split("</td>")[0]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_unaccounted_mark_ignores_sorting_and_counts_the_whole_list(warehouse_env):
    """#29: мітка не залежить від сортування, а лічильник рахує весь завантажений список."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        payload = {"docs": DOC_UNACCOUNTED_DOCS, "cards": {}, "cardDocIds": []}
        result = _run_doc_unaccounted(html, payload)
        default_marks = result["initial"]["marks"]

        # лічильник показує всі необліковані документи — двох
        assert str(result["initial"]["count"]) == "2"

        # порядок рядків змінюється, мітки лишаються ті самі
        result = _run_doc_unaccounted(html, {**payload, "sort": {"key": "filename", "dir": "asc"}})
        assert result["initial"]["ids"] != [1, 2, 3, 8, 9]
        assert result["initial"]["marks"] == default_marks
        assert str(result["initial"]["count"]) == "2"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_unaccounted_filter_hides_accounted_rows_and_composes_with_sorting(warehouse_env):
    """#29: фільтр лишає тільки необліковані, переживає автооновлення, а сортує вже його результат."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        result = _run_doc_unaccounted(html, {"docs": DOC_UNACCOUNTED_DOCS, "cards": {},
                                             "cardDocIds": []})

        assert result["initial"]["ids"] == [1, 2, 3, 8, 9]
        assert result["initial"]["active"] is False

        # увімкнений фільтр лишає тільки документи з не розпізнаними полями
        assert result["filtered"]["ids"] == [2, 3]
        assert result["filtered"]["active"] is True
        # лічильник і далі рахує весь список, а не показані рядки
        assert str(result["filtered"]["count"]) == "2"

        # автооновлення не скидає ні фільтр, ні його результат
        assert result["refreshed"]["ids"] == [2, 3]
        assert result["refreshed"]["active"] is True

        # сортування застосовується вже до відфільтрованого списку: «б.pdf» перед «я.pdf»
        assert result["sorted"]["ids"] == [3, 2]

        # повторний клік знімає фільтр — весь список повертається
        assert sorted(result["cleared"]["ids"]) == [1, 2, 3, 8, 9]
        assert result["cleared"]["active"] is False
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_expanded_card_repeats_the_warning_with_the_same_missing_fields(warehouse_env):
    """#29: у розгорнутій картці — той самий перелік, що й у підказці мітки."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        cards = _run_doc_unaccounted(html, {"docs": DOC_UNACCOUNTED_DOCS,
                                            "cards": DOC_UNACCOUNTED_CARDS,
                                            "cardDocIds": [2, 9]})["cards"]

        assert DOC_UNACCOUNTED_WARNING + "№ документа, Дата документа" in cards["2"]
        assert "fa-triangle-exclamation" in cards["2"]

        # системний документ ручних коригувань попередження не отримує
        assert DOC_UNACCOUNTED_WARNING not in cards["9"]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_unaccounted_filter_button_follows_the_warehouse_filter_pattern(warehouse_env):
    """#29: кнопка фільтра — та сама розмітка й той самий стан, що й у вкладці «Склад»."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        assert "let docFilter = '';" in html
        assert "function setDocFilter(filter)" in html
        assert "function updateDocFilterUI()" in html
        assert "function filterDocs()" in html

        # кнопка з лічильником — у рядку фільтрів вкладки «Документи», за зразком «Складу»
        documents_panel = html.split('id="panel-documents"')[1].split("</main>")[0]
        assert 'onclick="setDocFilter(\'not-accounted\')"' in documents_panel
        assert 'id="filter-not-accounted"' in documents_panel
        assert 'id="filter-not-accounted-count"' in documents_panel
        assert "fa-triangle-exclamation text-amber-400" in documents_panel
        assert "bg-blue-600/30" in html.split("function updateDocFilterUI()")[1]

        # фільтр застосовується при кожному рендері — саме так його бачить автооновлення
        fetch_docs = html.split("async function fetchDocs()")[1].split("checkSmartPolling();")[0]
        assert "filterDocs();" in fetch_docs
        assert "renderDocs(allDocs);" not in fetch_docs

        # фільтри «Складу» не змінені
        assert "['below-min', 'negative', 'no-docs', 'dup-names', 'zeros']" in html
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_unaccounted_rule_is_not_duplicated_in_the_frontend(warehouse_env):
    """#29: перелік полів рахує бекенд — фронтенд лише показує готовий missing_fields."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        block = html.split(DOC_UNACCOUNTED_BLOCK_START, 1)[1].split(DOC_UNACCOUNTED_BLOCK_END, 1)[0]
        assert "doc.missing_fields" in block
        assert "allDocs.filter(isDocUnaccounted)" in block

        # жодної другої копії переліку обовʼязкових полів
        for label in DOC_REQUIRED_LABELS:
            assert label not in block, label

        # мітка рядка й попередження в картці теж беруть готовий перелік
        render_docs = html.split("function renderDocs(docs)")[1].split("tbody.innerHTML = html;")[0]
        assert "const missingFields = doc.missing_fields || [];" in render_docs
        card = html.split("async function reloadDocImpact(docId)")[1].split("// OCR Text Box")[0]
        assert "const missingFields = data.missing_fields || [];" in card
        assert "Документ не в обліку. Не розпізнано: " in card
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_document_ocr_endpoint_exposes_the_missing_fields_from_the_shared_helper(warehouse_env):
    """#29: картка розгортання отримує перелік із бекенду, а не рахує його сама."""
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()
    try:
        photo_id = db.add_document(filename="scan.jpg", file_type="photo", doc_type="НАКЛАДНА",
                                   doc_number="123", requested_by="Іваненко")
        excel_id = db.add_document(filename="import.xlsx", file_type="excel")
        manual_id = db.get_or_create_manual_document()

        photo = await (await client.get(f"/api/warehouse/documents/{photo_id}/ocr")).json()
        assert photo["missing_fields"] == ["Дата документа", "Через кого"]

        excel = await (await client.get(f"/api/warehouse/documents/{excel_id}/ocr")).json()
        assert excel["missing_fields"] == []

        manual = await (await client.get(f"/api/warehouse/documents/{manual_id}/ocr")).json()
        assert manual["missing_fields"] == []

        # той самий перелік, що й у таблиці документів
        docs = {d["id"]: d for d in db.get_documents()}
        assert docs[photo_id]["missing_fields"] == photo["missing_fields"]
    finally:
        await client.close()
        db.close()


# =========================================================================
# Слайс #30: невраховані документи в розгорнутій історії транзакцій позиції
# =========================================================================

# Історію малює єдина функція — поза нею неврахованих міток бути не має.
TX_HISTORY_BLOCK_START = "async function reloadTransactions(itemId)"
TX_HISTORY_BLOCK_END = "function toggleTransactions"

# Приглушення рядка і прочерк замість числа, якого немає в залишку позиції.
TX_ROW_DIM = "opacity-60"
TX_DASH_TITLE = "Документ не в обліку — кількість не входить у залишок"

# Оточення браузера для всієї сторінки: /transactions віддає історію, /items — позицію.
_TX_HISTORY_STUBS = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const els = {};
function el(id) {
    if (!els[id]) {
        els[id] = {
            id: id, innerHTML: '', textContent: '', innerText: '', value: '', type: '', style: {},
            classList: { add() {}, remove() {}, contains: () => false },
            addEventListener() {}
        };
    }
    return els[id];
}
globalThis.document = { getElementById: el, querySelectorAll: () => [], addEventListener() {} };
globalThis.window = { addEventListener() {} };
globalThis.setTimeout = () => 0;
globalThis.clearTimeout = () => {};
globalThis.alert = () => {};

globalThis.fetch = async url => {
    const body = String(url).indexOf('/transactions') !== -1 ? payload.txs : payload.items;
    return { ok: true, status: 200, json: async () => body };
};
"""

_TX_HISTORY_DRIVER = """
(async () => {
    allItems = payload.items;
    await reloadTransactions(payload.itemId);
    console.log(JSON.stringify({ html: els['tx-content-' + payload.itemId].innerHTML }));
})();
"""


def _run_tx_history(html, payload):
    """Проганяє сторінку в node: історію транзакцій малює справжній JS сторінки."""
    page = html.split("<script>", 1)[1].split("</script>", 1)[0]
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "tx_history.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(_TX_HISTORY_STUBS + page + _TX_HISTORY_DRIVER)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        proc = subprocess.run([NODE, script, payload_path],
                              capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["html"]


def _history_rows(markup):
    """Рядки історії транзакцій у порядку показу — без рядка заголовків."""
    return [chunk for chunk in markup.split("<tr ")[1:] if "<td " in chunk]


def _history_row_of(markup, filename):
    """Рядок історії, у якому згадано цей файл документа."""
    for row in _history_rows(markup):
        if filename in row:
            return row
    raise AssertionError(f"рядка з файлом {filename} в історії немає")


def _history_row_class(row):
    """Класи рядка історії — саме тут видно приглушення."""
    return row.split('class="', 1)[1].split('"', 1)[0]


def _history_cell(row, label):
    """Вміст клітинки рядка історії за підписом колонки."""
    for cell in row.split("<td ")[1:]:
        if f'data-label="{label}"' in cell:
            return cell.split(">", 1)[1].split("</td>", 1)[0]
    raise AssertionError(f"клітинки «{label}» у рядку немає")


def _history_cell_tooltip(row, label):
    """Текст підказки в клітинці рядка історії — те, що побачить користувач при наведенні."""
    return _history_cell(row, label).split('title="', 1)[1].split('"', 1)[0]


def _history_cell_text(row, label):
    """Видимий текст клітинки: розмітка не має вдавати число або прочерк."""
    return re.sub(r"<[^>]+>", "", _history_cell(row, label)).strip()


def _item_with_an_unaccounted_document(db):
    """Позиція з трьома транзакціями: два враховані документи і один неврахований.

    Неврахований приносить +50 і в залишок не входить, тож залишок позиції — 70.
    Повертає id позиції та id неврахованого документа.
    """
    item_id = db.add_item(name="Гайка М6", sku="NUT-M6", unit="шт")
    accounted_income = _partial_photo_doc(db, filename="nakladna_101.jpg", doc_number="101",
                                         requested_by="комірник (ПІБ)")
    unaccounted = _partial_photo_doc(db, filename="vymoha_215.jpg", doc_number="215")
    accounted_expense = _partial_photo_doc(db, filename="vymoha_216.jpg", doc_number="216",
                                           requested_by="комірник (ПІБ)", doc_type="ВИМОГА")
    db.add_transaction(item_id=item_id, document_id=accounted_income,
                       operation_type="income", quantity=100.0)
    db.add_transaction(item_id=item_id, document_id=unaccounted,
                       operation_type="income", quantity=50.0)
    db.add_transaction(item_id=item_id, document_id=accounted_expense,
                       operation_type="expense", quantity=30.0)
    return item_id, unaccounted


async def _history_payload(client, item_id):
    """Свіжі відповіді API: позиція зі своїм залишком і її історія транзакцій."""
    items = await (await client.get("/api/warehouse/items")).json()
    txs = await (await client.get(f"/api/warehouse/items/{item_id}/transactions")).json()
    item = next(i for i in items if i["id"] == item_id)
    return {"itemId": item_id, "items": [item], "txs": txs}


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_unaccounted_row_in_the_history_is_dimmed_with_a_triangle_and_a_dash(warehouse_env):
    """#30: неврахований рядок приглушено; у «Документі» — жовтий трикутник, у «Залишку» — прочерк."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        item_id, _ = _item_with_an_unaccounted_document(db)
        payload = await _history_payload(client, item_id)
        assert [tx["accounted"] for tx in payload["txs"]] == [True, False, True]
        markup = _run_tx_history(html, payload)

        unaccounted = _history_row_of(markup, "vymoha_215.jpg")
        accounted = _history_row_of(markup, "nakladna_101.jpg")

        # рядок видно приглушеним — а сусідній врахований ні
        assert TX_ROW_DIM in _history_row_class(unaccounted)
        assert TX_ROW_DIM not in _history_row_class(accounted)

        # трикутник стоїть у колонці «Документ» і перелічує причину тими самими словами, що й #29
        doc_cell = _history_cell(unaccounted, "Документ")
        assert "fa-triangle-exclamation" in doc_cell
        assert "text-amber-400" in doc_cell
        assert _history_cell_tooltip(unaccounted, "Документ") == DOC_UNACCOUNTED_WARNING + "Затребував"

        # у «Залишку» — прочерк, а не число, якого немає в залишку позиції
        dash = _history_cell_text(unaccounted, "Залишок")
        assert dash == "—"
        assert TX_DASH_TITLE in _history_cell(unaccounted, "Залишок")

        # у врахованого рядка число лишається на місці
        assert _history_cell_text(accounted, "Залишок") == "100"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_unaccounted_row_stays_in_the_history(warehouse_env):
    """#30: неврахований рядок не ховається — інакше незрозуміло, куди поділася кількість."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        item_id, _ = _item_with_an_unaccounted_document(db)
        payload = await _history_payload(client, item_id)
        markup = _run_tx_history(html, payload)

        # усі три рядки на місці, у порядку створення транзакцій
        rows = _history_rows(markup)
        assert len(rows) == len(payload["txs"]) == 3
        assert [tx["filename"] for tx in payload["txs"]] == [
            "nakladna_101.jpg", "vymoha_215.jpg", "vymoha_216.jpg"
        ]
        for tx in payload["txs"]:
            assert _history_row_of(markup, tx["filename"])

        # кількість неврахованого документа показана — видно, куди поділася кількість
        qty = _history_cell_text(_history_row_of(markup, "vymoha_215.jpg"), "Кількість")
        assert qty == "+50"
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_history_balance_matches_the_item_header(warehouse_env):
    """#30: накопичувальний залишок історії збігається із залишком у шапці — двох залишків на екрані немає."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        item_id, _ = _item_with_an_unaccounted_document(db)
        payload = await _history_payload(client, item_id)
        balance = payload["items"][0]["balance"]
        assert balance == 70.0                       # невраховані 50 у залишок не входять
        assert payload["txs"][-1]["running_balance"] == balance

        markup = _run_tx_history(html, payload)

        # шапка розгорнутої історії показує рівно залишок позиції
        header = markup.split("Поточний залишок:")[1].split("</div>")[0]
        assert f"{balance:g} шт" in header

        # останній рядок історії дає той самий залишок; неврахований рядок числа не додає
        shown = [_history_cell_text(row, "Залишок") for row in _history_rows(markup)]
        assert shown == ["100", "—", f"{balance:g}"]
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_the_unaccounted_mark_in_the_history_comes_from_the_backend(warehouse_env):
    """#30: приглушення й трикутник спираються на готові accounted і missing_fields."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        block = html.split(TX_HISTORY_BLOCK_START, 1)[1].split(TX_HISTORY_BLOCK_END, 1)[0]
        assert "tx.accounted === false" in block
        assert "tx.missing_fields" in block
        # підказка сформульована тими самими словами, що й у вкладці «Документи»
        assert DOC_UNACCOUNTED_WARNING in block

        # перелік полів не переказано у фронтенді: причину показує готовий missing_fields
        assert "missingFields.join(', ')" in block
        for label in DOC_REQUIRED_LABELS:
            assert f"'{label}'" not in block, label
        assert "file_type IN" not in block
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_item_row_and_manual_correction_row_get_no_unaccounted_marks(warehouse_env):
    """#30: приглушення й трикутник — лише в історії; рядок позиції та системний документ їх не мають."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        # рядок позиції складу не отримує нічого нового: його єдиний трикутник — «нижче мінімуму»
        render_items = html.split("function renderItems(items)")[1].split("tbody.innerHTML = html;")[0]
        assert "не в обліку" not in render_items
        assert TX_ROW_DIM not in render_items
        assert "Залишок менше мінімального!" in render_items

        item_id, unaccounted_doc = _item_with_an_unaccounted_document(db)
        # правка поля робить неврахований документ ручним, не повертаючи його в облік
        db.edit_document_field(unaccounted_doc, "requested_via", "7939 - (ПІБ)")
        manual_doc = db.get_or_create_manual_document()
        db.add_transaction(item_id=item_id, document_id=manual_doc,
                           operation_type="income", quantity=5.0)

        payload = await _history_payload(client, item_id)
        markup = _run_tx_history(html, payload)

        # системний документ ручних коригувань під правило обліку не підпадає
        manual_row = _history_row_of(markup, "Ручне редагування (Користувач)")
        assert "fa-user-pen" in _history_cell(manual_row, "Документ")
        assert "fa-triangle-exclamation" not in manual_row
        assert TX_ROW_DIM not in _history_row_class(manual_row)
        assert "—" not in _history_cell(manual_row, "Залишок")

        # а на неврахованому рядку поруч стоять два різні значки: трикутник і олівець правки
        row = _history_row_of(markup, "vymoha_215.jpg")
        assert "fa-triangle-exclamation" in row
        assert "fa-pen" in _history_cell(row, "Документ")
        assert 'title="Правка вручну"' in _history_cell(row, "Документ")
    finally:
        await client.close()
        db.close()


# ---- Слайс #33: попередження про втрату ручних правок при повторі ----

DELETE_MODAL_COMMENT = "<!-- Delete Confirmation Modal -->"
RETRY_MODAL_COMMENT = "<!-- Repeat Confirmation Modal -->"
RETRY_BLOCK_START = "// ---- Repeat ----"


def _modal_classes(html, comment):
    """Класи обгортки й картки вікна: [фон, картка]."""
    parts = html.split(comment, 1)[1].split('class="')
    return [parts[1].split('"', 1)[0], parts[2].split('"', 1)[0]]


def _retry_block(html):
    return html.split(RETRY_BLOCK_START, 1)[1].split("async function fetchDocs", 1)[0]


# Клік по «Повторити» виконується справжнім JS сторінки; запити лише збираються.
_DOC_REPEAT_STUBS = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const els = {};
function el(id) {
    if (!els[id]) {
        const classes = new Set();
        els[id] = {
            id: id, innerHTML: '', textContent: '', innerText: '', value: '', style: {}, onclick: null,
            classList: {
                add: c => classes.add(c),
                remove: c => classes.delete(c),
                contains: c => classes.has(c)
            }
        };
    }
    return els[id];
}
globalThis.document = { getElementById: el, addEventListener() {} };
globalThis.window = { addEventListener() {} };
globalThis.alert = () => {};

const requests = [];
globalThis.fetch = async (url, opts) => {
    requests.push(url);
    return { ok: true, status: 200, json: async () => (url.indexOf('/documents') !== -1 ? payload.docs : []) };
};
"""

_DOC_REPEAT_DRIVER = """
(async () => {
    allDocs = payload.docs;
    fetchDocs = async () => {};   // перезавантаження списку тут не перевіряється

    const retries = () => requests.filter(url => url.indexOf('/retry') !== -1);
    const snap = () => ({
        modalOpen: !el('retry-modal').classList.contains('hidden'),
        name: el('retry-doc-name').innerText,
        retries: retries(),
    });

    retryDocument(payload.docs[0].id);
    const afterClick = snap();

    if (payload.mode === 'confirm') {
        await el('confirm-retry-btn').onclick();
        console.log(JSON.stringify({ afterClick: afterClick, afterConfirm: snap() }));
    } else if (payload.mode === 'cancel') {
        closeRetryModal();
        console.log(JSON.stringify({ afterClick: afterClick, afterCancel: snap() }));
    } else {
        console.log(JSON.stringify({ afterClick: afterClick }));
    }
})();
"""

# Половина документа, якої досить для повтору: id, назва файлу й позначка правки.
_REPEAT_DOC = {"id": 7, "filename": "nakladna_101.jpg", "manual_edited": True}


def _run_repeat(html, docs, mode="none"):
    """Проганяє повтор у node: клік по кнопці, а далі — підтвердження, скасування або нічого."""
    page = html.split("<script>", 1)[1].split("</script>", 1)[0]
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "doc_repeat.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(_DOC_REPEAT_STUBS + page + _DOC_REPEAT_DRIVER)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump({"docs": docs, "mode": mode}, fh)
        proc = subprocess.run([NODE, script, payload_path],
                              capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _repeat_doc(doc_id, status, manual_edited):
    """Рядок документа для перевірки видимості кнопки «Повторити»."""
    return {"id": doc_id, "filename": f"f{doc_id}.pdf", "file_type": "pdf", "doc_type": "НАКЛАДНА",
            "status": status, "uploaded_at": doc_id, "doc_number": str(doc_id),
            "requested_by": "", "requested_via": "", "transaction_count": 0,
            "manual_edited": manual_edited}


def _rows_with_the_repeat_button(markup):
    """id рядків, у яких намальовано кнопку «Повторити»."""
    return [int(chunk.split("doc-chevron-")[1].split('"', 1)[0])
            for chunk in markup.split("<tr ")[1:]
            if "doc-chevron-" in chunk and "retryDocument(" in chunk]


@pytest.mark.asyncio
async def test_repeat_warning_reuses_the_delete_confirmation_style(warehouse_env):
    """#33: попередження — така сама картка, як підтвердження видалення, а не діалог браузера."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        delete_overlay, delete_card = _modal_classes(html, DELETE_MODAL_COMMENT)
        retry_overlay, retry_card = _modal_classes(html, RETRY_MODAL_COMMENT)

        # та сама обгортка й та сама картка — відрізняється лише колір попередження
        assert retry_overlay == delete_overlay
        assert retry_card == delete_card.replace("red", "amber")

        # усередині — назва файлу, «Скасувати» і підтвердження
        modal = html.split(RETRY_MODAL_COMMENT, 1)[1].split("<!--", 1)[0]
        assert modal.count("<button") == 2
        assert 'id="retry-doc-name"' in modal
        assert 'id="confirm-retry-btn"' in modal
        assert "closeRetryModal()" in modal
        assert "ручні правки буде втрачено" in modal

        # жодного системного діалогу браузера на шляху повтору
        block = _retry_block(html)
        assert "confirm(" not in block
        assert "retryDocument" in block and "/retry" in block
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_repeat_of_a_manually_edited_document_warns_before_retrying(warehouse_env):
    """#33: документ із позначкою правки спершу питає, і лише підтвердження запускає повтор."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        retry_url = f"/api/warehouse/documents/{_REPEAT_DOC['id']}/retry"
        result = _run_repeat(html, [_REPEAT_DOC], mode="confirm")

        # клік по кнопці спиняється на попередженні з назвою файлу — повтору ще немає
        assert result["afterClick"] == {
            "modalOpen": True,
            "name": _REPEAT_DOC["filename"],
            "retries": [],
        }
        # підтвердження у вікні повторює документ і закриває вікно
        assert result["afterConfirm"] == {"modalOpen": False, "name": _REPEAT_DOC["filename"],
                                          "retries": [retry_url]}
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_cancelling_the_repeat_warning_does_not_retry(warehouse_env):
    """#33: «Скасувати» закриває вікно й не чіпає документ."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        result = _run_repeat(html, [_REPEAT_DOC], mode="cancel")

        assert result["afterClick"]["retries"] == []
        assert result["afterCancel"]["modalOpen"] is False
        assert result["afterCancel"]["retries"] == []
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_repeat_without_manual_edits_goes_straight_through(warehouse_env):
    """#33: без позначки правки вікна немає — кнопка повторює документ одразу."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        doc = dict(_REPEAT_DOC, manual_edited=False)
        result = _run_repeat(html, [doc])

        assert result["afterClick"] == {
            "modalOpen": False,
            "name": "",
            "retries": [f"/api/warehouse/documents/{doc['id']}/retry"],
        }
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_repeat_button_stays_visible_only_for_error_documents(warehouse_env):
    """#33: обсяг кнопки «Повторити» не змінився — вона лишається лише для статусу «помилка»."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        docs = [
            _repeat_doc(1, "completed", manual_edited=True),
            _repeat_doc(2, "error", manual_edited=False),
            _repeat_doc(3, "error", manual_edited=True),
            _repeat_doc(4, "processing_ocr", manual_edited=True),
            _repeat_doc(5, "queued", manual_edited=True),
        ]
        markup = _run_doc_render(html, {"docs": docs, "sort": {"key": None, "dir": None}})

        assert _rows_with_the_repeat_button(markup) == [2, 3]
    finally:
        await client.close()
        db.close()


# ---- Підказка до позначок у вкладці «Документи» ----

DOC_LEGEND_START = "// ---- Підказка до позначок таблиці ----"
DOC_LEGEND_END = "// ---- Кінець підказки до позначок таблиці ----"

# Перший документ — і «не в обліку» (бракує тієї самої дати, що й у прикладі підказки), і
# ручна правка. Три документи з одним номером дають кожному з них двох двійників — рівно
# стільки, скільки обіцяє приклад підказки.
DOC_LEGEND_DOCS = [
    dict(_unaccounted_doc(1, "а.pdf", ["Дата документа"]), manual_edited=True),
    dict(_unaccounted_doc(2, "б.pdf", []), doc_number="№ 7"),
    dict(_unaccounted_doc(3, "в.pdf", []), doc_number="№ 7"),
    dict(_unaccounted_doc(4, "г.pdf", []), doc_number="№ 7"),
]

# Оточення браузера те саме, що й у слайсі #29: сторінка цілком, DOM лише приймає розмітку.
_DOC_LEGEND_DRIVER = """
(async () => {
    allDocs = payload.docs;
    renderDocLegend();
    const legend = els['doc-legend-body'].innerHTML;

    await fetchDocs();
    const table = els['docs-tbody'].innerHTML;
    const samples = {
        triangle: docUnaccountedMark(['Дата документа']),
        pen: manualEditMark(true),
        twin: docNumberTwinMark(2)
    };
    // Підказка показує ту саму розмітку, що й рядки таблиці: де саме стоїть позначка в
    // рядку — справа тестів рядка, тут важлива лише тотожність розмітки.
    const shown = {};
    for (const key in samples) {
        shown[key] = legend.includes(samples[key]) && table.includes(samples[key]);
    }
    console.log(JSON.stringify({legend: legend, shown: shown}));
})();
"""


def _run_doc_legend(html, docs):
    """Проганяє сторінку в node: підказка й рядки таблиці мають показати ті самі позначки."""
    page = html.split("<script>", 1)[1].split("</script>", 1)[0]
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "doc_legend.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(_DOC_UNACCOUNTED_STUBS + page + _DOC_LEGEND_DRIVER)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump({"docs": docs}, fh)
        proc = subprocess.run([NODE, script, payload_path],
                              capture_output=True, text=True, encoding="utf-8")
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.asyncio
async def test_documents_tab_carries_a_collapsible_hint_above_the_table(warehouse_env):
    """Підказка — нативний <details> над таблицею: згортається, але лишається підписаною."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        panel = html.split('<main id="panel-documents"', 1)[1].split('id="docs-tbody"', 1)[0]
        assert panel.index("doc-legend") < panel.index("<table")

        # єдиний розгортуваний блок на вкладці, розгорнутий за замовчуванням
        assert panel.count("<details") == 1
        assert 'class="glass rounded-2xl mb-6 doc-legend" open' in panel

        legend = panel.split("<details", 1)[1].split("</details>", 1)[0]
        assert legend.count("<summary") == 1
        # згорнутий блок усе одно читається як пояснення: заголовок лишається на екрані
        summary = legend.split("<summary", 1)[1].split("</summary>", 1)[0]
        assert "fa-circle-info" in summary
        assert "Підказка" in summary
        assert "позначки в таблиці" in summary

        # тіло наповнює сторінка, а системний маркер <summary> прибирає CSS
        assert 'id="doc-legend-body"' in legend
        assert ".doc-legend > summary { list-style: none; }" in html
        assert ".doc-legend > summary::-webkit-details-marker { display: none; }" in html
        assert ".doc-legend[open] .doc-legend-arrow { transform: rotate(180deg); }" in html

        # малюється один раз, на ініціалізації, а не при кожному оновленні списку
        assert "renderDocLegend();" in html.split("document.addEventListener('DOMContentLoaded'", 1)[1]
        assert html.count("function renderDocLegend(") == 1
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
@pytest.mark.skipif(NODE is None, reason="node недоступний — JS сторінки не виконати")
async def test_documents_hint_repeats_the_exact_marks_and_tooltips_of_the_table(warehouse_env):
    """Підказка малює ті самі позначки, що й рядки, і цитує їхні справжні підказки."""
    client, db, html = await _documents_page(warehouse_env)
    try:
        result = _run_doc_legend(html, DOC_LEGEND_DOCS)
        legend = result["legend"]

        # три пояснення — за три позначки, і кожне з прикладом
        assert legend.count("Приклад:") == 3
        for label in ("Не в обліку", "Ручне редагування", "Дубль номера"):
            assert label in legend, label

        # приклади цитують підказки, які користувач бачить при наведенні на позначку
        assert "«Документ не в обліку. Не розпізнано: Дата документа»" in legend
        assert "«Правка вручну»" in legend
        assert "«Такий самий номер ще в 2 документах»" in legend

        # фіолетовий зразок клітинки номера — той самий клас, що й у рядку таблиці
        assert '<span class="doc-dup px-1.5 py-0.5 rounded font-mono">№ 7</span>' in legend

        # самі позначки — не переказ, а та сама розмітка, що в рядках
        assert result["shown"] == {"triangle": True, "pen": True, "twin": True}
    finally:
        await client.close()
        db.close()

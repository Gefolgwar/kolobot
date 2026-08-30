"""Tests for embedded WebServer routes and warehouse API."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from kolobot.warehouse_db import WarehouseDB
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
    client = TestClient(TestServer(server._app))
    await client.start_server()

    try:
        resp = await client.get("/")
        assert resp.status == 200
        text = await resp.text()
        assert "kolobot" in text
    finally:
        await client.close()
        db.close()


@pytest.mark.asyncio
async def test_api_items_empty(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server._app))
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
    client = TestClient(TestServer(server._app))
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
    client = TestClient(TestServer(server._app))
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
    client = TestClient(TestServer(server._app))
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

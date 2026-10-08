"""Tests for feat(m11): link indicators on Documents tab (Issue #50)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from unittest.mock import MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from kolobot.warehouse_db import WarehouseDB
from kolobot.web.assets import JS, PAGE
from kolobot.web_server import WebServer

NODE = shutil.which("node")


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


# ==============================================================================
# 1. Database layer tests: get_documents() and get_document_links_map()
# ==============================================================================


def test_get_documents_includes_link_fields_for_all_docs(warehouse_env):
    """GET /api/warehouse/documents (via db.get_documents) includes link information."""
    db, _, _ = warehouse_env

    # 1. Classic ВИМОГА
    vimoga_id = db.add_document(
        filename="vimoga_1.pdf",
        file_type="pdf",
        doc_type="ВИМОГА",
        doc_number="101",
        doc_date="2026-03-01",
    )

    # 2. M-11 document
    m11_id = db.add_document(
        filename="m11_1.pdf",
        file_type="pdf",
        doc_type="ВИМОГА М-11",
        doc_number="42",
        doc_date="2026-03-01",
    )

    # 3. Regular НАКЛАДНА
    nakladna_id = db.add_document(
        filename="nakladna_1.pdf",
        file_type="pdf",
        doc_type="НАКЛАДНА",
        doc_number="555",
        doc_date="2026-03-01",
    )

    # Before linking:
    docs = {d["id"]: d for d in db.get_documents()}
    assert len(docs) == 3

    # Classic ВИМОГА unlinked
    v_doc = docs[vimoga_id]
    assert v_doc["linked_doc_id"] is None
    assert v_doc["linked_doc_number"] is None
    assert v_doc["match_status"] is None
    assert v_doc["needs_review"] == 0

    # M-11 unlinked
    m_doc = docs[m11_id]
    assert m_doc["linked_doc_id"] is None
    assert m_doc["linked_doc_number"] is None
    assert m_doc["match_status"] == "none"
    assert m_doc["needs_review"] == 0

    # НАКЛАДНА unlinked
    n_doc = docs[nakladna_id]
    assert n_doc["linked_doc_id"] is None
    assert n_doc["match_status"] is None
    assert n_doc["needs_review"] == 0

    # Now add link between M-11 and ВИМОГА (full match)
    db.add_document_link(
        m11_doc_id=m11_id,
        vimoga_doc_id=vimoga_id,
        match_status="full",
        needs_review=0,
    )

    docs_linked = {d["id"]: d for d in db.get_documents()}
    v_linked = docs_linked[vimoga_id]
    m_linked = docs_linked[m11_id]

    # Classic ВИМОГА row points to M-11
    assert v_linked["linked_doc_id"] == m11_id
    assert v_linked["linked_doc_number"] == "42"
    assert v_linked["match_status"] == "full"
    assert v_linked["needs_review"] == 0

    # M-11 row points to ВИМОГА
    assert m_linked["linked_doc_id"] == vimoga_id
    assert m_linked["linked_doc_number"] == "101"
    assert m_linked["match_status"] == "full"
    assert m_linked["needs_review"] == 0


def test_get_documents_conflict_sets_needs_review(warehouse_env):
    """When a document link has needs_review = 1, both sides reflect it."""
    db, _, _ = warehouse_env

    vimoga_id = db.add_document(
        filename="vimoga.pdf",
        file_type="pdf",
        doc_type="ВИМОГА",
        doc_number="101",
    )
    m11_id = db.add_document(
        filename="m11.pdf",
        file_type="pdf",
        doc_type="ВИМОГА М-11",
        doc_number="42",
    )

    db.add_document_link(
        m11_doc_id=m11_id,
        vimoga_doc_id=vimoga_id,
        match_status="partial",
        needs_review=1,
    )

    docs = {d["id"]: d for d in db.get_documents()}
    assert docs[vimoga_id]["needs_review"] == 1
    assert docs[m11_id]["needs_review"] == 1
    assert docs[m11_id]["match_status"] == "partial"
    assert docs[vimoga_id]["match_status"] == "partial"


# ==============================================================================
# 2. API endpoint test: GET /api/warehouse/documents
# ==============================================================================


@pytest.mark.asyncio
async def test_api_documents_endpoint_returns_link_data(warehouse_env):
    """GET /api/warehouse/documents endpoint returns link fields for all documents."""
    db, fs, vs = warehouse_env

    vimoga_id = db.add_document(
        filename="v1.pdf",
        file_type="pdf",
        doc_type="ВИМОГА",
        doc_number="V-10",
        doc_date="2026-03-01",
    )
    m11_id = db.add_document(
        filename="m1.pdf",
        file_type="pdf",
        doc_type="ВИМОГА М-11",
        doc_number="M-20",
        doc_date="2026-03-01",
    )
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
        resp = await client.get("/api/warehouse/documents")
        assert resp.status == 200
        data = await resp.json()
        assert len(data) == 2

        by_id = {d["id"]: d for d in data}
        v = by_id[vimoga_id]
        m = by_id[m11_id]

        assert v["doc_type"] == "ВИМОГА"
        assert v["linked_doc_id"] == m11_id
        assert v["linked_doc_number"] == "M-20"
        assert v["match_status"] == "full"
        assert v["needs_review"] == 0

        assert m["doc_type"] == "ВИМОГА М-11"
        assert m["linked_doc_id"] == vimoga_id
        assert m["linked_doc_number"] == "V-10"
        assert m["match_status"] == "full"
        assert m["needs_review"] == 0
    finally:
        await client.close()
        db.close()


# ==============================================================================
# 3. Frontend rendering tests: 10-documents_render.js in Node.js
# ==============================================================================


_NODE_STUBS = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const els = {};
function el(id) {
    if (!els[id]) {
        els[id] = { id, innerHTML: '', textContent: '', classList: { add() {}, remove() {}, contains: () => false } };
    }
    return els[id];
}

globalThis.document = { getElementById: el, querySelectorAll: () => [], addEventListener() {} };
globalThis.window = { addEventListener() {} };
"""

_NODE_RUNNER = """
allDocs = payload.docs;
renderDocs(allDocs);

console.log(JSON.stringify({ html: els['docs-tbody'].innerHTML }));
"""


def _run_render_docs(docs):
    page = "\n".join(v for k, v in JS.items() if k != "m11")
    with tempfile.TemporaryDirectory() as tmp:
        script_path = os.path.join(tmp, "render.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(_NODE_STUBS + "\n" + page + "\n" + _NODE_RUNNER)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump({"docs": docs}, fh)
        proc = subprocess.run(
            [NODE, script_path, payload_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["html"]


@pytest.mark.skipif(not NODE, reason="node not available")
def test_frontend_classic_vimoga_with_linked_m11_shows_link_icon():
    """Classic ВИМОГА with linked M-11 shows link icon with tooltip 'Пов'язана з М-11 №...'."""
    docs = [
        {
            "id": 1,
            "filename": "vimoga.pdf",
            "file_type": "pdf",
            "doc_type": "ВИМОГА",
            "doc_number": "101",
            "uploaded_at": 1000,
            "transaction_count": 2,
            "missing_fields": [],
            "linked_doc_id": 2,
            "linked_doc_number": "42",
            "match_status": "full",
            "needs_review": 0,
        }
    ]
    html = _run_render_docs(docs)
    assert 'fa-link' in html
    assert 'title="Пов\'язана з М-11 №42"' in html


@pytest.mark.skipif(not NODE, reason="node not available")
def test_frontend_clean_baseline_documents_show_no_extra_indicators():
    """Documents without links (classic ВИМОГА or НАКЛАДНА) show no link or warning icons."""
    docs = [
        {
            "id": 1,
            "filename": "vimoga_unlinked.pdf",
            "file_type": "pdf",
            "doc_type": "ВИМОГА",
            "doc_number": "101",
            "uploaded_at": 1000,
            "transaction_count": 2,
            "missing_fields": [],
            "linked_doc_id": None,
            "linked_doc_number": None,
            "match_status": None,
            "needs_review": 0,
        },
        {
            "id": 2,
            "filename": "nakladna.pdf",
            "file_type": "pdf",
            "doc_type": "НАКЛАДНА",
            "doc_number": "202",
            "uploaded_at": 1001,
            "transaction_count": 5,
            "missing_fields": [],
            "linked_doc_id": None,
            "linked_doc_number": None,
            "match_status": None,
            "needs_review": 0,
        },
    ]
    html = _run_render_docs(docs)
    assert 'fa-link' not in html
    assert 'fa-triangle-exclamation' not in html
    assert 'fa-circle' not in html


@pytest.mark.skipif(not NODE, reason="node not available")
def test_frontend_m11_documents_excluded_from_documents_table():
    """M-11 documents do not appear as rows in the Documents tab table."""
    docs = [
        # M-11 documents of different formats/cases
        {
            "id": 10,
            "filename": "m11_full.pdf",
            "file_type": "pdf",
            "doc_type": "ВИМОГА М-11",
            "doc_number": "М-1",
            "uploaded_at": 1000,
            "transaction_count": 0,
            "missing_fields": [],
        },
        {
            "id": 20,
            "filename": "m11_lower.pdf",
            "file_type": "pdf",
            "doc_type": "м-11",
            "doc_number": "М-2",
            "uploaded_at": 1001,
            "transaction_count": 0,
            "missing_fields": [],
        },
        # Classic document that SHOULD be rendered
        {
            "id": 30,
            "filename": "nakladna.pdf",
            "file_type": "pdf",
            "doc_type": "НАКЛАДНА",
            "doc_number": "Н-3",
            "uploaded_at": 1002,
            "transaction_count": 2,
            "missing_fields": [],
        },
    ]
    html = _run_render_docs(docs)
    assert 'm11_full.pdf' not in html
    assert 'm11_lower.pdf' not in html
    assert 'nakladna.pdf' in html


@pytest.mark.skipif(not NODE, reason="node not available")
def test_frontend_document_with_needs_review_shows_warning_icon():
    """Documents with needs_review = 1 show warning icon (fa-triangle-exclamation)."""
    docs = [
        {
            "id": 5,
            "filename": "vimoga_conflict.pdf",
            "file_type": "pdf",
            "doc_type": "ВИМОГА",
            "doc_number": "500",
            "uploaded_at": 1000,
            "transaction_count": 1,
            "missing_fields": [],
            "linked_doc_id": 10,
            "linked_doc_number": "M-50",
            "match_status": "partial",
            "needs_review": 1,
        }
    ]
    html = _run_render_docs(docs)
    assert 'fa-triangle-exclamation' in html
    assert 'title="Потребує перевірки"' in html

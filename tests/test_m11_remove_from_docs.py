"""Tests for issue #53: feat(m11): remove M-11 from Documents tab + boot fetch."""

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


def test_boot_js_calls_fetch_m11_docs():
    """fetchM11Docs() is called on page boot in 17-boot.js."""
    boot_js = JS.get("17-boot", JS.get("boot", ""))
    assert "fetchM11Docs()" in boot_js, "fetchM11Docs() must be called in 17-boot.js"
    assert "refreshAll()" in boot_js, "refreshAll() must be called in 17-boot.js"


def test_refresh_all_wrapped_to_call_fetch_m11_docs():
    """refreshAll() refreshes both classic documents/items and allM11Docs."""
    m11_js = JS.get("18-m11", JS.get("m11", ""))
    assert "refreshAll" in m11_js
    assert "fetchM11Docs()" in m11_js


@pytest.mark.asyncio
async def test_all_docs_backend_still_contains_m11(warehouse_env):
    """allDocs array from /api/warehouse/documents still contains M-11 documents (no backend changes)."""
    db, fs, vs = warehouse_env

    vimoga_id = db.add_document(
        filename="vimoga.pdf",
        file_type="pdf",
        doc_type="ВИМОГА",
        doc_number="В-100",
    )
    m11_id = db.add_document(
        filename="m11.pdf",
        file_type="pdf",
        doc_type="ВИМОГА М-11",
        doc_number="М-200",
    )

    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/api/warehouse/documents")
        assert resp.status == 200
        data = await resp.json()
        doc_ids = [d["id"] for d in data]
        assert vimoga_id in doc_ids
        assert m11_id in doc_ids
        # Verify M-11 doc is still in the response array
        m11_doc = next(d for d in data if d["id"] == m11_id)
        assert m11_doc["doc_type"] == "ВИМОГА М-11"
    finally:
        await client.close()
        db.close()


_NODE_TEST_HARNESS = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const els = {};
function el(id) {
    if (!els[id]) {
        els[id] = { id, innerHTML: '', textContent: '', innerText: '', classList: { add() {}, remove() {}, contains: () => false } };
    }
    return els[id];
}

globalThis.document = {
    getElementById: el,
    querySelectorAll: () => [],
    addEventListener() {}
};
globalThis.window = { addEventListener() {} };
"""


def _run_node_script(runner_code: str, payload_data: dict) -> dict:
    page = "\n".join(JS.values())
    with tempfile.TemporaryDirectory() as tmp:
        script_path = os.path.join(tmp, "test_runner.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(_NODE_TEST_HARNESS + "\n" + page + "\n" + runner_code)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload_data, fh)
        proc = subprocess.run(
            [NODE, script_path, payload_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.skipif(not NODE, reason="node not available")
def test_is_m11_doc_case_insensitive():
    """isM11Doc recognizes 'ВИМОГА М-11' and 'М-11' case-insensitively and handles Cyrillic/Latin."""
    runner = """
    const results = payload.testCases.map(tc => isM11Doc({ doc_type: tc.input }));
    console.log(JSON.stringify({ results }));
    """
    cases = [
        {"input": "ВИМОГА М-11", "expected": True},
        {"input": "вимога м-11", "expected": True},
        {"input": "Вимога М-11", "expected": True},
        {"input": "  ВИМОГА   М-11  ", "expected": True},
        {"input": "М-11", "expected": True},
        {"input": "м-11", "expected": True},
        {"input": "M-11", "expected": True},  # Latin M
        {"input": "ВИМОГА M-11", "expected": True},  # Latin M
        {"input": "ВИМОГА", "expected": False},
        {"input": "НАКЛАДНА", "expected": False},
        {"input": "", "expected": False},
        {"input": None, "expected": False},
    ]
    out = _run_node_script(runner, {"testCases": cases})
    for tc, res in zip(cases, out["results"]):
        assert res == tc["expected"], f"Failed for input {tc['input']!r}: expected {tc['expected']}, got {res}"


@pytest.mark.skipif(not NODE, reason="node not available")
def test_render_docs_excludes_m11_rows():
    """M-11 documents do not appear as rows in the Documents tab table."""
    runner = """
    allDocs = payload.docs;
    renderDocs(allDocs);
    console.log(JSON.stringify({ html: els['docs-tbody'].innerHTML }));
    """
    docs = [
        {"id": 1, "filename": "m11_doc1.pdf", "doc_type": "ВИМОГА М-11", "doc_number": "M-1"},
        {"id": 2, "filename": "m11_doc2.pdf", "doc_type": "м-11", "doc_number": "M-2"},
        {"id": 3, "filename": "vimoga_classic.pdf", "doc_type": "ВИМОГА", "doc_number": "V-1"},
        {"id": 4, "filename": "nakladna.pdf", "doc_type": "НАКЛАДНА", "doc_number": "N-1"},
    ]
    out = _run_node_script(runner, {"docs": docs})
    html = out["html"]
    assert "m11_doc1.pdf" not in html
    assert "m11_doc2.pdf" not in html
    assert "vimoga_classic.pdf" in html
    assert "nakladna.pdf" in html


@pytest.mark.skipif(not NODE, reason="node not available")
def test_docs_count_and_filter_counts_exclude_m11():
    """docs-count badge and filter-not-accounted-count exclude M-11 documents."""
    runner = """
    allDocs = payload.docs;
    // Simulate what fetchDocs does for badge:
    document.getElementById('docs-count').innerText = allDocs.filter(d => !isM11Doc(d)).length;
    updateDocFilterCounts();

    console.log(JSON.stringify({
        docsCount: els['docs-count'].innerText,
        unaccountedCount: els['filter-not-accounted-count'].textContent
    }));
    """
    docs = [
        # M-11 document with missing fields (unaccounted)
        {"id": 1, "filename": "m1.pdf", "doc_type": "ВИМОГА М-11", "missing_fields": ["doc_date"]},
        # Another M-11 document
        {"id": 2, "filename": "m2.pdf", "doc_type": "М-11", "missing_fields": []},
        # Classic unaccounted document
        {"id": 3, "filename": "v1.pdf", "doc_type": "ВИМОГА", "missing_fields": ["doc_date"]},
        # Classic accounted document
        {"id": 4, "filename": "n1.pdf", "doc_type": "НАКЛАДНА", "missing_fields": []},
    ]
    out = _run_node_script(runner, {"docs": docs})
    # Total docs is 4, but only 2 are non-M11
    assert out["docsCount"] == 2
    # Total unaccounted is 2 (m1 and v1), but m1 is M-11, so unaccountedCount must be 1
    assert out["unaccountedCount"] == 1


@pytest.mark.skipif(not NODE, reason="node not available")
def test_filter_docs_excludes_m11_when_filter_applied():
    """filterDocs() passes only non-M-11 docs to renderDocs even when filter is active."""
    runner = """
    allDocs = payload.docs;
    docFilter = 'not-accounted';
    filterDocs();
    const filteredHtml = els['docs-tbody'].innerHTML;

    docFilter = '';
    filterDocs();
    const allHtml = els['docs-tbody'].innerHTML;

    console.log(JSON.stringify({ filteredHtml, allHtml }));
    """
    docs = [
        {"id": 1, "filename": "m11_unaccounted.pdf", "doc_type": "ВИМОГА М-11", "missing_fields": ["doc_date"]},
        {"id": 2, "filename": "vimoga_unaccounted.pdf", "doc_type": "ВИМОГА", "missing_fields": ["doc_date"]},
        {"id": 3, "filename": "nakladna_accounted.pdf", "doc_type": "НАКЛАДНА", "missing_fields": []},
    ]
    out = _run_node_script(runner, {"docs": docs})
    # Under 'not-accounted' filter:
    assert "m11_unaccounted.pdf" not in out["filteredHtml"]
    assert "vimoga_unaccounted.pdf" in out["filteredHtml"]
    assert "nakladna_accounted.pdf" not in out["filteredHtml"]

    # Under all docs:
    assert "m11_unaccounted.pdf" not in out["allHtml"]
    assert "vimoga_unaccounted.pdf" in out["allHtml"]
    assert "nakladna_accounted.pdf" in out["allHtml"]

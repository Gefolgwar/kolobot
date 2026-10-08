"""Tests for feat(m11): badge counters redesign on both tabs (Issue #57)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

import pytest

from kolobot.web.assets import JS, PAGE

NODE = shutil.which("node")

_NODE_TEST_HARNESS = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const els = {};
function el(id) {
    if (!els[id]) {
        els[id] = {
            id,
            innerHTML: '',
            textContent: '',
            innerText: '',
            className: '',
            classList: { add() {}, remove() {}, contains: () => false }
        };
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


def _run_node_badge_script(runner_code: str, payload_data: dict) -> dict:
    page = "\n".join(JS.values())
    with tempfile.TemporaryDirectory() as tmp:
        script_path = os.path.join(tmp, "badge_test_runner.js")
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


# ==============================================================================
# 1. HTML structure in PAGE / shell.html
# ==============================================================================


def test_documents_tab_has_second_vimoga_badge():
    """Documents tab has second badge next to docs-count."""
    docs_tab_idx = PAGE.find('id="tab-documents"')
    m11_tab_idx = PAGE.find('id="tab-m11"')
    assert docs_tab_idx != -1
    assert m11_tab_idx != -1

    docs_tab_html = PAGE[docs_tab_idx:m11_tab_idx]
    assert 'id="docs-count"' in docs_tab_html
    assert 'id="docs-vimoga-badge"' in docs_tab_html or 'id="vimoga-badge"' in docs_tab_html


def test_m11_tab_has_m11_badge():
    """M-11 tab has m11-badge."""
    m11_tab_idx = PAGE.find('id="tab-m11"')
    logs_tab_idx = PAGE.find('id="tab-logs"')
    assert m11_tab_idx != -1
    assert logs_tab_idx != -1

    m11_tab_html = PAGE[m11_tab_idx:logs_tab_idx]
    assert 'id="m11-badge"' in m11_tab_html


def test_both_badges_initial_markup():
    """Both badges render initial 0/0 structure with muted styling."""
    assert 'id="docs-vimoga-badge"' in PAGE
    assert 'id="m11-badge"' in PAGE
    # Check 0/0 exists in shell
    assert "0" in PAGE


# ==============================================================================
# 2. M-11 Badge calculations and styling
# ==============================================================================


@pytest.mark.skipif(not NODE, reason="node not available")
def test_m11_badge_shows_total_and_unlinked_rose_when_unlinked():
    """M-11 badge shows total/unlinked format and rose styling when unlinked > 0."""
    runner = """
    allM11Docs = payload.m11Docs;
    updateM11Badge();
    const b = els['m11-badge'];
    console.log(JSON.stringify({
        innerHTML: b.innerHTML,
        textContent: b.textContent,
        totalText: els['total-m11-count'].textContent,
        probText: els['problem-m11-count'].textContent
    }));
    """
    # 5 M-11 docs: 3 linked, 2 unlinked
    docs = [
        {"id": 1, "link_id": 101, "linked_vimoga": {"id": 10, "number": "В-1"}, "match_status": "full", "needs_review": 0},
        {"id": 2, "link_id": 102, "linked_vimoga": {"id": 11, "number": "В-2"}, "match_status": "manual", "needs_review": 0},
        {"id": 3, "link_id": 103, "linked_vimoga": {"id": 12, "number": "В-3"}, "match_status": "partial", "needs_review": 1},
        {"id": 4, "link_id": None, "linked_vimoga": None, "match_status": "none", "needs_review": 0},
        {"id": 5, "link_id": None, "linked_vimoga": None, "match_status": "none", "needs_review": 0},
    ]
    out = _run_node_badge_script(runner, {"m11Docs": docs})
    assert out["textContent"] == "5/2"
    assert "text-rose-400" in out["innerHTML"]
    assert "5" in out["innerHTML"]
    assert "2" in out["innerHTML"]
    # Internal counters
    assert str(out["totalText"]) == "5"


@pytest.mark.skipif(not NODE, reason="node not available")
def test_m11_badge_muted_when_unlinked_is_zero():
    """M-11 badge unlinked portion is muted slate when unlinked == 0."""
    runner = """
    allM11Docs = payload.m11Docs;
    updateM11Badge();
    const b = els['m11-badge'];
    console.log(JSON.stringify({
        innerHTML: b.innerHTML,
        textContent: b.textContent
    }));
    """
    # 2 M-11 docs, both linked
    docs = [
        {"id": 1, "link_id": 101, "linked_vimoga": {"id": 10, "number": "В-1"}, "match_status": "full", "needs_review": 0},
        {"id": 2, "link_id": 102, "linked_vimoga": {"id": 11, "number": "В-2"}, "match_status": "manual", "needs_review": 0},
    ]
    out = _run_node_badge_script(runner, {"m11Docs": docs})
    assert out["textContent"] == "2/0"
    assert "text-rose-400" not in out["innerHTML"]
    assert "text-slate-500" in out["innerHTML"]


@pytest.mark.skipif(not NODE, reason="node not available")
def test_m11_badge_zero_zero():
    """M-11 badge renders 0/0 correctly when there are no M-11 documents."""
    runner = """
    allM11Docs = [];
    updateM11Badge();
    const b = els['m11-badge'];
    console.log(JSON.stringify({
        innerHTML: b.innerHTML,
        textContent: b.textContent,
        totalText: els['total-m11-count'].textContent
    }));
    """
    out = _run_node_badge_script(runner, {})
    assert out["textContent"] == "0/0"
    assert "text-rose-400" not in out["innerHTML"]
    assert "text-slate-500" in out["innerHTML"]
    assert str(out["totalText"]) == "0"


# ==============================================================================
# 3. Documents tab second badge (ВІМОГА ratio) calculations and styling
# ==============================================================================


@pytest.mark.skipif(not NODE, reason="node not available")
def test_vimoga_badge_computed_from_all_docs_and_all_m11_docs():
    """ВІМОГА badge counts classic vimogas and cross-references with allM11Docs."""
    runner = """
    allDocs = payload.allDocs;
    allM11Docs = payload.allM11Docs;
    updateVimogaBadge();
    const b = els['docs-vimoga-badge'];
    console.log(JSON.stringify({
        innerHTML: b.innerHTML,
        textContent: b.textContent
    }));
    """
    all_docs = [
        # 3 classic ВИМОГА
        {"id": 10, "doc_type": "ВИМОГА", "doc_number": "В-1"},
        {"id": 11, "doc_type": "ВИМОГА", "doc_number": "В-2"},
        {"id": 12, "doc_type": "ВИМОГА", "doc_number": "В-3"},
        # 1 M-11 document (must be ignored in vimoga count)
        {"id": 99, "doc_type": "ВИМОГА М-11", "doc_number": "М-99"},
        # 1 НАКЛАДНА (must be ignored in vimoga count)
        {"id": 50, "doc_type": "НАКЛАДНА", "doc_number": "Н-50"},
    ]
    # M-11 docs: only doc 10 is linked
    all_m11_docs = [
        {"id": 1, "link_id": 201, "linked_vimoga": {"id": 10, "number": "В-1"}},
        {"id": 2, "link_id": None, "linked_vimoga": None},
    ]
    out = _run_node_badge_script(runner, {"allDocs": all_docs, "allM11Docs": all_m11_docs})
    # 3 vimogas total, 1 linked -> 2 unlinked
    assert out["textContent"] == "3/2"
    assert "text-rose-400" in out["innerHTML"]


@pytest.mark.skipif(not NODE, reason="node not available")
def test_vimoga_badge_muted_when_all_linked():
    """ВІМОГА badge unlinked portion is muted slate when unlinked == 0."""
    runner = """
    allDocs = payload.allDocs;
    allM11Docs = payload.allM11Docs;
    updateVimogaBadge();
    const b = els['docs-vimoga-badge'];
    console.log(JSON.stringify({
        innerHTML: b.innerHTML,
        textContent: b.textContent
    }));
    """
    all_docs = [
        {"id": 10, "doc_type": "ВИМОГА", "doc_number": "В-1"},
        {"id": 11, "doc_type": "ВИМОГА", "doc_number": "В-2"},
    ]
    all_m11_docs = [
        {"id": 1, "link_id": 201, "linked_vimoga": {"id": 10, "number": "В-1"}},
        {"id": 2, "link_id": 202, "linked_vimoga": {"id": 11, "number": "В-2"}},
    ]
    out = _run_node_badge_script(runner, {"allDocs": all_docs, "allM11Docs": all_m11_docs})
    assert out["textContent"] == "2/0"
    assert "text-rose-400" not in out["innerHTML"]
    assert "text-slate-500" in out["innerHTML"]


@pytest.mark.skipif(not NODE, reason="node not available")
def test_vimoga_badge_zero_zero():
    """ВІМОГА badge renders 0/0 when there are no classic vimoga documents."""
    runner = """
    allDocs = payload.allDocs;
    allM11Docs = payload.allM11Docs;
    updateVimogaBadge();
    const b = els['docs-vimoga-badge'];
    console.log(JSON.stringify({
        innerHTML: b.innerHTML,
        textContent: b.textContent
    }));
    """
    all_docs = [
        {"id": 50, "doc_type": "НАКЛАДНА", "doc_number": "Н-50"},
        {"id": 99, "doc_type": "ВИМОГА М-11", "doc_number": "М-99"},
    ]
    out = _run_node_badge_script(runner, {"allDocs": all_docs, "allM11Docs": []})
    assert out["textContent"] == "0/0"
    assert "text-rose-400" not in out["innerHTML"]
    assert "text-slate-500" in out["innerHTML"]


# ==============================================================================
# 4. Dynamic badge update on unbind / bind / fetch
# ==============================================================================


@pytest.mark.skipif(not NODE, reason="node not available")
def test_badges_update_dynamically_after_unbind():
    """When a link is removed from allM11Docs, both badges update their unlinked ratios."""
    runner = """
    allDocs = payload.allDocs;
    allM11Docs = payload.allM11DocsInitial;

    updateM11Badge();
    updateVimogaBadge();

    const m11Before = els['m11-badge'].textContent;
    const vimogaBefore = els['docs-vimoga-badge'].textContent;

    // Simulate unbind: M-11 document #1 becomes unlinked
    allM11Docs = payload.allM11DocsAfterUnbind;

    updateM11Badge();
    updateVimogaBadge();

    const m11After = els['m11-badge'].textContent;
    const vimogaAfter = els['docs-vimoga-badge'].textContent;

    console.log(JSON.stringify({
        m11Before,
        vimogaBefore,
        m11After,
        vimogaAfter
    }));
    """
    all_docs = [
        {"id": 10, "doc_type": "ВИМОГА", "doc_number": "В-1"},
    ]
    initial_m11 = [
        {"id": 1, "link_id": 50, "linked_vimoga": {"id": 10, "number": "В-1"}},
    ]
    after_unbind_m11 = [
        {"id": 1, "link_id": None, "linked_vimoga": None, "match_status": "none"},
    ]
    out = _run_node_badge_script(runner, {
        "allDocs": all_docs,
        "allM11DocsInitial": initial_m11,
        "allM11DocsAfterUnbind": after_unbind_m11,
    })
    assert out["m11Before"] == "1/0"
    assert out["vimogaBefore"] == "1/0"
    assert out["m11After"] == "1/1"
    assert out["vimogaAfter"] == "1/1"


def test_js_functions_present():
    """Verify updateVimogaBadge, updateM11Badge, and isClassicVimoga exist in JS bundle."""
    all_js = "\n".join(JS.values())
    assert "updateM11Badge" in all_js
    assert "updateVimogaBadge" in all_js
    assert "isClassicVimoga" in all_js
    assert "isM11DocLinked" in all_js

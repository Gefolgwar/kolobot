"""Tests for feat(m11): sub-document cards in both tab accordions (Issue #55)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

import pytest

from kolobot.web.assets import JS

NODE = shutil.which("node")


def test_render_linked_doc_card_exists_in_js():
    """Verify renderLinkedDocCard function exists in document_impact JS."""
    doc_impact_js = JS.get("document_impact", JS.get("11-document_impact", ""))
    assert "function renderLinkedDocCard" in doc_impact_js
    assert "renderLinkedDocCard" in doc_impact_js
    assert "getLinkedCardForDoc" in doc_impact_js


_NODE_STUBS = """
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));

const els = {};
function el(id) {
    if (!els[id]) {
        els[id] = { id, innerHTML: '', textContent: '', classList: { add() {}, remove() {}, contains: () => false }, style: {} };
    }
    return els[id];
}

globalThis.document = {
    getElementById: el,
    querySelectorAll: () => [],
    addEventListener: () => {}
};
globalThis.window = { addEventListener: () => {} };

let lastViewedDoc = null;
globalThis.viewDocument = function(id, filename, fileType) {
    lastViewedDoc = { id, filename, fileType };
};
"""


@pytest.mark.skipif(not NODE, reason="node not available")
def test_render_linked_doc_card_unit():
    """Test renderLinkedDocCard function directly for both types."""
    page = "\n".join(JS.values())

    runner = """
    // 1. Linked Vimoga card
    const vimogaDoc = {
        id: 101,
        doc_number: "В-55",
        doc_date: "2026-03-01",
        filename: "vimoga_55.pdf",
        file_type: "pdf",
        status: "completed"
    };
    const vimogaCardHtml = renderLinkedDocCard(vimogaDoc, "ВІМОГА");

    // 2. Linked M-11 card
    const m11Doc = {
        id: 202,
        doc_number: "М11-88",
        doc_date: "2026-03-02",
        filename: "m11_88.jpg",
        file_type: "photo",
        status: "completed",
        match_status: "full",
        needs_review: 0
    };
    const m11CardHtml = renderLinkedDocCard(m11Doc, "М-11");

    // 3. Falsy doc
    const emptyCardHtml = renderLinkedDocCard(null, "ВІМОГА");

    console.log(JSON.stringify({ vimogaCardHtml, m11CardHtml, emptyCardHtml }));
    """

    payload = {}
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "test_card.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(_NODE_STUBS + page + "\n" + runner)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        proc = subprocess.run([NODE, script, payload_path],
                              capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0, proc.stderr
        data = json.loads(proc.stdout)

    # 1. Vimoga card
    v_html = data["vimogaCardHtml"]
    assert "linked-doc-card" in v_html
    assert "В-55" in v_html
    assert "2026-03-01" in v_html
    assert "ВІМОГА" in v_html
    assert "Переглянути" in v_html
    assert "viewDocument(101" in v_html
    assert "badge-" in v_html  # status badge

    # 2. M-11 card
    m_html = data["m11CardHtml"]
    assert "linked-doc-card" in m_html
    assert "М11-88" in m_html
    assert "2026-03-02" in m_html
    assert "М-11" in m_html
    assert "Переглянути" in m_html
    assert "viewDocument(202" in m_html
    assert "badge-" in m_html  # status badge

    # 3. Falsy doc
    assert data["emptyCardHtml"] == ""


@pytest.mark.skipif(not NODE, reason="node not available")
def test_accordion_m11_shows_linked_vimoga_card():
    """Test M-11 accordion shows linked classic Vimoga card at top when linked, and no card when unlinked."""
    page = "\n".join(JS.values())

    runner = """
    (async () => {
        // Setup allM11Docs: doc 10 linked to vimoga 5, doc 20 unlinked
        allM11Docs = [
            {
                id: 10,
                doc_number: "М11-01",
                doc_date: "2026-03-01",
                filename: "m11_01.pdf",
                file_type: "pdf",
                status: "completed",
                match_status: "full",
                needs_review: 0,
                linked_vimoga: {
                    id: 5,
                    number: "В-100",
                    doc_number: "В-100",
                    date: "2026-02-28",
                    doc_date: "2026-02-28",
                    filename: "vimoga_100.pdf",
                    file_type: "pdf"
                }
            },
            {
                id: 20,
                doc_number: "М11-02",
                doc_date: "2026-03-02",
                filename: "m11_02.pdf",
                file_type: "pdf",
                status: "completed",
                match_status: "none",
                needs_review: 0,
                linked_vimoga: null
            }
        ];

        // Mock fetch for OCR
        globalThis.fetch = async (url) => {
            if (url.includes('/10/ocr')) {
                return {
                    json: async () => ({
                        id: 10,
                        doc_type: "ВИМОГА М-11",
                        doc_number: "М11-01",
                        filename: "m11_01.pdf",
                        file_type: "pdf",
                        raw_text: "Текст М-11 01",
                        impact: []
                    })
                };
            }
            if (url.includes('/20/ocr')) {
                return {
                    json: async () => ({
                        id: 20,
                        doc_type: "ВИМОГА М-11",
                        doc_number: "М11-02",
                        filename: "m11_02.pdf",
                        file_type: "pdf",
                        raw_text: "Текст М-11 02",
                        impact: []
                    })
                };
            }
            return { json: async () => ({}) };
        };

        // Reload impact for linked M-11 #10
        await reloadDocImpact(10);
        const m11_10_html = els['m11-impact-content-10'].innerHTML;

        // Reload impact for unlinked M-11 #20
        await reloadDocImpact(20);
        const m11_20_html = els['m11-impact-content-20'].innerHTML;

        console.log(JSON.stringify({ m11_10_html, m11_20_html }));
    })();
    """

    payload = {}
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "test_m11_acc.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(_NODE_STUBS + page + "\n" + runner)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        proc = subprocess.run([NODE, script, payload_path],
                              capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0, proc.stderr
        data = json.loads(proc.stdout)

    h10 = data["m11_10_html"]
    # Card is injected at the top
    assert h10.startswith('<div class="space-y-4"><div class="linked-doc-card')
    assert "В-100" in h10
    assert "2026-02-28" in h10
    assert "ВІМОГА" in h10
    assert "Переглянути" in h10
    assert "viewDocument(5" in h10

    # Unlinked M-11 has no linked-doc-card
    h20 = data["m11_20_html"]
    assert "linked-doc-card" not in h20
    assert "Переглянути" not in h20


@pytest.mark.skipif(not NODE, reason="node not available")
def test_accordion_documents_tab_shows_linked_m11_card_for_vimoga_only():
    """Test Documents tab accordion shows linked M-11 card only for ВІМОГА, never for НАКЛАДНА."""
    page = "\n".join(JS.values())

    runner = """
    (async () => {
        // M-11 doc #100 is linked to vimoga #50
        allM11Docs = [
            {
                id: 100,
                doc_number: "М11-999",
                doc_date: "2026-03-05",
                filename: "m11_999.pdf",
                file_type: "pdf",
                status: "completed",
                match_status: "full",
                needs_review: 0,
                linked_vimoga: {
                    id: 50,
                    number: "В-50",
                    date: "2026-03-04"
                }
            }
        ];

        globalThis.fetch = async (url) => {
            // 1. Linked Vimoga #50
            if (url.includes('/50/ocr')) {
                return {
                    json: async () => ({
                        id: 50,
                        doc_type: "ВИМОГА",
                        doc_number: "В-50",
                        filename: "vimoga_50.pdf",
                        file_type: "pdf",
                        raw_text: "Текст вимоги",
                        impact: []
                    })
                };
            }
            // 2. Unlinked Vimoga #51
            if (url.includes('/51/ocr')) {
                return {
                    json: async () => ({
                        id: 51,
                        doc_type: "ВИМОГА",
                        doc_number: "В-51",
                        filename: "vimoga_51.pdf",
                        file_type: "pdf",
                        raw_text: "Текст вимоги",
                        impact: []
                    })
                };
            }
            // 3. Nakladna #52 (even if allM11Docs had linked_vimoga id 52, it must not show)
            if (url.includes('/52/ocr')) {
                return {
                    json: async () => ({
                        id: 52,
                        doc_type: "НАКЛАДНА",
                        doc_number: "Н-52",
                        filename: "nakladna_52.pdf",
                        file_type: "pdf",
                        raw_text: "Текст накладної",
                        impact: []
                    })
                };
            }
            return { json: async () => ({}) };
        };

        // Linked Vimoga #50
        await reloadDocImpact(50);
        const vimoga_50_html = els['doc-impact-content-50'].innerHTML;

        // Unlinked Vimoga #51
        await reloadDocImpact(51);
        const vimoga_51_html = els['doc-impact-content-51'].innerHTML;

        // Nakladna #52
        await reloadDocImpact(52);
        const nakladna_52_html = els['doc-impact-content-52'].innerHTML;

        console.log(JSON.stringify({ vimoga_50_html, vimoga_51_html, nakladna_52_html }));
    })();
    """

    payload = {}
    with tempfile.TemporaryDirectory() as tmp:
        script = os.path.join(tmp, "test_doc_acc.js")
        payload_path = os.path.join(tmp, "payload.json")
        with open(script, "w", encoding="utf-8") as fh:
            fh.write(_NODE_STUBS + page + "\n" + runner)
        with open(payload_path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        proc = subprocess.run([NODE, script, payload_path],
                              capture_output=True, text=True, encoding="utf-8")
        assert proc.returncode == 0, proc.stderr
        data = json.loads(proc.stdout)

    # 1. Linked Vimoga #50: card at top
    h50 = data["vimoga_50_html"]
    assert h50.startswith('<div class="space-y-4"><div class="linked-doc-card')
    assert "М11-999" in h50
    assert "2026-03-05" in h50
    assert "М-11" in h50
    assert "Переглянути" in h50
    assert "viewDocument(100" in h50

    # 2. Unlinked Vimoga #51: no card
    h51 = data["vimoga_51_html"]
    assert "linked-doc-card" not in h51
    assert "Переглянути" not in h51

    # 3. Nakladna #52: no card
    h52 = data["nakladna_52_html"]
    assert "linked-doc-card" not in h52
    assert "Переглянути" not in h52

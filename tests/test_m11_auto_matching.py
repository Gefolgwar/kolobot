"""Unit and integration tests for bidirectional auto-matching between M-11 and classic ВИМОГА documents (Issue #48)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pytest

from kolobot.doc_structurer import Document
from kolobot.file_store import FileStore
from kolobot.warehouse_db import WarehouseDB
from kolobot.warehouse_writer import (
    _save_to_warehouse,
    match_m11_document,
    match_vimoga_document,
)


@pytest.fixture
def warehouse_db(tmp_path):
    db = WarehouseDB(db_path=str(tmp_path / "warehouse.db"))
    db.init_db()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def file_store(tmp_path):
    return FileStore(downloads_path=str(tmp_path / "downloads"))


def _make_m11_doc(
    items: Optional[List[Dict[str, Any]]] = None,
    doc_number: str = "42",
    doc_date: str = "15.08.2026",
    raw_text: str = "Типова форма № М-11\nНАКЛАДНА-ВИМОГА № 42",
    **kwargs,
) -> Document:
    if items is None:
        items = [
            {
                "num": 1,
                "name": "Муфта термоусаджувальна 10кВ",
                "nomenclature_number": "00-00059398",
                "unit": "шт",
                "quantity": "2",
            },
            {
                "num": 2,
                "name": "Кабель ААБл 3х120",
                "nomenclature_number": "00-00059399",
                "unit": "м",
                "quantity": "50.5",
            },
        ]
    return Document(
        doc_type="вимога м-11",
        raw_text=raw_text,
        doc_number=doc_number,
        doc_date=doc_date,
        requested_by=kwargs.get("requested_by", "Іванов І.І."),
        requested_via=kwargs.get("requested_via", "Петров П.П."),
        items=items,
        **{k: v for k, v in kwargs.items() if k not in ("requested_by", "requested_via")},
    )


def _make_vimoga_doc(
    items: Optional[List[Dict[str, Any]]] = None,
    doc_number: str = "101",
    doc_date: str = "15.08.2026",
    raw_text: str = "ВИМОГА № 101\nВідпустити зі складу",
    **kwargs,
) -> Document:
    if items is None:
        items = [
            {
                "num": 1,
                "name": "Муфта термоусаджувальна 10кВ",
                "nomenclature_number": "00-00059398",
                "unit": "шт",
                "quantity": "2",
            },
            {
                "num": 2,
                "name": "Кабель ААБл 3х120",
                "nomenclature_number": "00-00059399",
                "unit": "м",
                "quantity": "50.5",
            },
        ]
    return Document(
        doc_type="вимога",
        raw_text=raw_text,
        doc_number=doc_number,
        doc_date=doc_date,
        requested_by=kwargs.get("requested_by", "Іванов І.І."),
        requested_via=kwargs.get("requested_via", "Петров П.П."),
        items=items,
        **{k: v for k, v in kwargs.items() if k not in ("requested_by", "requested_via")},
    )


def _make_nakladna_doc(
    items: Optional[List[Dict[str, Any]]] = None,
    doc_number: str = "202",
    doc_date: str = "15.08.2026",
    raw_text: str = "ВИДАТКОВА НАКЛАДНА № 202",
    **kwargs,
) -> Document:
    if items is None:
        items = [
            {
                "num": 1,
                "name": "Кабель ААБл 3х120",
                "nomenclature_number": "00-00059399",
                "unit": "м",
                "quantity": "100",
            },
        ]
    return Document(
        doc_type="накладна",
        raw_text=raw_text,
        doc_number=doc_number,
        doc_date=doc_date,
        requested_by=kwargs.get("requested_by", "Сидоров С.С."),
        requested_via=kwargs.get("requested_via", "Петров П.П."),
        items=items,
        **{k: v for k, v in kwargs.items() if k not in ("requested_by", "requested_via")},
    )


# ==============================================================================
# Helper method tests for WarehouseDB
# ==============================================================================


def test_warehouse_db_vimoga_and_unlinked_m11_helpers(warehouse_db, file_store):
    """WarehouseDB helper queries accurately retrieve items and unlinked status."""
    # 1. Save classic ВИМОГА
    vimoga_doc = _make_vimoga_doc()
    _save_to_warehouse(
        warehouse_db, file_store, vimoga_doc,
        {"file_name": "vimoga.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-vimoga-1",
    )
    vimoga_id = warehouse_db.get_documents()[0]["id"]

    # Verify get_vimoga_items returns items from warehouse_transactions JOIN warehouse_items
    v_items = warehouse_db.get_vimoga_items(vimoga_id)
    assert len(v_items) == 2
    names = {it["name"] for it in v_items}
    assert "Муфта термоусаджувальна 10кВ" in names
    assert "Кабель ААБл 3х120" in names

    # Verify get_all_vimoga_documents_with_items returns candidate
    candidates = warehouse_db.get_all_vimoga_documents_with_items()
    assert len(candidates) == 1
    assert candidates[0]["doc_id"] == vimoga_id
    assert len(candidates[0]["items"]) == 2

    # Exclude vimoga_id
    candidates_excluded = warehouse_db.get_all_vimoga_documents_with_items(exclude_doc_id=vimoga_id)
    assert len(candidates_excluded) == 0

    # 2. Initially no unlinked M-11
    assert len(warehouse_db.get_unlinked_m11_documents()) == 0


# ==============================================================================
# Direction A: M-11 arrives after existing classic ВИМОГА
# ==============================================================================


def test_direction_a_full_match(warehouse_db, file_store):
    """Direction A: M-11 arrives, matches existing classic ВИМОГА (full match)."""
    # 1. Classic ВИМОГА arrives first
    vimoga_doc = _make_vimoga_doc(
        items=[
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
            {"name": "Муфта термоусаджувальна 10кВ", "quantity": "2", "unit": "шт"},
        ]
    )
    _save_to_warehouse(
        warehouse_db, file_store, vimoga_doc,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )
    v_id = warehouse_db.get_documents()[0]["id"]

    # No links yet
    assert len(warehouse_db.get_document_links()) == 0

    # 2. M-11 arrives second with reversed item order
    m11_doc = _make_m11_doc(
        items=[
            {"name": "Муфта термоусаджувальна 10кВ", "quantity": "2", "unit": "шт"},
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
        ]
    )
    _save_to_warehouse(
        warehouse_db, file_store, m11_doc,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )
    m11_id = [d["id"] for d in warehouse_db.get_documents() if d["id"] != v_id][0]

    # Verify link created with full match and needs_review = 0
    links = warehouse_db.get_document_links()
    assert len(links) == 1
    link = links[0]
    assert link["m11_doc_id"] == m11_id
    assert link["vimoga_doc_id"] == v_id
    assert link["match_status"] == "full"
    assert link["needs_review"] == 0


def test_direction_a_partial_match(warehouse_db, file_store):
    """Direction A: M-11 arrives, matches existing classic ВИМОГА partially."""
    # 1. Classic ВИМОГА with 2 items
    vimoga_doc = _make_vimoga_doc(
        items=[
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
            {"name": "Муфта термоусаджувальна 10кВ", "quantity": "2", "unit": "шт"},
        ]
    )
    _save_to_warehouse(
        warehouse_db, file_store, vimoga_doc,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )
    v_id = warehouse_db.get_documents()[0]["id"]

    # 2. M-11 arrives with 1 matching item and 1 non-matching item
    m11_doc = _make_m11_doc(
        items=[
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
            {"name": "Ізоляційна стрічка", "quantity": "10", "unit": "шт"},
        ]
    )
    _save_to_warehouse(
        warehouse_db, file_store, m11_doc,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )
    m11_id = [d["id"] for d in warehouse_db.get_documents() if d["id"] != v_id][0]

    # Link created with partial match
    links = warehouse_db.get_document_links()
    assert len(links) == 1
    assert links[0]["m11_doc_id"] == m11_id
    assert links[0]["vimoga_doc_id"] == v_id
    assert links[0]["match_status"] == "partial"
    assert links[0]["needs_review"] == 0


def test_direction_a_no_match_stays_unlinked(warehouse_db, file_store):
    """Direction A: M-11 arrives with non-matching items, stays unlinked."""
    vimoga_doc = _make_vimoga_doc(
        items=[
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
        ]
    )
    _save_to_warehouse(
        warehouse_db, file_store, vimoga_doc,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )

    m11_doc = _make_m11_doc(
        items=[
            {"name": "Шпаклівка гіпсова", "quantity": "15", "unit": "кг"},
        ]
    )
    _save_to_warehouse(
        warehouse_db, file_store, m11_doc,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )

    # No link should be created
    assert len(warehouse_db.get_document_links()) == 0

    # M-11 is in unlinked list
    unlinked = warehouse_db.get_unlinked_m11_documents()
    assert len(unlinked) == 1


def test_direction_a_best_match_selection(warehouse_db, file_store):
    """Direction A: M-11 selects the best matching candidate among multiple classic ВИМОГА documents."""
    # V1: only 1 item matching
    v1 = _make_vimoga_doc(
        doc_number="101",
        items=[{"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"}],
    )
    _save_to_warehouse(
        warehouse_db, file_store, v1,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )
    v1_id = warehouse_db.get_documents()[0]["id"]

    # V2: 2 items matching (full match)
    v2 = _make_vimoga_doc(
        doc_number="102",
        items=[
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
            {"name": "Муфта термоусаджувальна 10кВ", "quantity": "2", "unit": "шт"},
        ],
    )
    _save_to_warehouse(
        warehouse_db, file_store, v2,
        {"file_name": "v2.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v2",
    )
    v2_id = warehouse_db.get_documents()[0]["id"]

    # M-11 arrives with both items
    m11 = _make_m11_doc(
        items=[
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
            {"name": "Муфта термоусаджувальна 10кВ", "quantity": "2", "unit": "шт"},
        ]
    )
    _save_to_warehouse(
        warehouse_db, file_store, m11,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )

    links = warehouse_db.get_document_links()
    assert len(links) == 1
    assert links[0]["vimoga_doc_id"] == v2_id
    assert links[0]["match_status"] == "full"


def test_direction_a_conflict_detection_when_vimoga_already_linked(warehouse_db, file_store):
    """Direction A: conflict detected (needs_review = 1) if matched ВИМОГА already has another M-11 linked."""
    # 1. Classic ВИМОГА arrives
    v_doc = _make_vimoga_doc()
    _save_to_warehouse(
        warehouse_db, file_store, v_doc,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )
    v_id = warehouse_db.get_documents()[0]["id"]

    # 2. First M-11 arrives and links
    m11_doc1 = _make_m11_doc(doc_number="42")
    _save_to_warehouse(
        warehouse_db, file_store, m11_doc1,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )
    m11_id1 = [d["id"] for d in warehouse_db.get_documents() if d["id"] != v_id][0]

    links = warehouse_db.get_document_links()
    assert len(links) == 1
    assert links[0]["needs_review"] == 0

    # 3. Second M-11 arrives with same matching items
    m11_doc2 = _make_m11_doc(doc_number="43")
    _save_to_warehouse(
        warehouse_db, file_store, m11_doc2,
        {"file_name": "m2.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m2",
    )
    m11_id2 = [d["id"] for d in warehouse_db.get_documents() if d["id"] not in (v_id, m11_id1)][0]

    links = warehouse_db.get_document_links()
    assert len(links) == 2

    # Second link has needs_review = 1
    link2 = [l for l in links if l["m11_doc_id"] == m11_id2][0]
    assert link2["vimoga_doc_id"] == v_id
    assert link2["match_status"] == "full"
    assert link2["needs_review"] == 1


# ==============================================================================
# Direction B: Classic ВИМОГА arrives after unlinked M-11
# ==============================================================================


def test_direction_b_full_match(warehouse_db, file_store):
    """Direction B: Unlinked M-11 exists, classic ВИМОГА arrives and matches (full match)."""
    # 1. M-11 arrives first (no ВИМОГА in DB -> stays unlinked)
    m11_doc = _make_m11_doc()
    _save_to_warehouse(
        warehouse_db, file_store, m11_doc,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )
    m11_id = warehouse_db.get_documents()[0]["id"]
    assert len(warehouse_db.get_document_links()) == 0
    assert len(warehouse_db.get_unlinked_m11_documents()) == 1

    # 2. Classic ВИМОГА arrives second
    vimoga_doc = _make_vimoga_doc()
    _save_to_warehouse(
        warehouse_db, file_store, vimoga_doc,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )
    v_id = [d["id"] for d in warehouse_db.get_documents() if d["id"] != m11_id][0]

    # Verify link created
    links = warehouse_db.get_document_links()
    assert len(links) == 1
    link = links[0]
    assert link["m11_doc_id"] == m11_id
    assert link["vimoga_doc_id"] == v_id
    assert link["match_status"] == "full"
    assert link["needs_review"] == 0

    # M-11 is no longer in unlinked list
    assert len(warehouse_db.get_unlinked_m11_documents()) == 0


def test_direction_b_partial_match(warehouse_db, file_store):
    """Direction B: Unlinked M-11 exists, classic ВИМОГА arrives and matches partially."""
    # 1. M-11 with 2 items
    m11_doc = _make_m11_doc(
        items=[
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
            {"name": "Муфта термоусаджувальна 10кВ", "quantity": "2", "unit": "шт"},
        ]
    )
    _save_to_warehouse(
        warehouse_db, file_store, m11_doc,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )
    m11_id = warehouse_db.get_documents()[0]["id"]

    # 2. Classic ВИМОГА with 1 matching item and 1 other item
    vimoga_doc = _make_vimoga_doc(
        items=[
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
            {"name": "Труба ПНД", "quantity": "20", "unit": "м"},
        ]
    )
    _save_to_warehouse(
        warehouse_db, file_store, vimoga_doc,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )
    v_id = [d["id"] for d in warehouse_db.get_documents() if d["id"] != m11_id][0]

    links = warehouse_db.get_document_links()
    assert len(links) == 1
    assert links[0]["m11_doc_id"] == m11_id
    assert links[0]["vimoga_doc_id"] == v_id
    assert links[0]["match_status"] == "partial"
    assert links[0]["needs_review"] == 0


def test_direction_b_no_match_leaves_m11_unlinked(warehouse_db, file_store):
    """Direction B: Unlinked M-11 exists, classic ВИМОГА with different items arrives -> no link."""
    m11_doc = _make_m11_doc(
        items=[{"name": "Шпаклівка", "quantity": "5", "unit": "кг"}]
    )
    _save_to_warehouse(
        warehouse_db, file_store, m11_doc,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )

    vimoga_doc = _make_vimoga_doc(
        items=[{"name": "Кабель ААБл 3х120", "quantity": "50", "unit": "м"}]
    )
    _save_to_warehouse(
        warehouse_db, file_store, vimoga_doc,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )

    assert len(warehouse_db.get_document_links()) == 0
    assert len(warehouse_db.get_unlinked_m11_documents()) == 1


def test_direction_b_ignores_already_linked_m11(warehouse_db, file_store):
    """Direction B: classic ВИМОГА arrives, does not re-link already linked M-11 documents."""
    # 1. Link M-11 #1 to ВИМОГА #1
    v1_doc = _make_vimoga_doc(doc_number="101")
    _save_to_warehouse(
        warehouse_db, file_store, v1_doc,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )
    v1_id = warehouse_db.get_documents()[0]["id"]

    m1_doc = _make_m11_doc(doc_number="41")
    _save_to_warehouse(
        warehouse_db, file_store, m1_doc,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )
    m1_id = warehouse_db.get_documents()[0]["id"]

    assert len(warehouse_db.get_document_links()) == 1

    # 2. Add unlinked M-11 #2 with different item
    m2_doc = _make_m11_doc(
        doc_number="42",
        items=[{"name": "Трансформатор ТМГ 100", "quantity": "1", "unit": "шт"}],
    )
    _save_to_warehouse(
        warehouse_db, file_store, m2_doc,
        {"file_name": "m2.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m2",
    )
    m2_id = warehouse_db.get_documents()[0]["id"]

    # M-11 #2 is unlinked, M-11 #1 is linked
    unlinked = [d["id"] for d in warehouse_db.get_unlinked_m11_documents()]
    assert m1_id not in unlinked
    assert m2_id in unlinked

    # 3. New ВИМОГА #2 arrives with items matching M-11 #1 AND M-11 #2
    v2_doc = _make_vimoga_doc(
        doc_number="102",
        items=[
            {"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"},
            {"name": "Муфта термоусаджувальна 10кВ", "quantity": "2", "unit": "шт"},
            {"name": "Трансформатор ТМГ 100", "quantity": "1", "unit": "шт"},
        ],
    )
    _save_to_warehouse(
        warehouse_db, file_store, v2_doc,
        {"file_name": "v2.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v2",
    )
    v2_id = warehouse_db.get_documents()[0]["id"]

    # Only M-11 #2 should have been linked to ВИМОГА #2 (because M-11 #1 was already linked)
    links_v2 = warehouse_db.get_document_links_for_vimoga(v2_id)
    assert len(links_v2) == 1
    assert links_v2[0]["m11_doc_id"] == m2_id


def test_direction_b_conflict_detection_multiple_matching_unlinked_m11(warehouse_db, file_store):
    """Direction B: two unlinked M-11 documents match the arriving classic ВИМОГА -> second link gets needs_review = 1."""
    # 1. Two unlinked M-11 documents
    m1_doc = _make_m11_doc(doc_number="41")
    _save_to_warehouse(
        warehouse_db, file_store, m1_doc,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )
    m1_id = warehouse_db.get_documents()[0]["id"]

    m2_doc = _make_m11_doc(doc_number="42")
    _save_to_warehouse(
        warehouse_db, file_store, m2_doc,
        {"file_name": "m2.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m2",
    )
    m2_id = warehouse_db.get_documents()[0]["id"]

    assert len(warehouse_db.get_document_links()) == 0
    assert len(warehouse_db.get_unlinked_m11_documents()) == 2

    # 2. Classic ВИМОГА arrives and matches both
    v_doc = _make_vimoga_doc(doc_number="101")
    _save_to_warehouse(
        warehouse_db, file_store, v_doc,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )
    v_id = [d["id"] for d in warehouse_db.get_documents() if d["id"] not in (m1_id, m2_id)][0]

    links = warehouse_db.get_document_links_for_vimoga(v_id)
    assert len(links) == 2

    # One link has needs_review = 0, the other has needs_review = 1
    reviews = {l["m11_doc_id"]: l["needs_review"] for l in links}
    assert reviews[m1_id] == 0
    assert reviews[m2_id] == 1


# ==============================================================================
# Non-interference with existing transactions and document processing
# ==============================================================================


def test_nakladna_does_not_trigger_matching(warehouse_db, file_store):
    """НАКЛАДНА arrives: transactions created as income, matching is NOT triggered."""
    m_doc = _make_m11_doc(
        items=[{"name": "Кабель ААБл 3х120", "quantity": "100", "unit": "м"}]
    )
    _save_to_warehouse(
        warehouse_db, file_store, m_doc,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )

    nakladna_doc = _make_nakladna_doc()
    _save_to_warehouse(
        warehouse_db, file_store, nakladna_doc,
        {"file_name": "n1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-n1",
    )

    # No document links should be created for НАКЛАДНА
    assert len(warehouse_db.get_document_links()) == 0

    # But warehouse transactions must be present
    txs = warehouse_db._conn.execute("SELECT * FROM warehouse_transactions").fetchall()
    assert len(txs) == 1
    assert txs[0]["operation_type"] == "income"
    assert txs[0]["quantity"] == 100.0


def test_classic_vimoga_transactions_and_balance_unaffected(warehouse_db, file_store):
    """Classic ВИМОГА transactions and stock balances work normally alongside matching."""
    # First income via НАКЛАДНА
    _save_to_warehouse(
        warehouse_db, file_store,
        _make_nakladna_doc(
            items=[{"name": "Кабель ААБл 3х120", "quantity": "100", "unit": "м"}]
        ),
        {"file_name": "n1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-n1",
    )

    # Classic ВИМОГА expense
    _save_to_warehouse(
        warehouse_db, file_store,
        _make_vimoga_doc(
            items=[{"name": "Кабель ААБл 3х120", "quantity": "30", "unit": "м"}]
        ),
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )

    # Check inventory balance: 100 - 30 = 70
    items = warehouse_db.get_items_with_balance()
    assert len(items) == 1
    assert items[0]["name"] == "Кабель ААБл 3х120"
    assert items[0]["balance"] == 70.0


# ==============================================================================
# Repeat recognition / Idempotency
# ==============================================================================


def test_repeat_recognition_m11_updates_link(warehouse_db, file_store):
    """Re-processing an M-11 document updates its link without leaving duplicate stale rows."""
    v1 = _make_vimoga_doc(
        doc_number="101",
        items=[{"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"}],
    )
    _save_to_warehouse(
        warehouse_db, file_store, v1,
        {"file_name": "v1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v1",
    )
    v1_id = warehouse_db.get_documents()[0]["id"]

    v2 = _make_vimoga_doc(
        doc_number="102",
        items=[{"name": "Муфта термоусаджувальна 10кВ", "quantity": "2", "unit": "шт"}],
    )
    _save_to_warehouse(
        warehouse_db, file_store, v2,
        {"file_name": "v2.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-v2",
    )
    v2_id = warehouse_db.get_documents()[0]["id"]

    # First M-11 recognition matches V1
    m11 = _make_m11_doc(
        items=[{"name": "Кабель ААБл 3х120", "quantity": "50.5", "unit": "м"}]
    )
    _save_to_warehouse(
        warehouse_db, file_store, m11,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
    )
    m11_id = warehouse_db.get_documents()[0]["id"]

    links = warehouse_db.get_document_links()
    assert len(links) == 1
    assert links[0]["vimoga_doc_id"] == v1_id

    # Second recognition of same M-11 (e.g. repeat OCR) matches V2
    m11_updated = _make_m11_doc(
        items=[{"name": "Муфта термоусаджувальна 10кВ", "quantity": "2", "unit": "шт"}]
    )
    _save_to_warehouse(
        warehouse_db, file_store, m11_updated,
        {"file_name": "m1.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "arch-m1",
        existing_doc_id=m11_id,
    )

    # Link should be updated to V2 without duplicate rows
    links = warehouse_db.get_document_links()
    assert len(links) == 1
    assert links[0]["m11_doc_id"] == m11_id
    assert links[0]["vimoga_doc_id"] == v2_id
    assert links[0]["match_status"] == "full"

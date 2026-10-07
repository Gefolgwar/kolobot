"""Unit tests for M-11 document detection and warehouse saving behavior (Issue #46)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pytest

from kolobot.doc_structurer import Document
from kolobot.file_store import FileStore
from kolobot.warehouse_db import WarehouseDB
from kolobot.warehouse_writer import _detect_doc_type_and_op, _save_to_warehouse


@pytest.fixture
def warehouse_db(tmp_path):
    db = WarehouseDB(db_path=str(tmp_path / "warehouse.db"))
    db.init_db()
    try:
        yield db
    finally:
        db.close()


def _make_m11_doc(
    raw_text: str = "Типова форма № М-11\nНАКЛАДНА-ВИМОГА № 42",
    items: Optional[List[Dict[str, Any]]] = None,
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
        doc_type=kwargs.get("doc_type", "вимога м-11"),
        raw_text=raw_text,
        doc_number=kwargs.get("doc_number", "42"),
        doc_date=kwargs.get("doc_date", "15.08.2026"),
        requested_by=kwargs.get("requested_by", "Іванов І.І."),
        requested_via=kwargs.get("requested_via", "Петров П.П."),
        items=items,
        **{k: v for k, v in kwargs.items() if k not in ("doc_type", "doc_number", "doc_date", "requested_by", "requested_via")},
    )


def test_detect_doc_type_and_op_m11_returns_empty_operation():
    """_detect_doc_type_and_op повертає ('ВИМОГА М-11', '') для М-11 (порожня операція = без транзакцій)."""
    # 1. За regex у raw_text
    doc1 = Document(
        raw_text="Типова форма № М-11\nНАКЛАДНА-ВИМОГА на відпуск",
        doc_type="інше",
    )
    doc_type, op = _detect_doc_type_and_op(doc1)
    assert doc_type == "ВИМОГА М-11"
    assert op == ""

    # 2. Різні варіації написання
    for text in (
        "типова форма № м-11",
        "ТИПОВА ФОРМА М-11",
        "Типова форма  №  м 11",
        "Типова форма № м - 11",
    ):
        doc = Document(raw_text=text)
        assert _detect_doc_type_and_op(doc) == ("ВИМОГА М-11", "")

    # 3. За явним doc_type
    doc3 = Document(raw_text="", doc_type="вимога м-11")
    assert _detect_doc_type_and_op(doc3) == ("ВИМОГА М-11", "")


def test_detect_doc_type_and_op_preserves_vymoga_and_nakladna():
    """Перевірка, що класичні ВИМОГА та НАКЛАДНА не поламані."""
    vymoga = Document(raw_text="ВИМОГА № 101\nВідпустити зі складу", doc_type="вимога")
    assert _detect_doc_type_and_op(vymoga) == ("ВИМОГА", "expense")

    nakladna = Document(raw_text="ВИДАТКОВА НАКЛАДНА № 202", doc_type="накладна")
    assert _detect_doc_type_and_op(nakladna) == ("НАКЛАДНА", "income")


def test_save_to_warehouse_m11_saves_items_and_skips_transactions(warehouse_db, tmp_path):
    """М-11 зберігає позиції в m11_items, не створює warehouse_items та warehouse_transactions."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    doc = _make_m11_doc()

    summary = _save_to_warehouse(
        warehouse_db,
        file_store,
        doc,
        {"file_name": "m11_doc.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "doc-m11-1",
    )

    # 1. Документ збережено в таблиці documents
    docs = warehouse_db.get_documents()
    assert len(docs) == 1
    doc_row = docs[0]
    assert doc_row["doc_type"] == "ВИМОГА М-11"
    assert doc_row["doc_number"] == "42"

    # 2. Позиції збережено в m11_items
    m11_items = warehouse_db.get_m11_items_by_document(doc_row["id"])
    assert len(m11_items) == 2
    assert m11_items[0]["name"] == "Муфта термоусаджувальна 10кВ"
    assert m11_items[0]["quantity"] == 2.0
    assert m11_items[0]["unit"] == "шт"
    assert m11_items[0]["nomenclature_number"] == "00-00059398"

    assert m11_items[1]["name"] == "Кабель ААБл 3х120"
    assert m11_items[1]["quantity"] == 50.5
    assert m11_items[1]["unit"] == "м"
    assert m11_items[1]["nomenclature_number"] == "00-00059399"

    # 3. НЕ створено складських позицій або транзакцій
    cur_tx = warehouse_db._conn.execute("SELECT COUNT(*) as cnt FROM warehouse_transactions")
    assert cur_tx.fetchone()["cnt"] == 0

    cur_wh_items = warehouse_db._conn.execute("SELECT COUNT(*) as cnt FROM warehouse_items")
    assert cur_wh_items.fetchone()["cnt"] == 0

    # 4. Баланс складу порожній
    assert len(warehouse_db.get_items_with_balance()) == 0


def test_save_to_warehouse_m11_repeat_recognition_updates_m11_items(warehouse_db, tmp_path):
    """Повторне розпізнавання М-11 оновлює m11_items без дублювання."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    doc1 = _make_m11_doc()

    _save_to_warehouse(
        warehouse_db,
        file_store,
        doc1,
        {"file_name": "m11_doc.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "doc-m11-1",
    )
    doc_id = warehouse_db.get_documents()[0]["id"]
    assert len(warehouse_db.get_m11_items_by_document(doc_id)) == 2

    # Другий прохід з іншими позиціями
    doc2 = _make_m11_doc(
        items=[
            {
                "num": 1,
                "name": "Нова позиція",
                "quantity": "10",
                "unit": "шт",
                "nomenclature_number": "999",
            }
        ]
    )
    _save_to_warehouse(
        warehouse_db,
        file_store,
        doc2,
        {"file_name": "m11_doc.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "doc-m11-1",
        existing_doc_id=doc_id,
    )

    m11_items = warehouse_db.get_m11_items_by_document(doc_id)
    assert len(m11_items) == 1
    assert m11_items[0]["name"] == "Нова позиція"
    assert m11_items[0]["quantity"] == 10.0

    # Транзакцій все одно 0
    cur_tx = warehouse_db._conn.execute("SELECT COUNT(*) as cnt FROM warehouse_transactions")
    assert cur_tx.fetchone()["cnt"] == 0

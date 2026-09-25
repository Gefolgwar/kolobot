"""Issue #32: повторне розпізнавання не подвоює транзакції документа."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from kolobot.doc_structurer import Document
from kolobot.file_store import FileStore
from kolobot.main import _save_to_warehouse
from kolobot.warehouse_db import WarehouseDB


@pytest.fixture
def warehouse_db(tmp_path):
    db = WarehouseDB(db_path=str(tmp_path / "warehouse.db"))
    db.init_db()
    try:
        yield db
    finally:
        db.close()


def _doc(items: Optional[List[Dict[str, Any]]] = None) -> Document:
    return Document(
        doc_type="накладна",
        raw_text="НАКЛАДНА №101",
        doc_number="101",
        doc_date="01.08.2026",
        requested_by="начальник служби (ПІБ)",
        requested_via="7939 - (ПІБ)",
        items=items
        if items is not None
        else [{"name": "Болт М8", "nomenclature_number": "SKU-001", "unit": "шт", "quantity": "5"}],
    )


def _save(wdb: WarehouseDB, file_store: FileStore, doc: Document, existing_doc_id: Optional[int] = None) -> str:
    return _save_to_warehouse(
        wdb,
        file_store,
        doc,
        {"file_name": "nakladna_101.jpg", "ext": ".jpg", "mime": "image/jpeg"},
        "doc-1",
        existing_doc_id=existing_doc_id,
    )


def test_repeat_recognition_does_not_double_transactions(warehouse_db, tmp_path):
    """Повтор розпізнавання замінює транзакції документа, а не додає нові до старих."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    doc = _doc()

    _save(warehouse_db, file_store, doc)
    doc_id = warehouse_db.get_documents()[0]["id"]
    item_id = warehouse_db.get_items_with_balance()[0]["id"]

    assert len(warehouse_db.get_document_impact(doc_id)) == 1
    assert warehouse_db.get_item_balance(item_id) == 5.0

    # Другий прохід того самого документа — саме це робить кнопка «Повторити».
    _save(warehouse_db, file_store, doc, existing_doc_id=doc_id)

    assert len(warehouse_db.get_document_impact(doc_id)) == 1
    assert warehouse_db.get_item_balance(item_id) == 5.0
    assert warehouse_db.get_document(doc_id)["status"] == "completed"


def test_repeat_recognition_writes_exactly_the_new_positions(warehouse_db, tmp_path):
    """Після повтору транзакцій рівно стільки, скільки позицій у новому результаті."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    _save(warehouse_db, file_store, _doc())
    doc_id = warehouse_db.get_documents()[0]["id"]

    new_items = [
        {"name": "Болт М8", "nomenclature_number": "SKU-001", "unit": "шт", "quantity": "7"},
        {"name": "Гайка М8", "nomenclature_number": "SKU-002", "unit": "шт", "quantity": "9"},
    ]
    _save(warehouse_db, file_store, _doc(items=new_items), existing_doc_id=doc_id)

    impact = warehouse_db.get_document_impact(doc_id)
    assert len(impact) == 2
    assert sorted(tx["quantity"] for tx in impact) == [7.0, 9.0]
    assert warehouse_db.get_item_balance(
        warehouse_db.find_item(sku="SKU-001")["id"]
    ) == 7.0


def test_repeat_recognition_keeps_warehouse_items_and_manual_fields(warehouse_db, tmp_path):
    """Позиції складу з ручними полями при повторі не видаляються."""
    file_store = FileStore(downloads_path=str(tmp_path / "downloads"))
    _save(warehouse_db, file_store, _doc())
    doc_id = warehouse_db.get_documents()[0]["id"]
    item_id = warehouse_db.find_item(sku="SKU-001")["id"]
    warehouse_db.update_item(item_id, supplier="ТОВ Постач", notes="Мій коментар", min_balance=3.0)

    _save(warehouse_db, file_store, _doc(), existing_doc_id=doc_id)

    item = warehouse_db.get_item(item_id)
    assert item is not None
    assert item["supplier"] == "ТОВ Постач"
    assert item["notes"] == "Мій коментар"
    assert item["min_balance"] == 3.0

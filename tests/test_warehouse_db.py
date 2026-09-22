"""Unit tests for WarehouseDB item metadata adjustment and audit logging."""

from __future__ import annotations

import datetime
import sqlite3

import pytest

from kolobot.warehouse_db import WarehouseDB


@pytest.fixture
def warehouse_db(tmp_path):
    db_path = str(tmp_path / "warehouse.db")
    db = WarehouseDB(db_path=db_path)
    db.init_db()
    try:
        yield db
    finally:
        db.close()


def test_adjust_item_field_name_creates_audit_transaction(warehouse_db):
    # 1. Add initial doc and item
    doc_id = warehouse_db.add_document(
        filename="nakladna_1.xlsx",
        file_type="excel",
        doc_type="НАКЛАДНА",
        doc_number="101",
        doc_date="01.08.2026",
    )
    item_id = warehouse_db.add_item(
        name="Болт М8",
        sku="SKU-001",
        unit="шт",
        supplier="ТОВ Постач",
        notes="Стандартний",
    )
    warehouse_db.add_transaction(
        item_id=item_id,
        document_id=doc_id,
        operation_type="income",
        quantity=50.0,
        doc_number="101",
        doc_date="01.08.2026",
    )

    # 2. Adjust name
    result = warehouse_db.adjust_item_field(
        item_id=item_id,
        field="name",
        new_value="Болт М8х30 Оцинкований",
        comment="Уточнення розміру",
    )

    assert result is not None
    assert result["success"] is True
    assert result["item"]["name"] == "Болт М8х30 Оцинкований"
    assert result["old_value"] == "Болт М8"
    assert result["new_value"] == "Болт М8х30 Оцинкований"

    # 3. Verify item updated in DB
    item = warehouse_db.find_item(name="Болт М8х30 Оцинкований")
    assert item is not None
    assert item["id"] == item_id

    # 4. Verify balance is preserved
    items = warehouse_db.get_items_with_balance()
    assert len(items) == 1
    assert items[0]["name"] == "Болт М8х30 Оцинкований"
    assert items[0]["total_income"] == 50.0
    assert items[0]["total_expense"] == 0.0
    assert items[0]["balance"] == 50.0

    # 5. Verify audit transaction in item transaction history
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 2

    # Second transaction is the zero-quantity audit record
    audit_tx = txs[1]
    assert audit_tx["quantity"] == 0.0
    assert audit_tx["operation_type"] == "income"
    assert audit_tx["running_balance"] == 50.0
    assert audit_tx["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"
    assert audit_tx["filename"] == "Ручне редагування (Користувач)"
    assert audit_tx["file_type"] == "manual"
    assert "Змінено [Найменування]: 'Болт М8' → 'Болт М8х30 Оцинкований'" in audit_tx["source_row"]
    assert "Уточнення розміру" in audit_tx["source_row"]


def test_adjust_item_other_fields(warehouse_db):
    item_id = warehouse_db.add_item(
        name="Гайка М6",
        sku="OLD-SKU",
        unit="шт",
        supplier="Старий Постачальник",
        notes="Стара примітка",
    )
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    warehouse_db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=100.0)

    # Adjust SKU
    res_sku = warehouse_db.adjust_item_field(item_id=item_id, field="sku", new_value="NEW-SKU-999")
    assert res_sku["success"] is True
    assert "Змінено [Номенклатурний номер]: 'OLD-SKU' → 'NEW-SKU-999'" in res_sku["source_row"]

    # Adjust Unit
    res_unit = warehouse_db.adjust_item_field(item_id=item_id, field="unit", new_value="компл")
    assert res_unit["success"] is True
    assert "Змінено [Од. виміру]: 'шт' → 'компл'" in res_unit["source_row"]

    # Adjust Supplier
    res_sup = warehouse_db.adjust_item_field(item_id=item_id, field="supplier", new_value="Новий Постачальник")
    assert res_sup["success"] is True
    assert "Змінено [Постачальник]: 'Старий Постачальник' → 'Новий Постачальник'" in res_sup["source_row"]

    # Adjust Notes
    res_not = warehouse_db.adjust_item_field(item_id=item_id, field="notes", new_value="Оновлена примітка")
    assert res_not["success"] is True
    assert "Змінено [Примітки]: 'Стара примітка' → 'Оновлена примітка'" in res_not["source_row"]

    # Verify transactions count
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 5  # 1 initial + 4 adjustments
    assert all(tx["running_balance"] == 100.0 for tx in txs[1:])


def test_adjust_item_field_reuses_manual_document(warehouse_db):
    item1_id = warehouse_db.add_item(name="Item 1")
    item2_id = warehouse_db.add_item(name="Item 2")
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    warehouse_db.add_transaction(item_id=item1_id, document_id=doc_id, operation_type="income", quantity=10)
    warehouse_db.add_transaction(item_id=item2_id, document_id=doc_id, operation_type="income", quantity=20)

    warehouse_db.adjust_item_field(item_id=item1_id, field="name", new_value="Item 1 Edited")
    warehouse_db.adjust_item_field(item_id=item2_id, field="name", new_value="Item 2 Edited")

    docs = warehouse_db.get_documents()
    manual_docs = [d for d in docs if d["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"]
    assert len(manual_docs) == 1
    assert manual_docs[0]["transaction_count"] == 2


def test_adjust_item_field_nonexistent_and_invalid(warehouse_db):
    # Nonexistent item
    res_none = warehouse_db.adjust_item_field(item_id=9999, field="name", new_value="Test")
    assert res_none is None

    # Invalid field
    item_id = warehouse_db.add_item(name="Valid Item")
    with pytest.raises(ValueError, match="Invalid field"):
        warehouse_db.adjust_item_field(item_id=item_id, field="balance", new_value="100")


def test_adjust_item_quantity_positive_delta_creates_income_transaction(warehouse_db):
    # Initial balance: 50
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    item_id = warehouse_db.add_item(name="Кабель ВВГ", sku="CAB-01", unit="м")
    warehouse_db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=50.0)

    # Adjust target quantity to 80 (delta = +30)
    result = warehouse_db.adjust_item_quantity(
        item_id=item_id,
        target_quantity=80.0,
        comment="Перерахунок залишку",
    )

    assert result is not None
    assert result["success"] is True
    assert result["old_balance"] == 50.0
    assert result["target_quantity"] == 80.0
    assert result["delta"] == 30.0
    assert result["operation_type"] == "income"
    assert result["transaction_id"] is not None
    assert "Змінено 'Кількість': 50 → 80 (Перерахунок залишку)" in result["source_row"]

    # Verify balance reconciliation
    items = warehouse_db.get_items_with_balance()
    cab = next(i for i in items if i["id"] == item_id)
    assert cab["total_income"] == 80.0
    assert cab["total_expense"] == 0.0
    assert cab["balance"] == 80.0

    # Verify transactions history
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 2
    adj_tx = txs[1]
    assert adj_tx["quantity"] == 30.0
    assert adj_tx["operation_type"] == "income"
    assert adj_tx["running_balance"] == 80.0
    assert adj_tx["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"
    assert adj_tx["filename"] == "Ручне редагування (Користувач)"


def test_adjust_item_quantity_negative_delta_creates_expense_transaction(warehouse_db):
    # Initial balance: 100
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    item_id = warehouse_db.add_item(name="Труба ПВХ", sku="TR-01", unit="м")
    warehouse_db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=100.0)

    # Adjust target quantity to 65 (delta = -35 -> expense of 35)
    result = warehouse_db.adjust_item_quantity(
        item_id=item_id,
        target_quantity=65.0,
        comment="Списання браку",
    )

    assert result is not None
    assert result["success"] is True
    assert result["old_balance"] == 100.0
    assert result["target_quantity"] == 65.0
    assert result["delta"] == -35.0
    assert result["operation_type"] == "expense"
    assert result["transaction_id"] is not None
    assert "Змінено 'Кількість': 100 → 65 (Списання браку)" in result["source_row"]

    # Verify balance reconciliation
    items = warehouse_db.get_items_with_balance()
    pipe = next(i for i in items if i["id"] == item_id)
    assert pipe["total_income"] == 100.0
    assert pipe["total_expense"] == 35.0
    assert pipe["balance"] == 65.0

    # Verify transactions history
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 2
    adj_tx = txs[1]
    assert adj_tx["quantity"] == 35.0
    assert adj_tx["operation_type"] == "expense"
    assert adj_tx["running_balance"] == 65.0


def test_adjust_item_quantity_zero_delta_no_transaction(warehouse_db):
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    item_id = warehouse_db.add_item(name="Лампа LED", sku="LED-01", unit="шт")
    warehouse_db.add_transaction(item_id=item_id, document_id=doc_id, operation_type="income", quantity=20.0)

    # Target is same as current balance (20.0)
    result = warehouse_db.adjust_item_quantity(
        item_id=item_id,
        target_quantity=20.0,
        comment="Без змін",
    )

    assert result is not None
    assert result["success"] is True
    assert result["delta"] == 0.0
    assert result["transaction_id"] is None

    # Verify no new transaction was created
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 1


def test_adjust_item_quantity_nonexistent_item(warehouse_db):
    result = warehouse_db.adjust_item_quantity(item_id=99999, target_quantity=10.0)
    assert result is None


def test_get_items_with_balance_doc_count(warehouse_db):
    # Item 1 has an excel doc transaction
    doc_id = warehouse_db.add_document(filename="init.xlsx", file_type="excel")
    item1_id = warehouse_db.add_item(name="Item With Doc", sku="SKU-1")
    warehouse_db.add_transaction(item_id=item1_id, document_id=doc_id, operation_type="income", quantity=10.0)

    # Item 2 has only manual adjustment transactions (no non-manual docs)
    item2_id = warehouse_db.add_item(name="Item Manual Only", sku="SKU-2")
    warehouse_db.adjust_item_quantity(item_id=item2_id, target_quantity=5.0)

    # Item 3 has no transactions at all
    item3_id = warehouse_db.add_item(name="Item No Tx", sku="SKU-3")

    items = warehouse_db.get_items_with_balance()
    items_map = {it["id"]: it for it in items}

    assert items_map[item1_id]["doc_count"] == 1
    assert items_map[item2_id]["doc_count"] == 0
    assert items_map[item3_id]["doc_count"] == 0


def test_adjust_item_field_min_balance(warehouse_db):
    item_id = warehouse_db.add_item(
        name="Гайка М8",
        sku="NUT-M8",
        min_balance=0.0,
    )

    # 1. Adjust min_balance to 25.0
    res = warehouse_db.adjust_item_field(item_id=item_id, field="min_balance", new_value=25.0, comment="Норма запасу")
    assert res is not None
    assert res["success"] is True
    assert res["new_value"] == 25.0
    assert "Змінено [Мінімальний залишок]: '0' → '25'" in res["source_row"]
    assert "Норма запасу" in res["source_row"]

    # 2. Check item from find_item and get_item
    item = warehouse_db.get_item(item_id)
    assert item["min_balance"] == 25.0

    # 3. Check get_items_with_balance
    items = warehouse_db.get_items_with_balance()
    assert len(items) == 1
    assert items[0]["min_balance"] == 25.0

    # 4. Check audit transaction
    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 1
    assert txs[0]["doc_type"] == "РУЧНЕ_КОРИГУВАННЯ"
    assert txs[0]["quantity"] == 0.0


def test_add_item_with_min_balance(warehouse_db):
    item_id = warehouse_db.add_item(
        name="Шайба М10",
        sku="WASH-10",
        min_balance=100.0,
    )
    item = warehouse_db.get_item(item_id)
    assert item["min_balance"] == 100.0

    items = warehouse_db.get_items_with_balance()
    assert items[0]["min_balance"] == 100.0


def test_init_db_migrates_legacy_documents_to_completed_status(tmp_path):
    """Existing DBs without status columns: old rows must become 'completed'."""
    db_path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL DEFAULT '',
            uploaded_at REAL NOT NULL,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            raw_text TEXT NOT NULL DEFAULT '',
            doc_type TEXT NOT NULL DEFAULT ''
        );
    """)
    conn.execute(
        "INSERT INTO documents (filename, file_type, uploaded_at) VALUES (?, ?, ?)",
        ("legacy.jpg", "photo", 1.0),
    )
    conn.commit()
    conn.close()

    db = WarehouseDB(db_path=db_path)
    db.init_db()
    try:
        doc = db.get_document(1)
        assert doc["status"] == "completed"
        assert doc["error_message"] == ""
    finally:
        db.close()


def test_add_document_registers_queued_status_with_saved_file_path(warehouse_db):
    doc_id = warehouse_db.add_document(
        filename="nakladna_1.jpg",
        file_type="photo",
        file_path="/downloads/tmp/a1b2c3.jpg",
        status="queued",
    )

    doc = warehouse_db.get_document(doc_id)
    assert doc["status"] == "queued"
    assert doc["error_message"] == ""
    assert doc["file_path"] == "/downloads/tmp/a1b2c3.jpg"

    docs = warehouse_db.get_documents()
    assert len(docs) == 1
    assert docs[0]["status"] == "queued"


def test_update_document_completes_queued_record_in_place(warehouse_db):
    doc_id = warehouse_db.add_document(
        filename="photo.jpg",
        file_type="photo",
        file_path="/downloads/tmp/a1b2c3.jpg",
        status="queued",
    )

    updated = warehouse_db.update_document(
        doc_id,
        file_path="/downloads/abcdef1234.jpg",
        doc_number="101",
        doc_date="01.08.2026",
        doc_type="НАКЛАДНА",
        raw_text="НАКЛАДНА № 101",
        status="completed",
    )

    assert updated is True
    assert len(warehouse_db.get_documents()) == 1

    doc = warehouse_db.get_document(doc_id)
    assert doc["status"] == "completed"
    assert doc["file_path"] == "/downloads/abcdef1234.jpg"
    assert doc["doc_number"] == "101"
    assert doc["doc_type"] == "НАКЛАДНА"
    assert doc["raw_text"] == "НАКЛАДНА № 101"


def test_update_document_unknown_id_returns_false(warehouse_db):
    assert warehouse_db.update_document(9999, status="completed") is False


def test_add_document_persists_requested_by(warehouse_db):
    """Затребувач зберігається в документі і віддається в списку документів."""
    doc_id = warehouse_db.add_document(
        filename="nakladna_1.jpg",
        file_type="photo",
        requested_by="начальник служби (ПІБ)",
    )

    doc = warehouse_db.get_document(doc_id)
    assert doc["requested_by"] == "начальник служби (ПІБ)"

    docs = warehouse_db.get_documents()
    assert docs[0]["requested_by"] == "начальник служби (ПІБ)"


def test_update_document_can_set_requested_by(warehouse_db):
    """Затребувач дописується у вже наявний документ (напр. після повторного розпізнавання)."""
    doc_id = warehouse_db.add_document(filename="nakladna_2.jpg", file_type="photo")

    assert warehouse_db.update_document(doc_id, requested_by="механік (ПІБ)") is True
    assert warehouse_db.get_document(doc_id)["requested_by"] == "механік (ПІБ)"


def test_item_transactions_expose_document_requested_by(warehouse_db):
    """У розгорнутому рядку позиції (Склад) видно, хто затребував кожен документ."""
    doc_id = warehouse_db.add_document(
        filename="vymoha.jpg",
        file_type="photo",
        doc_type="ВИМОГА",
        requested_by="начальник служби (ПІБ)",
    )
    item_id = warehouse_db.add_item(name="Болт М8", sku="SKU-001", unit="шт")
    warehouse_db.add_transaction(
        item_id=item_id,
        document_id=doc_id,
        operation_type="expense",
        quantity=5.0,
    )

    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 1
    assert txs[0]["requested_by"] == "начальник служби (ПІБ)"


def test_add_document_persists_requested_via(warehouse_db):
    """'Через кого' зберігається в документі і віддається в списку документів."""
    doc_id = warehouse_db.add_document(
        filename="nakladna_1.jpg",
        file_type="photo",
        requested_via="7939 - (ПІБ)",
    )

    doc = warehouse_db.get_document(doc_id)
    assert doc["requested_via"] == "7939 - (ПІБ)"

    docs = warehouse_db.get_documents()
    assert docs[0]["requested_via"] == "7939 - (ПІБ)"


def test_update_document_can_set_requested_via(warehouse_db):
    """'Через кого' дописується у вже наявний документ (напр. після повторного розпізнавання)."""
    doc_id = warehouse_db.add_document(filename="nakladna_2.jpg", file_type="photo")

    assert warehouse_db.update_document(doc_id, requested_via="6461 - механік (ПІБ)") is True
    assert warehouse_db.get_document(doc_id)["requested_via"] == "6461 - механік (ПІБ)"


def test_item_transactions_expose_document_requested_via(warehouse_db):
    """У розгорнутому рядку позиції (Склад) видно, через кого отримано кожен документ."""
    doc_id = warehouse_db.add_document(
        filename="vymoha.jpg",
        file_type="photo",
        doc_type="ВИМОГА",
        requested_via="7939 - (ПІБ)",
    )
    item_id = warehouse_db.add_item(name="Болт М8", sku="SKU-001", unit="шт")
    warehouse_db.add_transaction(
        item_id=item_id,
        document_id=doc_id,
        operation_type="expense",
        quantity=5.0,
    )

    txs = warehouse_db.get_item_transactions(item_id)
    assert len(txs) == 1
    assert txs[0]["requested_via"] == "7939 - (ПІБ)"


def test_migration_backfills_requester_fields_from_existing_raw_text(tmp_path):
    """Документи, збережені до появи полів, отримують затребувача і 'через кого' зі свого OCR-тексту."""
    db_path = str(tmp_path / "legacy.db")

    # БД попередньої версії: колонок requested_by / requested_via ще немає.
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL DEFAULT '',
            uploaded_at REAL NOT NULL,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            raw_text TEXT NOT NULL DEFAULT '',
            doc_type TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE warehouse_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL DEFAULT '',
            name TEXT NOT NULL,
            unit TEXT NOT NULL DEFAULT '',
            supplier TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE warehouse_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL REFERENCES warehouse_items(id),
            document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
            operation_type TEXT NOT NULL CHECK(operation_type IN ('income', 'expense')),
            quantity REAL NOT NULL DEFAULT 0,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL
        );
    """)
    conn.execute(
        "INSERT INTO documents (filename, file_type, uploaded_at, raw_text, doc_type) VALUES (?, ?, ?, ?, ?)",
        (
            "old_nakladna.jpg",
            "photo",
            1.0,
            "НАКЛАДНА № 0002143\nЧЕРЕЗ КОГО 7939 - (ПІБ)\nЗАТРЕБУВАВ: начальник служби (ПІБ)\nБУХГАЛТЕР:",
            "НАКЛАДНА",
        ),
    )
    conn.execute(
        "INSERT INTO documents (filename, file_type, uploaded_at, raw_text, doc_type) VALUES (?, ?, ?, ?, ?)",
        ("old_excel.xlsx", "excel", 2.0, "", ""),
    )
    conn.commit()
    conn.close()

    db = WarehouseDB(db_path=db_path)
    db.init_db()
    try:
        docs = {d["filename"]: d for d in db.get_documents()}
        assert docs["old_nakladna.jpg"]["requested_by"] == "начальник служби (ПІБ)"
        assert docs["old_nakladna.jpg"]["requested_via"] == "7939 - (ПІБ)"
        assert docs["old_excel.xlsx"]["requested_by"] == ""
        assert docs["old_excel.xlsx"]["requested_via"] == ""
    finally:
        db.close()


def test_migration_handles_db_that_already_has_requested_by(tmp_path):
    """БД, мігрована попередньою версією (є requested_by, немає requested_via), дозаповнюється коректно."""
    db_path = str(tmp_path / "half_migrated.db")

    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL DEFAULT '',
            uploaded_at REAL NOT NULL,
            doc_number TEXT NOT NULL DEFAULT '',
            doc_date TEXT NOT NULL DEFAULT '',
            raw_text TEXT NOT NULL DEFAULT '',
            doc_type TEXT NOT NULL DEFAULT '',
            requested_by TEXT NOT NULL DEFAULT ''
        );
    """)
    conn.execute(
        "INSERT INTO documents (filename, file_type, uploaded_at, raw_text, requested_by) VALUES (?, ?, ?, ?, ?)",
        (
            "half.jpg",
            "photo",
            1.0,
            "НАКЛАДНА № 1\nЧЕРЕЗ КОГО 7939 - (ПІБ)\nЗАТРЕБУВАВ: начальник служби (ПІБ)",
            "",
        ),
    )
    conn.commit()
    conn.close()

    db = WarehouseDB(db_path=db_path)
    db.init_db()
    try:
        doc = db.get_documents()[0]
        assert doc["requested_by"] == "начальник служби (ПІБ)"
        assert doc["requested_via"] == "7939 - (ПІБ)"
    finally:
        db.close()




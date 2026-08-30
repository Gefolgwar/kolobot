"""Unit tests for WarehouseDB item metadata adjustment and audit logging."""

from __future__ import annotations

import datetime
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



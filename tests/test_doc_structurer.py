"""DocStructurer: parse, retry, raw fallback, card view model."""

from __future__ import annotations

import json

import pytest

from kolobot.doc_structurer import DocStructurer, ParseStatus


VALID_JSON = json.dumps({
    "doc_type": "receipt",
    "title": "ПриватБанк чек",
    "summary": "Оплата комунальних",
    "key_value_pairs": [
        {"key": "Сума", "value": "1234.56 грн"},
        {"key": "Дата", "value": "2026-07-15"},
        {"key": "Одержувач", "value": "Водоканал"},
    ],
    "raw_text": "ПриватБанк чек оплата комунальних ...",
    "language": "uk",
})

INVALID_JSON = "this is not json at all {{"

VALID_JSON_MISSING_FIELDS = json.dumps({"doc_type": "note"})


def test_parse_valid_json():
    ds = DocStructurer()
    result = ds.parse(VALID_JSON)
    assert result.status == ParseStatus.OK
    assert result.doc.title == "ПриватБанк чек"
    assert result.doc.doc_type == "receipt"
    assert len(result.doc.key_value_pairs) == 3
    assert result.doc.raw_text != ""


def test_parse_invalid_json_signals_retry():
    ds = DocStructurer()
    result = ds.parse(INVALID_JSON)
    assert result.status == ParseStatus.NEEDS_RETRY


def test_parse_after_retry_still_invalid_becomes_raw_fallback():
    ds = DocStructurer()
    first = ds.parse(INVALID_JSON)
    assert first.status == ParseStatus.NEEDS_RETRY

    result = ds.parse(INVALID_JSON, is_retry=True)
    assert result.status == ParseStatus.RAW_FALLBACK
    assert result.doc is not None
    assert result.doc.doc_type == "other"
    assert result.doc.raw_text == INVALID_JSON


def test_parse_missing_fields_fills_defaults():
    ds = DocStructurer()
    result = ds.parse(VALID_JSON_MISSING_FIELDS)
    assert result.status == ParseStatus.OK
    assert result.doc.doc_type == "note"
    assert result.doc.summary == ""
    assert result.doc.raw_text == ""


def test_card_caps_kv_at_8():
    many_kvs = json.dumps({
        "doc_type": "invoice",
        "title": "Big Invoice",
        "summary": "Many items",
        "key_value_pairs": [{"key": f"k{i}", "value": f"v{i}"} for i in range(20)],
        "raw_text": "raw...",
        "language": "en",
    })
    ds = DocStructurer()
    result = ds.parse(many_kvs)
    card = ds.to_card(result.doc)
    assert len(card.key_value_pairs) <= 8


def test_card_truncates_long_values():
    long_kv = json.dumps({
        "doc_type": "note",
        "title": "A" * 500,
        "summary": "B" * 500,
        "key_value_pairs": [{"key": "long", "value": "X" * 1000}],
        "raw_text": "raw",
        "language": "uk",
    })
    ds = DocStructurer()
    result = ds.parse(long_kv)
    card = ds.to_card(result.doc)
    assert len(card.title) <= 200
    assert len(card.summary) <= 300
    for kv in card.key_value_pairs:
        assert len(kv["value"]) <= 200


def test_empty_raw_text_yields_no_save():
    empty = json.dumps({
        "doc_type": "other",
        "title": "",
        "summary": "",
        "key_value_pairs": [],
        "raw_text": "",
        "language": "",
    })
    ds = DocStructurer()
    result = ds.parse(empty)
    assert result.doc.is_empty


def test_raw_fallback_from_blank_retry():
    ds = DocStructurer()
    result = ds.parse("", is_retry=True)
    assert result.status == ParseStatus.RAW_FALLBACK
    assert result.doc.is_empty


def test_parse_tabular_json():
    json_str = json.dumps({
        "doc_type": "invoice",
        "title": "Рахунок-фактура",
        "summary": "Матеріали",
        "doc_number": "3",
        "doc_date": "04.01.2024",
        "items": [
            {
                "num": 1,
                "name": "лак меблівий",
                "quantity": "10",
                "unit": "банки",
                "price_no_vat": "150.00",
                "total_no_vat": "1500.00",
            }
        ],
        "totals": {
            "total_no_vat": "1975.00",
            "vat": "395.00",
            "total_with_vat": "2370.00",
        },
        "raw_text": "Рахунок...",
        "language": "uk",
    })
    ds = DocStructurer()
    result = ds.parse(json_str)
    assert result.status == ParseStatus.OK
    assert result.doc.doc_number == "3"
    assert result.doc.doc_date == "04.01.2024"
    assert len(result.doc.items) == 1
    assert result.doc.items[0]["name"] == "лак меблівий"
    assert result.doc.totals["total_with_vat"] == "2370.00"


def test_fallback_text_parser():
    sample_text = (
        "Document Number: 3\n"
        "Date: 04.01.2024\n"
        "№ Товар Кількість Од. Ціна без ПДВ Сума без ПДВ\n"
        "1 лак меблівий акрил-поліуретановий Trae Lux Moebel lak (0,25л) 10 банки 150,00 1500,00\n"
        "2 ДВП СТ-40 (2.5мм×2440 мм ×1220 мм) 5 лист 95,00 475,00\n"
        "Всього: 1975,00\n"
        "Сума без ПДВ: 395,00\n"
        "Всього з ПДВ: 2370,00"
    )
    fb = DocStructurer.parse_fallback_text(sample_text)
    assert fb["doc_number"] == "3"
    assert fb["doc_date"] == "04.01.2024"
    assert len(fb["items"]) == 2
    assert fb["items"][0]["num"] == 1
    assert "лак" in fb["items"][0]["name"]
    assert fb["items"][0]["quantity"] == "10"
    assert fb["items"][0]["unit"] == "банки"
    assert fb["items"][0]["price_no_vat"] == "150,00"
    assert fb["items"][0]["total_no_vat"] == "1500,00"

    assert fb["items"][1]["num"] == 2
    assert "ДВП" in fb["items"][1]["name"]
    assert fb["items"][1]["quantity"] == "5"

    assert fb["totals"]["total_no_vat"] == "1975,00"
    assert fb["totals"]["vat"] == "395,00"
    assert fb["totals"]["total_with_vat"] == "2370,00"


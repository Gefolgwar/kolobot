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


def test_normalize_doc_type_vymoha_and_nakladna():
    from kolobot.doc_structurer import normalize_doc_type

    # 1. Direct vymoha keywords
    assert normalize_doc_type(doc_type="вимога") == "вимога"
    assert normalize_doc_type(title="Вимога-накладна № 0000215") == "вимога"
    assert normalize_doc_type(summary="Вимога-накладна на видачу зі складу") == "вимога"
    assert normalize_doc_type(raw_text="ВИМОГА № 0000215\nКІЛЬКІСТЬ ЗАТРЕБУВАНО") == "вимога"

    # 2. Gemini returns 'invoice' but title or text is 'Вимога'
    assert normalize_doc_type(doc_type="invoice", title="Вимога № 0000215") == "вимога"
    assert normalize_doc_type(doc_type="invoice", summary="Вимога-накладна № 0000215 від 15.08.2026") == "вимога"
    assert normalize_doc_type(doc_type="invoice", raw_text="ВИМОГА № 0000215\nВІДПУСТИВ") == "вимога"

    # 3. Nakladna keywords
    assert normalize_doc_type(doc_type="накладна") == "накладна"
    assert normalize_doc_type(title="Видаткова накладна № 12") == "накладна"
    assert normalize_doc_type(doc_type="invoice", title="Накладна на кабель ВВГ") == "накладна"
    assert normalize_doc_type(doc_type="receipt", title="Прибутковий чек") == "накладна"
    assert normalize_doc_type(doc_type="receipt", title="Чек з Епіцентру") == "receipt"

    # 4. Other types
    assert normalize_doc_type(doc_type="contract") == "contract"
    assert normalize_doc_type(doc_type="note") == "note"


def test_parse_vymoha_document_exact_user_case():
    json_str = json.dumps({
        "doc_type": "invoice",
        "title": "Вимога № 0000215",
        "summary": "Вимога-накладна № 0000215 від 15.08.2026 року на видачу зі складу",
        "doc_number": "0000215",
        "doc_date": "15.08.2026",
        "items": [
            {
                "num": 1,
                "nomenclature_number": "461993787922",
                "name": "АКУМУЛЯТОРНА БАТАРЕЯ 60Ач",
                "quantity": "1.000000",
                "unit": "51",
                "price_no_vat": "3100",
                "total_no_vat": "3100",
            },
            {
                "num": 2,
                "nomenclature_number": "461993787923",
                "name": "ЩІТКИ СКЛООЧИСНИКА 600мм",
                "quantity": "8.000000",
                "unit": "51",
                "price_no_vat": "150",
                "total_no_vat": "1200",
            },
        ],
        "totals": {"total_no_vat": "4300", "vat": "0", "total_with_vat": "4300"},
        "raw_text": "ВИМОГА № 0000215\nВІДПУСТИВ: комірник\nОДЕРЖАВ: СІДОРЕНКО",
        "language": "uk",
    })
    ds = DocStructurer()
    result = ds.parse(json_str)
    assert result.status == ParseStatus.OK
    assert result.doc.doc_type == "вимога"
    card = ds.to_card(result.doc)
    assert card.doc_type == "вимога"
    assert len(card.items) == 2


def test_parse_nakladna_with_vidpusk_in_summary_condensator():
    """Verify that Nakladna with 'відпуск' in summary and 'ВІДПУСТИВ' in text remains 'накладна'."""
    json_str = json.dumps({
        "doc_type": "invoice",
        "title": "Накладна № 00002143",
        "summary": "Накладна № 00002143 від 03.08.2026 на відпуск матеріалу КОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В у кількості 250 шт на суму 12.50 грн.",
        "doc_number": "00002143",
        "doc_date": "03.08.2026",
        "items": [
            {
                "num": 1,
                "nomenclature_number": "288410091721",
                "name": "КОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В",
                "quantity": "250.000000",
                "unit": "17",
                "price_no_vat": "0.05",
                "total_no_vat": "12.50",
            }
        ],
        "totals": {"total_no_vat": "12.50", "vat": "0.00", "total_with_vat": "12.50"},
        "raw_text": (
            "НАКЛАДНА № К.ГР ДАТА ЛИСТ № ОПЕР СКЛ СКЛ ОТРИМ\n"
            "00002143 1 03.08.2026 16:09:52 1 3 212 402\n"
            "ЧЕРЕЗ КОГО 7939 - (ПІВ) ЗАМОВЛЕННЯ СТ. ВИТРАТ\n"
            "ЗАТРЕБУВАВ начальник служби (ПІВ)\n"
            "1 | 288410091721 | КОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В | 17 | 250.000000 | 250.000000 00 | 0.05 | 12.50\n"
            "БУХГАЛТЕР: ВІДПУСТИВ: службовець на складі (комірник) (ПІВ) ОДЕРЖАВ: службовець на складі (комірник) (ПІВ)"
        ),
        "language": "uk",
    })
    ds = DocStructurer()
    result = ds.parse(json_str)
    assert result.status == ParseStatus.OK
    assert result.doc.doc_type == "накладна"
    card = ds.to_card(result.doc)
    assert card.doc_type == "накладна"
    assert card.title == "Накладна № 00002143"
    assert len(card.items) == 1
    assert card.items[0]["name"] == "КОНДЕНСАТОР КЕРАМІЧНИЙ 0.1мФ 50В"


def test_header_takes_precedence_over_model_doc_type_guess():
    """If Gemini returns doc_type='вимога' but header text says НАКЛАДНА, it must be 'накладна'."""
    from kolobot.doc_structurer import normalize_doc_type
    from kolobot.main import _detect_doc_type_and_op

    raw_header_nakladna = "НАКЛАДНА № 0002143\nК.ГР: 1\nДАТА: 03.08.2026\nЗАТРЕБУВАВ: ...\nВІДПУСТИВ: ..."
    # Even if model returned doc_type="вимога"
    dt = normalize_doc_type(
        doc_type="вимога",
        title="Накладна № 0002143",
        summary="Видача конденсаторів",
        raw_text=raw_header_nakladna,
    )
    assert dt == "накладна"

    doc_mock = type("Doc", (), {
        "doc_type": "вимога",
        "title": "Накладна № 0002143",
        "summary": "Видача конденсаторів",
        "raw_text": raw_header_nakladna,
    })()
    label, op = _detect_doc_type_and_op(doc_mock)
    assert label == "НАКЛАДНА"
    assert op == "income"

    raw_header_vymoha = "ВИМОГА № 0000215\nЗАТРЕБУВАВ: ...\nВІДПУСТИВ: ..."
    dt2 = normalize_doc_type(
        doc_type="накладна",
        title="Вимога № 0000215",
        summary="Накладна на отримання",
        raw_text=raw_header_vymoha,
    )
    assert dt2 == "вимога"

    doc_mock2 = type("Doc", (), {
        "doc_type": "накладна",
        "title": "Вимога № 0000215",
        "summary": "Накладна на отримання",
        "raw_text": raw_header_vymoha,
    })()
    label2, op2 = _detect_doc_type_and_op(doc_mock2)
    assert label2 == "ВИМОГА"
    assert op2 == "expense"


def test_extract_requested_by_with_colon():
    """Затребувач розпізнається, коли у тексті 'ЗАТРЕБУВАВ: <посада (ПІБ)>'."""
    from kolobot.doc_structurer import extract_requested_by

    text = "НАКЛАДНА № 0002143\nЧЕРЕЗ КОГО 7939 - (ПІБ)\nЗАТРЕБУВАВ: начальник служби (ПІБ)\n"
    assert extract_requested_by(text) == "начальник служби (ПІБ)"


def test_extract_requested_by_stops_at_table_header_on_flattened_line():
    """OCR інколи зліплює весь заголовок в один рядок — значення не має тягнути за собою таблицю."""
    from kolobot.doc_structurer import extract_requested_by

    text = (
        "НАКЛАДНА № 0003789 К.ГР 1 ДАТА 03.08.2026 ЛИСТ 1 ОПЕР 3 СКЛ 212 СКЛ ОТРИМ 402 "
        "ЧЕРЕЗ КОГО 7939 - (ПІБ) ЗАМОВЛЕННЯ СТ. ВИТРАТ ЗАТРЕБУВАВ начальник служби (ПІБ) П "
        "НОМЕНКЛАТУРНИЙ НОМЕР НАЙМЕНУВАННЯ, СОРТ, РОЗМІР МАТЕРІАЛУ ОД ВИМ КІЛЬКІСТЬ ЦІНА СУМА "
        "ЗАТРЕБУВАНО ВІДПУЩЕНО 1 311224098765 КАБЕЛЬ СИЛОВИЙ ВВГ-П 3х1,5 ЧОРНИЙ ШТ 25.500000"
    )
    assert extract_requested_by(text) == "начальник служби (ПІБ)"


def test_extract_requested_by_ignores_table_column_header():
    """'ЗАТРЕБУВАНО' — це заголовок колонки таблиці, а не затребувач."""
    from kolobot.doc_structurer import extract_requested_by

    text = (
        "ВИМОГА № 0000215\n"
        "№ п/п | НОМЕНКЛАТУРНИЙ НОМЕР | НАЙМЕНУВАННЯ | ОД ВИМ | ЗАТРЕБУВАНО | ВІДПУЩЕНО | ЦІНА | СУМА\n"
        "1 | 461993787922 | АКУМУЛЯТОРНА БАТАРЕЯ 60Ач | ШТ | 1.000000 | 1.000000 | 3100 | 3100\n"
    )
    assert extract_requested_by(text) == ""
    assert extract_requested_by("") == ""




def test_extract_requested_via_with_colon_and_code():
    """'ЧЕРЕЗ КОГО' розпізнається разом із кодом підрозділу та посадою."""
    from kolobot.doc_structurer import extract_requested_via

    text = "НАКЛАДНА № 0002143\nЧЕРЕЗ КОГО: 6461 - механік (ПІБ)\nЗАТРЕБУВАВ: начальник служби (ПІБ)\n"
    assert extract_requested_via(text) == "6461 - механік (ПІБ)"


def test_extract_requested_via_tolerates_ocr_typo():
    """OCR плутає Г/Т — 'ЧЕРЕЗ КОТО' має розпізнаватись нарівні з 'ЧЕРЕЗ КОГО'."""
    from kolobot.doc_structurer import extract_requested_via

    assert extract_requested_via("ЧЕРЕЗ КОТО: 6465 - механік (ПІБ)\n") == "6465 - механік (ПІБ)"
    assert extract_requested_via("ЧЕРЕЗ КОГО\t7939 - (ПІБ)\tЗАМОВЛЕННЯ") == "7939 - (ПІБ)"


def test_extract_requested_via_stops_at_next_form_field_on_flattened_line():
    """На зліпленому рядку значення не тягне за собою 'ЗАМОВЛЕННЯ СТ. ВИТРАТ' і далі."""
    from kolobot.doc_structurer import extract_requested_via

    text = (
        "НАКЛАДНА № 0003789 К.ГР 1 ДАТА 03.08.2026 ЛИСТ 1 ОПЕР 3 СКЛ 212 СКЛ ОТРИМ 402 "
        "ЧЕРЕЗ КОГО 7939 - (ПІБ) ЗАМОВЛЕННЯ СТ. ВИТРАТ ЗАТРЕБУВАВ начальник служби (ПІБ) П "
        "НОМЕНКЛАТУРНИЙ НОМЕР НАЙМЕНУВАННЯ, СОРТ, РОЗМІР МАТЕРІАЛУ"
    )
    assert extract_requested_via(text) == "7939 - (ПІБ)"


def test_extract_requested_via_absent_returns_empty():
    """Без поля 'ЧЕРЕЗ КОГО' значення порожнє — не підхоплюємо сусідні поля бланка."""
    from kolobot.doc_structurer import extract_requested_via

    assert extract_requested_via("НАКЛАДНА № 1\nЗАТРЕБУВАВ: начальник служби (ПІБ)\n") == ""
    assert extract_requested_via("") == ""


def test_parse_prefers_model_requested_by_field():
    """Якщо Gemini повернув requested_by — беремо його."""
    ds = DocStructurer()
    result = ds.parse(json.dumps({
        "doc_type": "накладна",
        "title": "Накладна № 1",
        "raw_text": "ЗАТРЕБУВАВ: з тексту (ПІБ)",
        "requested_by": "з поля моделі (ПІБ)",
    }))
    assert result.status == ParseStatus.OK
    assert result.doc.requested_by == "з поля моделі (ПІБ)"


def test_parse_falls_back_to_raw_text_for_requested_by():
    """Якщо поля від моделі немає — витягуємо з розпізнаного тексту."""
    ds = DocStructurer()
    result = ds.parse(json.dumps({
        "doc_type": "накладна",
        "title": "Накладна № 2",
        "raw_text": "НАКЛАДНА № 0002143\nЗАТРЕБУВАВ начальник служби (ПІВ)\nБУХГАЛТЕР:",
    }))
    assert result.status == ParseStatus.OK
    assert result.doc.requested_by == "начальник служби (ПІВ)"


def test_parse_prefers_model_requested_via_field():
    """Якщо Gemini повернув requested_via — беремо його."""
    ds = DocStructurer()
    result = ds.parse(json.dumps({
        "doc_type": "накладна",
        "title": "Накладна № 3",
        "raw_text": "ЧЕРЕЗ КОГО: з тексту (ПІБ)",
        "requested_via": "з поля моделі (ПІБ)",
    }))
    assert result.status == ParseStatus.OK
    assert result.doc.requested_via == "з поля моделі (ПІБ)"


def test_parse_falls_back_to_raw_text_for_requested_via():
    """Якщо поля від моделі немає — 'ЧЕРЕЗ КОГО' витягуємо з розпізнаного тексту."""
    ds = DocStructurer()
    result = ds.parse(json.dumps({
        "doc_type": "накладна",
        "title": "Накладна № 4",
        "raw_text": "НАКЛАДНА № 0002143\nЧЕРЕЗ КОГО 7939 - (ПІБ)\nЗАТРЕБУВАВ: начальник служби (ПІБ)",
    }))
    assert result.status == ParseStatus.OK
    assert result.doc.requested_via == "7939 - (ПІБ)"
    assert result.doc.requested_by == "начальник служби (ПІБ)"

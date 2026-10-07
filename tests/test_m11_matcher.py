"""Unit tests for kolobot.m11_matcher.

Covers:
- normalize_name edge cases (whitespace collapsing, lowercase, empty/None, unicode spaces)
- parse_quantity formats (comma/dot decimal, thousands space, trailing zeros, invalid values)
- compare_items match statuses (full, partial, none, order independence, duplicates, empty lists)
- find_best_match candidate selection (best rank, best overlap, tie breaking, empty candidates)
"""

from dataclasses import dataclass
from typing import Any, List

import pytest

from kolobot.m11_matcher import (
    compare_items,
    find_best_match,
    normalize_name,
    parse_quantity,
)


# ============================================================================
# normalize_name tests
# ============================================================================


def test_normalize_name_basic():
    assert normalize_name("Болт М10") == "болт м10"
    assert normalize_name("гайка м8") == "гайка м8"


def test_normalize_name_casing():
    assert normalize_name("ГАЙКА М8 СТАЛЬНА") == "гайка м8 стальна"
    assert normalize_name("КаБеЛь ВВГ") == "кабель ввг"


def test_normalize_name_whitespace_collapsing():
    assert normalize_name("   Болт   М10   х   50   ") == "болт м10 х 50"
    assert normalize_name("Муфта\t\tперехідна\n\nду50") == "муфта перехідна ду50"
    # Unicode non-breaking space
    assert normalize_name("Кран\xa0кульовий\xa01/2") == "кран кульовий 1/2"


def test_normalize_name_empty_and_none():
    assert normalize_name("") == ""
    assert normalize_name("   ") == ""
    assert normalize_name(None) == ""


def test_normalize_name_with_punctuation_and_numbers():
    assert normalize_name('Труба 1/2" (сталь, 2.5м)') == 'труба 1/2" (сталь, 2.5м)'
    assert normalize_name("Саморіз 3.5х25 з пресшайбою") == "саморіз 3.5х25 з пресшайбою"


# ============================================================================
# parse_quantity tests
# ============================================================================


@pytest.mark.parametrize(
    ("raw_qty", "expected"),
    [
        ("1", 1.0),
        ("42", 42.0),
        ("1,000", 1.0),
        ("1.000000", 1.0),
        ("1.000", 1.0),
        ("1 000", 1000.0),
        ("10 000", 10000.0),
        ("1 000,50", 1000.5),
        ("1 000.50", 1000.5),
        ("0,5", 0.5),
        ("0.5", 0.5),
        ("2,500", 2.5),
        ("0,0050", 0.005),
        ("1,234.56", 1234.56),
        ("1.234,56", 1234.56),
        (1, 1.0),
        (5.5, 5.5),
        (0, 0.0),
        ("0", 0.0),
        ("0,000", 0.0),
        ("0.000000", 0.0),
        (" 1,000 ", 1.0),
        ("\xa01 000\xa0", 1000.0),
        ("", 0.0),
        ("   ", 0.0),
        (None, 0.0),
        ("invalid", 0.0),
        ("N/A", 0.0),
        ("1,000 шт", 1.0),
        ("5.0 кг", 5.0),
    ],
)
def test_parse_quantity_formats(raw_qty: Any, expected: float):
    assert parse_quantity(raw_qty) == pytest.approx(expected)


# ============================================================================
# compare_items tests
# ============================================================================


def test_compare_items_exact_match():
    m11 = [
        {"name": "Гайка М8", "quantity": "10,000"},
        {"name": "Болт М10", "quantity": "5.000000"},
    ]
    vimoga = [
        {"name": "гайка м8", "quantity": 10},
        {"name": "болт м10", "quantity": 5},
    ]
    assert compare_items(m11, vimoga) == "full"


def test_compare_items_different_order():
    m11 = [
        {"name": "Шайба М12", "quantity": 20},
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
    ]
    vimoga = [
        {"name": "Болт М10", "quantity": 5},
        {"name": "Шайба М12", "quantity": 20},
        {"name": "Гайка М8", "quantity": 10},
    ]
    assert compare_items(m11, vimoga) == "full"


def test_compare_items_single_item_match():
    m11 = [{"name": "Гайка М8", "quantity": "1,000"}]
    vimoga = [{"name": "Гайка М8", "quantity": 1}]
    assert compare_items(m11, vimoga) == "full"


def test_compare_items_single_item_mismatch_name():
    m11 = [{"name": "Гайка М8", "quantity": 10}]
    vimoga = [{"name": "Болт М8", "quantity": 10}]
    assert compare_items(m11, vimoga) == "none"


def test_compare_items_single_item_mismatch_quantity():
    m11 = [{"name": "Гайка М8", "quantity": 10}]
    vimoga = [{"name": "Гайка М8", "quantity": 5}]
    assert compare_items(m11, vimoga) == "none"


def test_compare_items_partial_one_item_differs_in_name():
    m11 = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
    ]
    vimoga = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Шайба М12", "quantity": 5},
    ]
    assert compare_items(m11, vimoga) == "partial"


def test_compare_items_partial_one_item_differs_in_quantity():
    m11 = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
    ]
    vimoga = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 8},
    ]
    assert compare_items(m11, vimoga) == "partial"


def test_compare_items_partial_subset_and_superset():
    m11 = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
    ]
    vimoga_subset = [{"name": "Гайка М8", "quantity": 10}]
    assert compare_items(m11, vimoga_subset) == "partial"

    vimoga_superset = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
        {"name": "Шайба М12", "quantity": 20},
    ]
    assert compare_items(m11, vimoga_superset) == "partial"


def test_compare_items_no_match():
    m11 = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
    ]
    vimoga = [
        {"name": "Труба ДУ50", "quantity": 100},
        {"name": "Кран 1/2", "quantity": 2},
    ]
    assert compare_items(m11, vimoga) == "none"


def test_compare_items_empty_lists():
    assert compare_items([], []) == "none"
    assert compare_items([], [{"name": "Гайка М8", "quantity": 10}]) == "none"
    assert compare_items([{"name": "Гайка М8", "quantity": 10}], []) == "none"
    assert compare_items(None, None) == "none"
    assert compare_items(None, [{"name": "Гайка М8", "quantity": 10}]) == "none"
    assert compare_items([{"name": "Гайка М8", "quantity": 10}], None) == "none"


def test_compare_items_items_with_empty_or_whitespace_names():
    m11 = [{"name": "", "quantity": 10}, {"name": "   ", "quantity": 5}]
    vimoga = [{"name": "", "quantity": 10}]
    assert compare_items(m11, vimoga) == "none"


def test_compare_items_duplicates():
    # Identical duplicates in both
    m11 = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
    ]
    vimoga = [
        {"name": "Болт М10", "quantity": 5},
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Гайка М8", "quantity": 10},
    ]
    assert compare_items(m11, vimoga) == "full"

    # M-11 has duplicate, but ВИМОГА has only one
    vimoga_single = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
    ]
    assert compare_items(m11, vimoga_single) == "partial"


def test_compare_items_various_data_types():
    # Tuples / lists
    m11_tuples = [("Гайка М8", "1,000"), ("Болт М10", 5)]
    vimoga_tuples = [("болт м10", "5.0"), ("гайка  м8", 1.0)]
    assert compare_items(m11_tuples, vimoga_tuples) == "full"

    # Objects / dataclasses
    @dataclass
    class ItemObj:
        name: str
        quantity: Any

    m11_objs = [ItemObj("Гайка М8", "10,000")]
    vimoga_objs = [ItemObj("гайка м8", 10)]
    assert compare_items(m11_objs, vimoga_objs) == "full"


# ============================================================================
# find_best_match tests
# ============================================================================


def test_find_best_match_selects_full_over_partial_and_none():
    m11 = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
    ]
    candidates = [
        {
            "doc_id": 101,
            "items": [{"name": "Труба 1/2", "quantity": 1}],
        },  # none
        {
            "doc_id": 102,
            "items": [{"name": "Гайка М8", "quantity": 10}],
        },  # partial
        {
            "doc_id": 103,
            "items": [
                {"name": "Болт М10", "quantity": 5},
                {"name": "Гайка М8", "quantity": 10},
            ],
        },  # full
    ]
    doc_id, status = find_best_match(m11, candidates)
    assert doc_id == 103
    assert status == "full"


def test_find_best_match_selects_best_partial():
    m11 = [
        {"name": "Гайка М8", "quantity": 10},
        {"name": "Болт М10", "quantity": 5},
        {"name": "Шайба М12", "quantity": 20},
    ]
    candidates = [
        {
            "doc_id": 201,
            "items": [{"name": "Шайба М12", "quantity": 20}],
        },  # 1 matched item
        {
            "doc_id": 202,
            "items": [
                {"name": "Гайка М8", "quantity": 10},
                {"name": "Болт М10", "quantity": 5},
            ],
        },  # 2 matched items
        {
            "doc_id": 203,
            "items": [{"name": "Цвяхи 100", "quantity": 50}],
        },  # 0 matched items
    ]
    doc_id, status = find_best_match(m11, candidates)
    assert doc_id == 202
    assert status == "partial"


def test_find_best_match_returns_none_when_all_fail():
    m11 = [{"name": "Гайка М8", "quantity": 10}]
    candidates = [
        {"doc_id": 301, "items": [{"name": "Труба", "quantity": 1}]},
        {"doc_id": 302, "items": [{"name": "Кран", "quantity": 2}]},
    ]
    doc_id, status = find_best_match(m11, candidates)
    assert doc_id is None
    assert status == "none"


def test_find_best_match_empty_candidates_or_items():
    assert find_best_match([], [{"doc_id": 1, "items": [{"name": "A", "quantity": 1}]}]) == (
        None,
        "none",
    )
    assert find_best_match([{"name": "A", "quantity": 1}], []) == (None, "none")
    assert find_best_match(None, None) == (None, "none")


def test_find_best_match_various_candidate_structures():
    m11 = [("Гайка М8", 10)]

    # Tuple candidate (doc_id, items)
    tuple_candidates = [
        (401, [("Труба", 1)]),
        (402, [("Гайка М8", 10)]),
    ]
    assert find_best_match(m11, tuple_candidates) == (402, "full")

    # Dict with "id"
    id_candidates = [
        {"id": 501, "items": [("Гайка М8", 10)]},
    ]
    assert find_best_match(m11, id_candidates) == (501, "full")

    # Dict with "vimoga_doc_id"
    vimoga_id_candidates = [
        {"vimoga_doc_id": 601, "items": [("Гайка М8", 10)]},
    ]
    assert find_best_match(m11, vimoga_id_candidates) == (601, "full")

    # Object candidate
    @dataclass
    class CandidateObj:
        doc_id: int
        items: List[Any]

    obj_candidates = [
        CandidateObj(doc_id=701, items=[("Гайка М8", 10)]),
    ]
    assert find_best_match(m11, obj_candidates) == (701, "full")

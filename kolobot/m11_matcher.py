"""M-11 matching engine: pure logic for matching M-11 documents against classic ВИМОГА documents.

Order-independent set comparison by normalized name and parsed quantity.
No database or I/O dependencies.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable, Optional, Tuple


def normalize_name(name: Optional[str]) -> str:
    """Normalize item name: lowercase, strip, and collapse whitespace."""
    if not name:
        return ""
    return " ".join(str(name).strip().lower().split())


def parse_quantity(qty: Any) -> float:
    """Parse quantity into float.

    Handles formats like:
      - "1,000" -> 1.0 (comma decimal separator)
      - "1.000000" -> 1.0 (dot decimal separator with trailing zeros)
      - "1" -> 1.0
      - "1 000" -> 1000.0 (space thousands separator)
      - "1 000,50" -> 1000.5
      - "1 000.50" -> 1000.5
      - numeric int/float inputs directly
      - empty or unparseable inputs -> 0.0
    """
    if qty is None:
        return 0.0
    if isinstance(qty, (int, float)):
        return float(qty)

    s = str(qty).strip()
    if not s:
        return 0.0

    # Remove all whitespace (spaces, non-breaking spaces \xa0, etc.)
    s = re.sub(r"\s+", "", s)

    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        last_comma = s.rfind(",")
        last_dot = s.rfind(".")
        if last_comma > last_dot:
            # Dot is thousands separator, comma is decimal: "1.000,50" -> "1000.50"
            s = s.replace(".", "").replace(",", ".")
        else:
            # Comma is thousands separator, dot is decimal: "1,000.50" -> "1000.50"
            s = s.replace(",", "")
    elif has_comma:
        if s.count(",") > 1:
            # Multiple commas: thousands separators: "1,000,000" -> "1000000"
            s = s.replace(",", "")
        else:
            # Single comma: decimal separator: "1,000" -> "1.000"
            s = s.replace(",", ".")
    elif has_dot:
        if s.count(".") > 1:
            # Multiple dots: thousands separators: "1.000.000" -> "1000000"
            s = s.replace(".", "")

    try:
        return float(s)
    except ValueError:
        # Fallback for trailing unit text like "1,000 шт" -> "1.000"
        match = re.match(r"^[-+]?\d+(?:\.\d+)?", s)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                pass
        return 0.0


def _extract_item_pair(item: Any) -> Optional[Tuple[str, float]]:
    """Extract (normalized_name, rounded_quantity) from an item representation.

    Accepts dicts, tuples, lists, or objects with name/quantity attributes.
    Returns None if item has no name.
    """
    if item is None:
        return None

    name = ""
    qty_val: Any = 0

    if isinstance(item, dict):
        name = item.get("name") or item.get("item_name") or item.get("title") or ""
        qty_val = (
            item.get("quantity")
            if "quantity" in item
            else item.get("qty", item.get("count", item.get("amount", 0)))
        )
    elif isinstance(item, (tuple, list)):
        if len(item) > 0:
            name = item[0]
        if len(item) > 1:
            qty_val = item[1]
    else:
        name = getattr(item, "name", getattr(item, "item_name", getattr(item, "title", "")))
        qty_val = getattr(item, "quantity", getattr(item, "qty", getattr(item, "count", 0)))

    norm_name = normalize_name(name)
    if not norm_name:
        return None

    qty = round(parse_quantity(qty_val), 4)
    return (norm_name, qty)


def _match_stats(
    m11_items: Optional[Iterable[Any]],
    vimoga_items: Optional[Iterable[Any]],
) -> Tuple[str, int, int, int]:
    """Calculate match statistics between two item collections.

    Returns:
        (status, matched_count, total_m11, total_vimoga)
        status is one of: "full", "partial", "none"
    """
    if not m11_items or not vimoga_items:
        return ("none", 0, 0, 0)

    m11_pairs = [x for x in (_extract_item_pair(i) for i in m11_items) if x is not None]
    vimoga_pairs = [x for x in (_extract_item_pair(i) for i in vimoga_items) if x is not None]

    if not m11_pairs or not vimoga_pairs:
        return ("none", 0, 0, 0)

    m11_counts = Counter(m11_pairs)
    vimoga_counts = Counter(vimoga_pairs)

    common = m11_counts & vimoga_counts
    matched = sum(common.values())
    total_m11 = sum(m11_counts.values())
    total_vimoga = sum(vimoga_counts.values())

    if matched == 0:
        return ("none", 0, total_m11, total_vimoga)

    if matched == total_m11 and matched == total_vimoga:
        return ("full", matched, total_m11, total_vimoga)

    return ("partial", matched, total_m11, total_vimoga)


def compare_items(
    m11_items: Optional[Iterable[Any]],
    vimoga_items: Optional[Iterable[Any]],
) -> str:
    """Order-independent set comparison by normalized name + quantity.

    Returns:
        "full" - all items match (identical item multisets, any sequence)
        "partial" - some items match, but not all
        "none" - no items match or at least one document has no valid items
    """
    status, _, _, _ = _match_stats(m11_items, vimoga_items)
    return status


def _extract_candidate_id(candidate: Any) -> Any:
    """Extract document ID from a candidate representation."""
    if isinstance(candidate, dict):
        if "doc_id" in candidate:
            return candidate["doc_id"]
        if "vimoga_doc_id" in candidate:
            return candidate["vimoga_doc_id"]
        if "id" in candidate:
            return candidate["id"]
        return None
    if isinstance(candidate, (tuple, list)):
        return candidate[0] if len(candidate) > 0 else None
    return getattr(
        candidate,
        "doc_id",
        getattr(candidate, "vimoga_doc_id", getattr(candidate, "id", None)),
    )


def _extract_candidate_items(candidate: Any) -> Iterable[Any]:
    """Extract item collection from a candidate representation."""
    if isinstance(candidate, dict):
        return candidate.get("items") or []
    if isinstance(candidate, (tuple, list)):
        return candidate[1] if len(candidate) > 1 else []
    return getattr(candidate, "items", []) or []


def find_best_match(
    m11_items: Optional[Iterable[Any]],
    candidates: Optional[Iterable[Any]],
) -> Tuple[Optional[Any], str]:
    """Given M-11 items and a list of ВИМОГА candidates, find the best match.

    Each candidate can be a dict, tuple/list, or object containing doc_id and items.

    Returns:
        (vimoga_doc_id, match_status)
        If no candidate matches, or candidates is empty, returns (None, "none").
    """
    if not candidates or not m11_items:
        return (None, "none")

    best_doc_id: Optional[Any] = None
    best_status = "none"
    best_score: Tuple[int, float, int] = (-1, 0.0, 0)

    status_ranks = {"full": 2, "partial": 1, "none": 0}

    for candidate in candidates:
        doc_id = _extract_candidate_id(candidate)
        items = _extract_candidate_items(candidate)

        status, matched, total_m11, total_cand = _match_stats(m11_items, items)
        rank = status_ranks[status]

        # Score components:
        # 1. Rank: full (2) > partial (1) > none (0)
        # 2. Dice similarity ratio: 2 * matched / (total_m11 + total_cand)
        # 3. Absolute matched items count
        denom = total_m11 + total_cand
        ratio = (2.0 * matched / denom) if denom > 0 else 0.0
        score = (rank, ratio, matched)

        if score > best_score:
            best_score = score
            best_status = status
            best_doc_id = doc_id

    if best_status == "none":
        return (None, "none")

    return (best_doc_id, best_status)

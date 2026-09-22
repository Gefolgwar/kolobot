"""DocStructurer: parse Gemini JSON, retry, raw fallback, card view model."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ParseStatus(str, Enum):
    OK = "ok"
    NEEDS_RETRY = "needs_retry"
    RAW_FALLBACK = "raw_fallback"


_REQUESTED_BY_RE = re.compile(r"ЗАТРЕБУВАВ\b[:\s]*([^\n]*)", re.IGNORECASE)

# OCR плутає Г/Т, тому приймаємо і "ЧЕРЕЗ КОТО".
_REQUESTED_VIA_RE = re.compile(r"ЧЕРЕЗ\s+КО[ГТ]О\b[:\s]*([^\n]*)", re.IGNORECASE)

# Наступні за значенням поля бланка / підписи / заголовки таблиці — межа значення,
# коли OCR зліпив увесь бланк в один рядок.
_FIELD_STOP_RE = re.compile(
    r"\s+(?:"
    r"НОМЕНКЛАТУРНИЙ|НАЙМЕНУВАННЯ|ЗАТРЕБУВАВ|ЗАТРЕБУВАНО|ВІДПУЩЕНО|КІЛЬКІСТЬ|ЦІНА|СУМА"
    r"|ВІДПУСТИВ|ОДЕРЖАВ|ДОЗВОЛИВ|ОТРИМАВ|БУХГАЛТЕР"
    r"|ЧЕРЕЗ\s+КОГО|ЗАМОВЛЕННЯ|СТ\.\s*ВИТРАТ|ЛИСТ|ОПЕР|СКЛ|ДАТА|К\.?\s?ГР|№"
    r")\b",
    re.IGNORECASE,
)


def _clean_field_value(value: str) -> str:
    """Обрізає значення поля бланка на межі наступного поля й прибирає OCR-сміття."""
    stop = _FIELD_STOP_RE.search(value)
    if stop:
        value = value[: stop.start()]
    value = value.strip()

    # Хвіст із одиничних символів — сміття від OCR заголовка таблиці ("... (ПІБ) П Р R").
    while True:
        trimmed = re.sub(r"\s+\S$", "", value)
        if trimmed == value:
            break
        value = trimmed
    return value


def extract_requested_by(text: str) -> str:
    """Extract the requester ('ЗАТРЕБУВАВ') from raw OCR text."""
    if not text:
        return ""
    match = _REQUESTED_BY_RE.search(text)
    if not match:
        return ""
    return _clean_field_value(match.group(1))


def extract_requested_via(text: str) -> str:
    """Extract the intermediary ('ЧЕРЕЗ КОГО') from raw OCR text."""
    if not text:
        return ""
    match = _REQUESTED_VIA_RE.search(text)
    if not match:
        return ""
    return _clean_field_value(match.group(1))


def normalize_doc_type(
    doc_type: str = "",
    title: str = "",
    summary: str = "",
    raw_text: str = "",
) -> str:
    """
    Normalize document type to 'вимога', 'накладна', or original type.
    Determined strictly by the printed header/title of the document.
    """
    dt_lower = (doc_type or "").strip().lower()
    title_lower = (title or "").strip().lower()
    summary_lower = (summary or "").strip().lower()
    text_lower = (raw_text or "").strip().lower()
    header_lines = "\n".join(text_lower.splitlines()[:5])

    # Priority 1: Check header lines of raw text (top of document)
    if re.search(r"\bвимога\b", header_lines) or re.search(r"\bакт\s+списанн", header_lines):
        return "вимога"
    if (
        re.search(r"\bнакладна\b", header_lines)
        or re.search(r"\bприбутков", header_lines)
        or re.search(r"\bвидатков", header_lines)
        or re.search(r"\bтоварна\b", header_lines)
        or re.search(r"\bттн\b", header_lines)
    ):
        return "накладна"

    # Priority 2: Check explicit title
    if (
        "вимога" in title_lower
        or "списанн" in title_lower
    ):
        return "вимога"
    if (
        "накладна" in title_lower
        or "прибутков" in title_lower
        or "видатков" in title_lower
        or "товарна" in title_lower
        or "ттн" in title_lower
    ):
        return "накладна"

    # Priority 3: Check summary
    if "вимога" in summary_lower or "списанн" in summary_lower:
        return "вимога"
    if "накладна" in summary_lower or "прибутков" in summary_lower or "видатков" in summary_lower:
        return "накладна"

    # Priority 4: Explicit doc_type if no header/title/summary match
    if (
        "вимога" in dt_lower
        or "списанн" in dt_lower
    ):
        return "вимога"
    if (
        "накладна" in dt_lower
        or "прибутков" in dt_lower
        or "видатков" in dt_lower
    ):
        return "накладна"

    # Priority 5: Full raw text keyword search with boundaries
    if (
        re.search(r"\bвимога\s*№", text_lower)
        or re.search(r"\bвимога-накладна", text_lower)
        or re.search(r"\bакт\s+списанн", text_lower)
    ):
        return "вимога"
    if (
        re.search(r"\bнакладна\s*№", text_lower)
        or re.search(r"\bприбуткова\s+накладна", text_lower)
        or re.search(r"\bвидаткова\s+накладна", text_lower)
    ):
        return "накладна"

    return dt_lower or "other"


@dataclass
class Document:
    doc_type: str = "other"
    title: str = ""
    summary: str = ""
    key_value_pairs: List[Dict[str, str]] = field(default_factory=list)
    raw_text: str = ""
    language: str = ""
    doc_number: str = ""
    doc_date: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    totals: Dict[str, Any] = field(default_factory=dict)
    nomenclature_number: str = ""
    item_name: str = ""
    incoming: str = ""
    outgoing: str = ""
    balance: str = ""
    unit: str = ""
    supplier: str = ""
    notes: str = ""
    requested_by: str = ""
    requested_via: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.raw_text.strip() and not self.title.strip() and not self.summary.strip()


@dataclass
class CardViewModel:
    title: str
    doc_type: str
    summary: str
    key_value_pairs: List[Dict[str, str]]
    doc_number: str = ""
    doc_date: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    totals: Dict[str, Any] = field(default_factory=dict)
    nomenclature_number: str = ""
    item_name: str = ""
    incoming: str = ""
    outgoing: str = ""
    balance: str = ""
    unit: str = ""
    supplier: str = ""
    notes: str = ""


@dataclass
class ParseResult:
    status: ParseStatus
    doc: Optional[Document] = None


class DocStructurer:
    """Parse semi-structured JSON from Gemini, enforce schema, card view model."""

    MAX_KV = 8
    MAX_TITLE = 200
    MAX_SUMMARY = 300
    MAX_VALUE = 200

    def parse(self, model_text: str, *, is_retry: bool = False) -> ParseResult:
        data = self._try_json(model_text)
        if data is None:
            if is_retry:
                fallback_meta = self.parse_fallback_text(model_text)
                norm_dt = normalize_doc_type(
                    doc_type="other",
                    raw_text=model_text,
                )
                doc = Document(
                    doc_type=norm_dt,
                    raw_text=model_text,
                    doc_number=fallback_meta.get("doc_number", ""),
                    doc_date=fallback_meta.get("doc_date", ""),
                    items=fallback_meta.get("items", []),
                    totals=fallback_meta.get("totals", {}),
                    requested_by=extract_requested_by(model_text),
                    requested_via=extract_requested_via(model_text),
                )
                return ParseResult(status=ParseStatus.RAW_FALLBACK, doc=doc)
            return ParseResult(status=ParseStatus.NEEDS_RETRY)

        raw_doc_type = str(data.get("doc_type", "other") or "other")
        title = str(data.get("title", "") or "")
        summary = str(data.get("summary", "") or "")
        raw_text = str(data.get("raw_text", "") or "")

        norm_doc_type = normalize_doc_type(
            doc_type=raw_doc_type,
            title=title,
            summary=summary,
            raw_text=raw_text,
        )

        doc_number = str(data.get("doc_number", "") or "")
        doc_date = str(data.get("doc_date", "") or "")
        items = self._norm_items(data.get("items"))
        totals = self._norm_totals(data.get("totals"))

        # Apply fallback text extraction if fields are missing but raw_text is present
        if raw_text and (not doc_number or not doc_date or not items or not totals):
            fb = self.parse_fallback_text(raw_text)
            if not doc_number:
                doc_number = fb.get("doc_number", "")
            if not doc_date:
                doc_date = fb.get("doc_date", "")
            if not items:
                items = fb.get("items", [])
            if not totals:
                totals = fb.get("totals", {})

        doc = Document(
            doc_type=norm_doc_type,
            title=title,
            summary=summary,
            key_value_pairs=self._norm_kvs(data.get("key_value_pairs")),
            raw_text=raw_text,
            language=data.get("language", "") or "",
            doc_number=doc_number,
            doc_date=doc_date,
            items=items,
            totals=totals,
            nomenclature_number=str(data.get("nomenclature_number", "") or ""),
            item_name=str(data.get("item_name", "") or ""),
            incoming=str(data.get("incoming", "") or ""),
            outgoing=str(data.get("outgoing", "") or ""),
            balance=str(data.get("balance", "") or ""),
            unit=str(data.get("unit", "") or ""),
            supplier=str(data.get("supplier", "") or ""),
            notes=str(data.get("notes", "") or ""),
            requested_by=str(data.get("requested_by", "") or "")
            or extract_requested_by(raw_text),
            requested_via=str(data.get("requested_via", "") or "")
            or extract_requested_via(raw_text),
        )
        if not doc.title and doc.raw_text:
            doc.title = doc.raw_text[:80]

        return ParseResult(status=ParseStatus.OK, doc=doc)

    def to_card(self, doc: Document) -> CardViewModel:
        return CardViewModel(
            title=doc.title[: self.MAX_TITLE],
            doc_type=doc.doc_type,
            summary=doc.summary[: self.MAX_SUMMARY],
            key_value_pairs=[
                {"key": kv["key"], "value": kv["value"][: self.MAX_VALUE]}
                for kv in doc.key_value_pairs[: self.MAX_KV]
            ],
            doc_number=doc.doc_number,
            doc_date=doc.doc_date,
            items=doc.items,
            totals=doc.totals,
            nomenclature_number=doc.nomenclature_number,
            item_name=doc.item_name,
            incoming=doc.incoming,
            outgoing=doc.outgoing,
            balance=doc.balance,
            unit=doc.unit,
            supplier=doc.supplier,
            notes=doc.notes,
        )

    @classmethod
    def parse_fallback_text(cls, text: str) -> Dict[str, Any]:
        """Extract doc_number, doc_date, items, and totals from plain OCR text."""
        if not text:
            return {"doc_number": "", "doc_date": "", "items": [], "totals": {}}

        doc_number = ""
        doc_date = ""
        items = []
        totals = {}

        # 1. Extract Document Number
        num_match = re.search(
            r"(?:Document\s+Number|Документ\s*№|№\s*Документа|Документ|Накладна\s*№|Чек\s*№|Рахунок\s*№)\s*[:№]?\s*([A-Za-z0-9\-/]+)",
            text,
            re.IGNORECASE,
        )
        if num_match:
            doc_number = num_match.group(1).strip()

        # 2. Extract Date
        date_match = re.search(
            r"(?:Date|Дата)\s*[:№]?\s*(\d{2}[\./\.-]\d{2}[\./\.-]\d{4}|\d{4}-\d{2}-\d{2})",
            text,
            re.IGNORECASE,
        )
        if date_match:
            doc_date = date_match.group(1).strip()

        # 3. Extract Totals
        tot_no_vat = re.search(
            r"(?:Всього|Сума|Разом)\s*[:]?\s*([\d\s]+[.,]\d{2})", text, re.IGNORECASE
        )
        if tot_no_vat:
            totals["total_no_vat"] = tot_no_vat.group(1).strip()

        vat = re.search(
            r"(?:Сума\s*без\s*ПДВ|ПДВ|Враховуючи\s*ПДВ)\s*[:]?\s*([\d\s]+[.,]\d{2})",
            text,
            re.IGNORECASE,
        )
        if vat:
            totals["vat"] = vat.group(1).strip()

        tot_with_vat = re.search(
            r"(?:Всього\s*з\s*ПДВ|Разом\s*з\s*ПДВ|До\s*сплати)\s*[:]?\s*([\d\s]+[.,]\d{2})",
            text,
            re.IGNORECASE,
        )
        if tot_with_vat:
            totals["total_with_vat"] = tot_with_vat.group(1).strip()

        # 4. Extract Line Items
        # Pattern matching table rows e.g. "1 лак меблівий (0.25л) 10 банки 150,00 1500,00"
        item_pattern = re.compile(
            r"^\s*(\d+)\s+(.+?)\s+([\d\s]+[.,]?\d*)\s+([a-zA-Zа-яА-ЯіІїЇєЄ.]+)\s+([\d\s]+[.,]\d{2})\s+([\d\s]+[.,]\d{2})\s*$",
            re.MULTILINE,
        )
        for match in item_pattern.finditer(text):
            num, name, qty, unit, price, total = match.groups()
            items.append({
                "num": int(num),
                "name": name.strip(),
                "quantity": qty.strip(),
                "unit": unit.strip(),
                "price_no_vat": price.strip(),
                "total_no_vat": total.strip(),
            })

        return {
            "doc_number": doc_number,
            "doc_date": doc_date,
            "items": items,
            "totals": totals,
        }

    @staticmethod
    def _try_json(text: str) -> Optional[Dict[str, Any]]:
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:])
            if text.rstrip().endswith("```"):
                text = text.rstrip()[:-3]
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    @staticmethod
    def _norm_kvs(raw: Any) -> List[Dict[str, str]]:
        if not isinstance(raw, list):
            return []
        result = []
        for item in raw:
            if isinstance(item, dict) and "key" in item and "value" in item:
                result.append({"key": str(item["key"]), "value": str(item["value"])})
        return result

    @staticmethod
    def _norm_items(raw: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        result = []
        for item in raw:
            if isinstance(item, dict):
                result.append({
                    "num": item.get("num", len(result) + 1),
                    "nomenclature_number": str(item.get("nomenclature_number", "")),
                    "name": str(item.get("name", "")),
                    "quantity": str(item.get("quantity", "")),
                    "unit": str(item.get("unit", "")),
                    "price_no_vat": str(item.get("price_no_vat", "")),
                    "total_no_vat": str(item.get("total_no_vat", "")),
                })
        return result

    @staticmethod
    def _norm_totals(raw: Any) -> Dict[str, Any]:
        if not isinstance(raw, dict):
            return {}
        return {
            "total_no_vat": str(raw.get("total_no_vat", "")),
            "vat": str(raw.get("vat", "")),
            "total_with_vat": str(raw.get("total_with_vat", "")),
        }


"""Card rendering: the structured document as Telegram HTML, and its buttons.

Pure formatting — no bot, no storage, no side effects. ``format_card_text``
turns a ``Document`` and its ``CardViewModel`` into the text of one card;
``make_card_keyboard`` builds the save/reject buttons that pair with it.
"""

from __future__ import annotations

import html
from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from kolobot.doc_structurer import CardViewModel, Document


def h(text: Any) -> str:
    if not text:
        return ""
    return html.escape(str(text))


def format_card_text(doc: Document, card: CardViewModel) -> str:
    """Format a structured document and its card view model into HTML text for Telegram."""
    lines = [
        f"<b>{h(card.doc_type).upper()}</b>: {h(card.title)}",
    ]

    if card.doc_number or card.doc_date:
        meta_str = []
        if card.doc_number:
            meta_str.append(f"№ {h(card.doc_number)}")
        if card.doc_date:
            meta_str.append(f"від {h(card.doc_date)}")
        lines.append("<b>Документ:</b> " + " ".join(meta_str))

    if card.summary:
        lines.append(f"\n<b>Опис:</b> {h(card.summary)}")

    if card.key_value_pairs:
        lines.append("\n<b>Основні реквізити:</b>")
        for kv in card.key_value_pairs:
            lines.append(f"• <b>{h(kv['key'])}</b>: {h(kv['value'])}")

    if card.items:
        lines.append("\n<b>Повний перелік товарів / послуг:</b>")
        for it in card.items:
            num = h(it.get("num", ""))
            name = h(it.get("name", ""))
            qty = h(it.get("quantity", ""))
            unit = h(it.get("unit", ""))
            price = h(it.get("price_no_vat", ""))
            total_val = h(it.get("total_no_vat", ""))
            details = []
            if qty or unit:
                details.append(f"{qty} {unit}".strip())
            if price:
                details.append(f"ціна: {price}")
            if total_val:
                details.append(f"сума: {total_val}")
            det_str = f" ({', '.join(details)})" if details else ""
            num_str = f"{num}. " if num else "• "
            lines.append(f"  {num_str}<b>{name}</b>{det_str}")

    if card.totals:
        tot_parts = []
        if card.totals.get("total_no_vat"):
            tot_parts.append(f"Без ПДВ: {h(card.totals['total_no_vat'])}")
        if card.totals.get("vat"):
            tot_parts.append(f"ПДВ: {h(card.totals['vat'])}")
        if card.totals.get("total_with_vat"):
            tot_parts.append(f"Всього з ПДВ: {h(card.totals['total_with_vat'])}")
        if tot_parts:
            lines.append("\n<b>Підсумкові суми:</b>\n" + "\n".join(f"• {p}" for p in tot_parts))

    if getattr(doc, "raw_text", None):
        lines.append(f"\n<b>Повний розпізнаний текст:</b>\n<i>{h(doc.raw_text)}</i>")

    full_text = "\n".join(line for line in lines if line)
    if len(full_text) > 4000:
        full_text = full_text[:3950] + "\n\n<i>... [текст скорочено через ліміт Telegram (4000 символів)]</i>"

    return full_text


def make_card_keyboard(card_id: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for a specific pending card."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Зберегти", callback_data=f"confirm_save:{card_id}"),
        InlineKeyboardButton(text="Відхилити", callback_data=f"confirm_reject:{card_id}"),
    ]])

"""Warehouse items: the list, one item's history, and editing an item."""

from __future__ import annotations

import logging

from aiohttp import web

from kolobot.web.context import WebContext
from kolobot.web.router import route

logger = logging.getLogger("kolobot.web_server")


@route("GET", "/api/warehouse/items")
async def items(ctx: WebContext, request: web.Request) -> web.Response:
    return web.json_response(ctx.db.get_items_with_balance())


@route("GET", "/api/warehouse/items/{item_id}/transactions")
async def item_transactions(ctx: WebContext, request: web.Request) -> web.Response:
    item_id = int(request.match_info["item_id"])
    txs = ctx.db.get_item_transactions(item_id)
    return web.json_response(txs)


@route("POST", "/api/warehouse/items/{item_id}/edit")
@route("PATCH", "/api/warehouse/items/{item_id}")
@route("POST", "/api/warehouse/items/{item_id}")
async def edit_item(ctx: WebContext, request: web.Request) -> web.Response:
    try:
        item_id = int(request.match_info["item_id"])
    except (KeyError, ValueError):
        return web.json_response({"error": "Некоректний ID позиції"}, status=400)

    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Некоректний JSON"}, status=400)

    if not isinstance(data, dict):
        return web.json_response({"error": "Тіло запиту має бути JSON об'єктом"}, status=400)

    field = data.get("field")
    value = data.get("value")
    comment = data.get("comment", "")

    allowed_fields = {"name", "sku", "unit", "supplier", "notes", "balance", "quantity", "min_balance"}
    if not field:
        matching_fields = [k for k in data.keys() if k in allowed_fields]
        if len(matching_fields) == 1:
            field = matching_fields[0]
            value = data[field]
        else:
            return web.json_response({"error": "Не вказано поле для редагування ('field')"}, status=400)

    if field not in allowed_fields:
        return web.json_response(
            {"error": f"Непідтримуване поле: {field}. Дозволені: {sorted(allowed_fields)}"},
            status=400,
        )

    if value is None or (isinstance(value, str) and not value.strip() and field in {"balance", "quantity"}):
        return web.json_response({"error": "Значення ('value') не може бути порожнім/null"}, status=400)

    item = ctx.db.get_item(item_id)
    if not item:
        return web.json_response({"error": "Позицію не знайдено"}, status=404)

    if field == "min_balance":
        try:
            min_val = float(value) if value not in (None, "") else 0.0
            if min_val < 0:
                min_val = 0.0
        except (ValueError, TypeError):
            return web.json_response({"error": "Значення мінімального залишку має бути числом"}, status=400)

        try:
            result = ctx.db.adjust_item_field(
                item_id=item_id,
                field="min_balance",
                new_value=min_val,
                comment=str(comment or ""),
            )
        except Exception as exc:
            logger.error("Error adjusting item min_balance: %s", exc)
            return web.json_response({"error": f"Помилка оновлення: {exc}"}, status=400)

        if not result:
            return web.json_response({"error": "Позицію не знайдено"}, status=404)

        return web.json_response(result)

    if field in {"balance", "quantity"}:
        try:
            target_qty = float(value)
        except (ValueError, TypeError):
            return web.json_response({"error": "Значення кількості має бути числом"}, status=400)

        try:
            result = ctx.db.adjust_item_quantity(
                item_id=item_id,
                target_quantity=target_qty,
                comment=str(comment or ""),
            )
        except Exception as exc:
            logger.error("Error adjusting item quantity: %s", exc)
            return web.json_response({"error": f"Помилка оновлення кількості: {exc}"}, status=400)

        if not result:
            return web.json_response({"error": "Позицію не знайдено"}, status=404)

        updated_item = ctx.db.get_item(item_id)
        if updated_item:
            updated_item["balance"] = target_qty
            result["item"] = updated_item

        return web.json_response(result)

    try:
        result = ctx.db.adjust_item_field(
            item_id=item_id,
            field=field,
            new_value=str(value),
            comment=str(comment or ""),
        )
    except Exception as exc:
        logger.error("Error adjusting item field: %s", exc)
        return web.json_response({"error": f"Помилка оновлення: {exc}"}, status=400)

    if not result:
        return web.json_response({"error": "Позицію не знайдено"}, status=404)

    return web.json_response(result)

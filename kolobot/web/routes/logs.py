"""The system log: the ring buffer, its clear, and the live SSE stream."""

from __future__ import annotations

import asyncio
import json
import logging

from aiohttp import web

from kolobot.web.context import WebContext
from kolobot.web.router import route

logger = logging.getLogger("kolobot.web_server")


@route("GET", "/api/logs")
async def logs(ctx: WebContext, request: web.Request) -> web.Response:
    try:
        since_id = int(request.query.get("since_id", 0))
    except ValueError:
        since_id = 0
    try:
        limit = int(request.query.get("limit", 1000))
    except ValueError:
        limit = 1000
    level = request.query.get("level")
    query = request.query.get("q")

    entries, total, last_id = ctx.logs.get_logs(
        since_id=since_id,
        limit=limit,
        level=level,
        query=query,
    )
    return web.json_response({
        "logs": [e.to_dict() for e in entries],
        "total_count": total,
        "last_id": last_id,
    })


@route("POST", "/api/logs/clear")
@route("DELETE", "/api/logs")
async def clear_logs(ctx: WebContext, request: web.Request) -> web.Response:
    count = ctx.logs.clear()
    return web.json_response({"success": True, "cleared_count": count})


@route("GET", "/api/logs/stream")
async def stream_logs(ctx: WebContext, request: web.Request) -> web.StreamResponse:
    resp = web.StreamResponse(
        status=200,
        reason="OK",
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    await resp.prepare(request)

    queue = ctx.logs.subscribe()
    try:
        # Send initial ping comment
        await resp.write(b": ping\n\n")
        while True:
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=15.0)
                data_str = json.dumps(entry.to_dict(), ensure_ascii=False)
                payload = f"data: {data_str}\n\n"
                await resp.write(payload.encode("utf-8"))
            except asyncio.TimeoutError:
                # Heartbeat comment to prevent client timeout
                await resp.write(b": ping\n\n")
    except (asyncio.CancelledError, ConnectionResetError):
        pass
    finally:
        ctx.logs.unsubscribe(queue)

    return resp

"""The route table, its collisions, and the ctx every handler is handed.

``discover()`` is the only thing that knows routes exist, so these are the tests
that notice when one appears, disappears, or is claimed twice. They read the
table directly — no HTTP, and no fixture shaped like the page.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from kolobot.log_service import LogBuffer
from kolobot.warehouse_db import WarehouseDB
from kolobot.web.context import WebContext
from kolobot.web.frontend import Frontend
from kolobot.web.router import DuplicateRouteError, discover

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = REPO_ROOT / "kolobot" / "web"
ROUTES_PACKAGE = "kolobot.web.routes"

#: Every registration the server had before the split, as ``(method, path)``.
#: 19 distinct paths and 21 registrations — two paths answer more than one
#: method (``/api/warehouse/items/{item_id}`` on POST and PATCH, ``/api/logs``
#: on GET and DELETE). aiohttp adds a HEAD for every GET on top of that, which
#: is why ``app.router`` ends up carrying 33.
GOLDEN_ROUTES = {
    ("GET", "/"),
    ("GET", "/api/warehouse/items"),
    ("GET", "/api/warehouse/items/{item_id}/transactions"),
    ("POST", "/api/warehouse/items/{item_id}/edit"),
    ("PATCH", "/api/warehouse/items/{item_id}"),
    ("POST", "/api/warehouse/items/{item_id}"),
    ("GET", "/api/warehouse/documents"),
    ("POST", "/api/warehouse/documents/{doc_id}/edit"),
    ("POST", "/api/warehouse/documents/{doc_id}/retry"),
    ("GET", "/api/warehouse/documents/{doc_id}/impact"),
    ("GET", "/api/warehouse/documents/{doc_id}/ocr"),
    ("GET", "/api/warehouse/documents/{doc_id}/view"),
    ("GET", "/api/warehouse/documents/{doc_id}/download"),
    ("GET", "/api/warehouse/documents/{doc_id}/preview"),
    ("DELETE", "/api/warehouse/documents/{doc_id}"),
    ("POST", "/api/warehouse/import"),
    ("GET", "/api/warehouse/export"),
    ("GET", "/api/logs"),
    ("POST", "/api/logs/clear"),
    ("DELETE", "/api/logs"),
    ("GET", "/api/logs/stream"),
}

PROBE_OWNER_ID = 42


@pytest.fixture
def ctx(tmp_path):
    db = WarehouseDB(db_path=str(tmp_path / "warehouse.db"))
    db.init_db()

    files = MagicMock()
    files._base = str(tmp_path)

    try:
        yield WebContext(
            db=db,
            files=files,
            vectors=MagicMock(),
            logs=LogBuffer(),
            queue=None,
            owner_user_id=PROBE_OWNER_ID,
            frontend=Frontend(),
        )
    finally:
        db.close()


def test_route_table_is_exactly_this(ctx):
    """The golden set: a route cannot vanish or appear unnoticed."""
    app = web.Application()
    routes = discover(ROUTES_PACKAGE, ctx, app)

    assert {(r.method, r.path) for r in routes} == GOLDEN_ROUTES
    assert len(routes) == len(GOLDEN_ROUTES)
    assert len({r.path for r in routes}) == 19

    # What the application actually answers: the table above, plus the HEAD
    # aiohttp registers with every GET. A route that stopped being reachable
    # would be as much a change as one that left the table.
    head = {("HEAD", path) for method, path in GOLDEN_ROUTES if method == "GET"}
    assert {(r.method, r.resource.canonical) for r in app.router.routes()} == GOLDEN_ROUTES | head


_COLLISION = """
from aiohttp import web

from kolobot.web.router import route


@route("GET", "/claimed")
async def {name}(ctx, request):
    return web.json_response({{"by": "{name}"}})
"""

_PROBE = """
from aiohttp import web

from kolobot.web.router import route


@route("GET", "/probe")
async def probe(ctx, request):
    return web.json_response({
        "owner_user_id": ctx.owner_user_id,
        "base": ctx.files._base,
    })
"""


def _package(tmp_path: Path, monkeypatch, name: str, modules: Dict[str, str]) -> str:
    """Write a real package under ``tmp_path`` and make it importable by name."""
    root = tmp_path / name
    root.mkdir()
    (root / "__init__.py").write_text("", encoding="utf-8")
    for module, source in modules.items():
        (root / f"{module}.py").write_text(source, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    return name


def test_duplicate_route_raises(tmp_path, monkeypatch, ctx):
    """Two modules claiming one route fail at startup, before anything is wired."""
    package = _package(
        tmp_path,
        monkeypatch,
        "probe_duplicate",
        {
            "first": _COLLISION.format(name="first"),
            "second": _COLLISION.format(name="second"),
        },
    )
    app = web.Application()

    with pytest.raises(DuplicateRouteError) as raised:
        discover(package, ctx, app)

    assert "GET /claimed" in str(raised.value)
    assert "first" in str(raised.value)
    assert "second" in str(raised.value)
    # The loser does not silently win, and the application is not half-wired.
    assert list(app.router.routes()) == []


def test_log_channel_is_web_server():
    """Every module under kolobot/web/ logs to ``kolobot.web_server``, never to
    ``__name__``: the operator's log tab renders that name."""
    modules = sorted(PACKAGE_DIR.rglob("*.py"))
    assert modules, f"no modules found under {PACKAGE_DIR}"

    for path in modules:
        name = _module_name(path)
        module = importlib.import_module(name)
        assert hasattr(module, "logger"), f"{name} declares no logger"
        assert module.logger.name == "kolobot.web_server", f"{name} logs to {module.logger.name!r}"


def _module_name(path: Path) -> str:
    """``kolobot/web/routes/items.py`` -> ``kolobot.web.routes.items``."""
    parts = list(path.relative_to(REPO_ROOT).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


@pytest.mark.asyncio
async def test_handler_receives_context(tmp_path, monkeypatch, ctx):
    """``discover()`` binds the ctx into a handler that never sees ``WebServer``.

    The package is built in ``tmp_path``, so no production route is involved.
    """
    package = _package(tmp_path, monkeypatch, "probe_context", {"probe": _PROBE})
    app = web.Application()
    discover(package, ctx, app)
    assert len(list(app.router.routes())) == 2  # the probe, and its HEAD

    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        resp = await client.get("/probe")
        assert resp.status == 200
        assert await resp.json() == {
            "owner_user_id": PROBE_OWNER_ID,
            "base": str(tmp_path),
        }
    finally:
        await client.close()

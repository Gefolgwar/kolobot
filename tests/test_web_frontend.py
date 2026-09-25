"""The frontend assets in files: the page, its script block, and the JS it carries."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from kolobot import web as web_package
from kolobot.warehouse_db import WarehouseDB
from kolobot.web.assets import JS, PAGE
from kolobot.web_server import WebServer

UI_DIR = Path(web_package.__file__).resolve().parent / "ui"


@pytest.fixture
def warehouse_env(tmp_path):
    db_path = str(tmp_path / "warehouse.db")
    db = WarehouseDB(db_path=db_path)
    db.init_db()

    fs = MagicMock()
    fs._base = str(tmp_path)

    vs = MagicMock()
    vs.list_all_ids.return_value = []

    return db, fs, vs


def _script_block(page: str) -> str:
    """The page's one script block, without the newline that ends its <script> tag.

    The head's CDN tag is ``<script src=...>``, so the exact string ``<script>``
    occurs once — on the block's opening line.
    """
    return page.split("<script>\n", 1)[1].split("</script>", 1)[0]


def test_script_tag_content_equals_frontend_js():
    """The invariant every node-driven test of the page depends on."""
    assert _script_block(PAGE) == "\n".join(JS.values())


def test_every_asset_reaches_the_page():
    """Each file under ``ui/`` is served — a typo'd directory would otherwise
    ship a page with no CSS and nothing would notice."""
    files = sorted(path for path in UI_DIR.rglob("*") if path.is_file())
    assert {
        "shell.html",
        "app.css",
        "js/01-core.js",
        "js/02-items_table.js",
        "js/03-document_fields.js",
        "js/04-item_edit_modal.js",
        "js/05-item_transactions.js",
        "js/06-items_filters.js",
        "js/07-document_status.js",
        "js/08-document_sort.js",
        "js/09-document_marks.js",
        "js/10-documents_render.js",
        "js/11-document_impact.js",
        "js/12-import_export.js",
        "js/13-document_viewer.js",
        "js/14-ocr_panel.js",
        "js/15-document_delete.js",
        "js/16-logs.js",
        "js/17-boot.js",
    } <= {path.relative_to(UI_DIR).as_posix() for path in files}

    for path in files:
        source = path.read_text(encoding="utf-8")
        if path.name != "shell.html":
            assert source in PAGE, f"{path.name} never reaches the page"
            continue
        # The shell's tokens are replaced by the assets they name; its own lines survive.
        for line in source.splitlines():
            if line.strip().startswith("{{"):
                continue
            assert line in PAGE, f"shell.html: {line!r} never reaches the page"


@pytest.mark.asyncio
async def test_index_serves_the_page(warehouse_env):
    db, fs, vs = warehouse_env
    server = WebServer(warehouse_db=db, file_store=fs, vector_store=vs, owner_user_id=42)
    client = TestClient(TestServer(server.app))
    await client.start_server()

    try:
        resp = await client.get("/")
        assert resp.status == 200
        assert await resp.text() == PAGE
    finally:
        await client.close()
        db.close()

"""The frontend assets in files: the page, its script block, and the migration gate."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from aiohttp.test_utils import TestClient, TestServer

from kolobot import web as web_package
from kolobot.warehouse_db import WarehouseDB
from kolobot.web.assets import JS, PAGE
from kolobot.web_server import WebServer

REPO_ROOT = Path(__file__).resolve().parent.parent
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


def _pre_refactor_literal():
    """``HTML_PAGE`` as it stands in ``git show HEAD:kolobot/web_server.py``."""
    source = subprocess.run(
        ["git", "show", "HEAD:kolobot/web_server.py"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            getattr(target, "id", None) == "HTML_PAGE" for target in node.targets
        ):
            return node.value.value
    return None


def test_page_matches_pre_refactor_html():
    """Migration gate: the page is the literal it replaced, character for character.

    Deleted with the other ``git show HEAD:`` tests once the series lands; until
    then it is the one check that the cut was verbatim.
    """
    literal = _pre_refactor_literal()
    if literal is None:
        pytest.skip("HEAD carries no HTML_PAGE literal: the extraction has landed")
    assert PAGE == literal.replace("\r\n", "\n")


def test_script_tag_content_equals_frontend_js():
    """The invariant every node-driven test of the page depends on."""
    assert _script_block(PAGE) == "\n".join(JS.values())


def test_every_asset_reaches_the_page():
    """Each file under ``ui/`` is served — a typo'd directory would otherwise
    ship a page with no CSS and nothing would notice."""
    files = sorted(path for path in UI_DIR.rglob("*") if path.is_file())
    assert {"shell.html", "app.css", "js/page.js"} <= {
        path.relative_to(UI_DIR).as_posix() for path in files
    }

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
    client = TestClient(TestServer(server._app))
    await client.start_server()

    try:
        resp = await client.get("/")
        assert resp.status == 200
        assert await resp.text() == PAGE
    finally:
        await client.close()
        db.close()

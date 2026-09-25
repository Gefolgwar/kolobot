"""The frontend assets: everything under ``ui/``, read off disk and assembled.

The directory *is* the configuration — no list of assets exists anywhere, so
there is nothing to keep in sync:

* ``ui/shell.html`` is the document skeleton. A line holding ``{{name}}`` is a
  token; the whole line is replaced by the asset the token names.
* ``{{styles}}`` takes every ``ui/*.css``, ``{{scripts}}`` every ``ui/js/*.js``,
  in asset order — dropping a file in is all it takes to serve it.
* ``{{documents.html}}``-style tokens name one file directly, because where a
  body fragment belongs is page structure, which no filename can express.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("kolobot.web_server")

#: ``09-document_sort.js`` sorts as 9. A name without a prefix sorts first, by name.
_NN_PREFIX = re.compile(r"^(\d+)-")

#: A token owns its whole line: the line, newline included, is replaced.
_TOKEN = re.compile(r"\{\{([^{}\n]+)\}\}\n")

_STYLES = "styles"
_SCRIPTS = "scripts"


@dataclass(frozen=True)
class Asset:
    """One file under ``ui/``, as read."""

    name: str  # relative to ui/, e.g. "js/page.js"
    path: Path
    source: str


def _order(path: Path) -> Tuple[int, int, str]:
    """Sort key: the lexicographic order of the ``NN-`` filename prefixes.

    The prefix is read as a number, so ``10-`` comes after ``09-``. Files with
    no prefix sort first, by name.
    """
    prefix = _NN_PREFIX.match(path.name)
    if prefix is None:
        return 0, 0, path.name
    return 1, int(prefix.group(1)), path.name


def _stem(path: Path) -> str:
    """``ui/js/09-document_sort.js`` -> ``document_sort``."""
    return _NN_PREFIX.sub("", path.stem)


class Frontend:
    """Reads ``ui/``, assembles the page, and hands out single assets."""

    def __init__(self, root: Optional[Path] = None) -> None:
        self._root = Path(root) if root is not None else Path(__file__).resolve().parent / "ui"
        if not self._root.is_dir():
            raise FileNotFoundError(
                f"frontend assets are missing: {self._root} is not a directory. "
                "kolobot/web/ui/ ships inside the package, so a wheel built without "
                'package-data "kolobot.web" = ["ui/*.html", "ui/*.css", "ui/js/*.js"] '
                "lands here."
            )
        self.reload()

    def reload(self) -> None:
        """Re-read every asset from disk. The page is rebuilt on next access."""
        self._shell = self._read(self._root / "shell.html")
        self._styles = self._load("*.css")
        self._scripts = self._load("js/*.js")
        self._fragments: Dict[str, Asset] = {}
        for name in _TOKEN.findall(self._shell):
            if name in (_STYLES, _SCRIPTS):
                continue
            path = self._root / name
            if not path.is_file():
                raise FileNotFoundError(
                    f"{self._root / 'shell.html'} includes {name!r}, but {path} is not a file"
                )
            self._fragments[name] = Asset(name, path, self._read(path))
        self._page: Optional[str] = None

    def html(self) -> str:
        """The whole document: the shell with every token replaced."""
        if self._page is None:
            self._page = _TOKEN.sub(self._expand, self._shell)
        return self._page

    def js(self) -> Dict[str, str]:
        """Module sources by file stem, in the order they are served."""
        return dict(zip((_stem(asset.path) for asset in self._scripts), self._parts(self._scripts)))

    def asset(self, name: str) -> str:
        """One asset's source: a JS module by stem (``"page"``), else by filename."""
        for asset in (*self._styles, *self._scripts, *self._fragments.values()):
            if asset.name == name or _stem(asset.path) == name:
                return asset.source
        raise KeyError(f"no asset named {name!r} under {self._root}")

    def _expand(self, token: re.Match) -> str:
        name = token.group(1)
        if name == _STYLES:
            return self._join(self._styles)
        if name == _SCRIPTS:
            return self._join(self._scripts)
        return self._fragments[name].source

    def _load(self, pattern: str) -> List[Asset]:
        paths = sorted(self._root.glob(pattern), key=_order)
        return [Asset(path.relative_to(self._root).as_posix(), path, self._read(path)) for path in paths]

    @staticmethod
    def _read(path: Path) -> str:
        # Universal newlines: the page is the same whatever the checkout did to
        # line endings.
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()

    @staticmethod
    def _parts(assets: Sequence[Asset]) -> List[str]:
        """Sources in order. A file ends with the newline that separates it from
        the next one; the last keeps its own, which closes the block."""
        if not assets:
            return []
        return [asset.source.rstrip("\n") for asset in assets[:-1]] + [assets[-1].source]

    def _join(self, assets: Sequence[Asset]) -> str:
        return "\n".join(self._parts(assets))

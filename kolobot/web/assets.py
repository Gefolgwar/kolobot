"""``PAGE`` and ``JS``, built once when this module is first imported.

``PAGE`` is the document served at ``GET /``. ``JS`` maps a module stem to its
source, in the order the modules appear in the page, so ``"\\n".join(JS.values())``
is the content of the page's single ``<script>``.
"""

from __future__ import annotations

from typing import Dict

from kolobot.web.frontend import Frontend

_frontend = Frontend()

PAGE: str = _frontend.html()
JS: Dict[str, str] = _frontend.js()

"""Web layer: the page served at ``GET /`` and the server that serves it.

Internal package. ``kolobot.web_server`` is the only front door — it re-exports
``WebServer``, ``PAGE`` and ``JS``. Nothing is re-exported here.

Every module under this package logs to the one channel ``kolobot.web_server``,
never to ``__name__``: the log tab renders logger names to the operator, and
``README.md`` documents that string. ``tests/test_web_routes.py`` holds us to it.
"""

import logging

logger = logging.getLogger("kolobot.web_server")

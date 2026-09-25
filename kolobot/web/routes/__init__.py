"""The route modules. One module per concern, none importing another.

Each module tags its own handlers with ``@route``; ``discover()`` finds them.
"""

import logging

# The channel is part of the observable output — the operator's log tab renders
# it. Every module under kolobot/web/ declares this same name, never __name__.
logger = logging.getLogger("kolobot.web_server")

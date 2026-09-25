"""``@route`` and ``discover()`` — the only place that knows routes exist.

A handler is ``async def h(ctx, request)``. Tagging it with ``@route("GET", "/x")``
puts it on the function itself; nothing anywhere lists routes. ``discover()``
imports every module of the route package, collects the tagged functions and
registers them on the application, binding the context as it goes.

Because the table is collected rather than declared, two modules can claim the
same ``(method, path)`` and neither would notice — the second would simply win.
``DuplicateRouteError`` turns that into one loud failure at startup instead.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Tuple

from aiohttp import web

from kolobot.web.context import WebContext

logger = logging.getLogger("kolobot.web_server")

Handler = Callable[[WebContext, web.Request], Awaitable[web.StreamResponse]]


class DuplicateRouteError(RuntimeError):
    """Two handlers claimed the same ``(method, path)``."""


@dataclass(frozen=True)
class Route:
    """One registration: what to answer, and on which method and path."""

    method: str
    path: str
    handler: Handler


def route(method: str, path: str) -> Callable[[Handler], Handler]:
    """Tag a module-level coroutine as a route. Stackable, order-independent."""

    def tag(handler: Handler) -> Handler:
        declared: Tuple[Route, ...] = getattr(handler, "__routes__", ())
        handler.__routes__ = (*declared, Route(method.upper(), path, handler))
        return handler

    return tag


def discover(package: str, ctx: WebContext, app: web.Application) -> Tuple[Route, ...]:
    """Import every module of ``package``, register what it tagged, return the table.

    Raises ``DuplicateRouteError`` before registering anything, so a collision
    cannot leave the application half-wired.
    """
    routes = _collect(package)
    _reject_duplicates(routes)
    for entry in routes:
        _add(app, entry, _bind(entry.handler, ctx))
    return tuple(routes)


def _collect(package: str) -> List[Route]:
    """Every ``@route`` under ``package``, in module-name order."""
    pkg = importlib.import_module(package)
    names = sorted(info.name for info in pkgutil.iter_modules(pkg.__path__))
    found: List[Route] = []
    for name in names:
        module = importlib.import_module(f"{package}.{name}")
        for value in vars(module).values():
            found.extend(getattr(value, "__routes__", ()))
    return found


def _reject_duplicates(routes: List[Route]) -> None:
    claimed: Dict[Tuple[str, str], Handler] = {}
    for entry in routes:
        key = (entry.method, entry.path)
        if key in claimed:
            raise DuplicateRouteError(
                f"{entry.method} {entry.path} is claimed twice: "
                f"{claimed[key].__module__}.{claimed[key].__qualname__} and "
                f"{entry.handler.__module__}.{entry.handler.__qualname__}"
            )
        claimed[key] = entry.handler


def _bind(handler: Handler, ctx: WebContext) -> Callable[[web.Request], Awaitable[web.StreamResponse]]:
    """``h(ctx, request)`` as aiohttp wants it: ``h(request)``."""

    async def bound(request: web.Request) -> web.StreamResponse:
        return await handler(ctx, request)

    return bound


def _add(app: web.Application, entry: Route, handler: Callable) -> None:
    """Register one route. ``GET`` goes through ``add_get``, which registers the
    implicit ``HEAD`` alongside it — going around that would drop a method the
    server answers today."""
    if entry.method == "GET":
        app.router.add_get(entry.path, handler)
    else:
        app.router.add_route(entry.method, entry.path, handler)

"""aura/cloud/router.py — AURA Cloud Dynamic Route Registry.

The CloudRouter is a runtime-expandable route table.  Unlike a static mapping,
routes can be added, removed, or listed while AURA is running — no restart
required.  This lets virtual servers advertise new capabilities dynamically
and lets the CloudManager build a unified route graph across all servers.

Route keys follow the convention ``"METHOD /path"`` (e.g. ``"GET /ping"``)
but any string key is accepted; the router performs exact-match lookup first
then prefix-match fallback.

Usage
-----
    from aura.cloud.router import CloudRouter

    router = CloudRouter()
    router.add_route("GET /hello", lambda req: {"msg": "hello"})
    router.add_route("POST /echo", lambda req: req.get("body"))

    handler = router.match("GET /hello")
    if handler:
        print(handler({}))   # {"msg": "hello"}

    print(router.list_routes())
    router.remove_route("GET /hello")
"""

from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, List, Optional


class CloudRouter:
    """Dynamic, thread-safe HTTP route registry.

    Routes may be added and removed at runtime without restarting the server.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # route_key → (handler, metadata)
        self._routes: Dict[str, Dict[str, Any]] = {}
        self._created_at: float = time.time()
        self._total_lookups: int = 0

    # ── route management ───────────────────────────────────────────────────────

    def add_route(
        self,
        route_key: str,
        handler: Callable,
        description: str = "",
        replace: bool = True,
    ) -> bool:
        """Register *handler* under *route_key*.

        Parameters
        ----------
        route_key:
            String key, e.g. ``"GET /api/ping"``.
        handler:
            Callable that accepts a request dict and returns a response value.
        description:
            Human-readable description shown in route listings.
        replace:
            If False and *route_key* already exists, return False without
            replacing the existing handler.

        Returns
        -------
        bool
            True if the route was added/replaced, False if it existed and
            *replace* was False.
        """
        with self._lock:
            if route_key in self._routes and not replace:
                return False
            self._routes[route_key] = {
                "handler": handler,
                "description": description,
                "registered_at": time.time(),
            }
            return True

    def remove_route(self, route_key: str) -> bool:
        """Remove *route_key*.  Returns True if it existed."""
        with self._lock:
            if route_key in self._routes:
                del self._routes[route_key]
                return True
            return False

    def match(self, route_key: str) -> Optional[Callable]:
        """Return the handler for *route_key*, or None.

        Lookup order:
        1. Exact match
        2. Prefix match (longest matching prefix wins)
        """
        with self._lock:
            self._total_lookups += 1
            # Exact match
            entry = self._routes.get(route_key)
            if entry is not None:
                return entry["handler"]
            # Prefix match
            best: Optional[str] = None
            for key in self._routes:
                if route_key.startswith(key) and (best is None or len(key) > len(best)):
                    best = key
            if best is not None:
                return self._routes[best]["handler"]
            return None

    # ── introspection ──────────────────────────────────────────────────────────

    def list_routes(self) -> List[Dict[str, Any]]:
        """Return a list of all registered routes (without handler callables)."""
        with self._lock:
            return [
                {
                    "route": key,
                    "description": meta["description"],
                    "registered_at": meta["registered_at"],
                }
                for key, meta in sorted(self._routes.items())
            ]

    def route_count(self) -> int:
        """Return the number of registered routes."""
        with self._lock:
            return len(self._routes)

    def stats(self) -> Dict[str, Any]:
        """Return router statistics."""
        with self._lock:
            return {
                "route_count": len(self._routes),
                "total_lookups": self._total_lookups,
                "uptime_seconds": round(time.time() - self._created_at, 2),
                "routes": [
                    {"route": k, "description": v["description"]}
                    for k, v in sorted(self._routes.items())
                ],
            }

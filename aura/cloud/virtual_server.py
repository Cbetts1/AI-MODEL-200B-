"""aura/cloud/virtual_server.py — AURA Virtual Server.

A VirtualServer is a lightweight compute unit that:

  • Registers itself on the VirtualNetwork under a unique server_id
  • Owns its own CloudRouter (route table)
  • Runs a background thread that drains its mailbox and dispatches requests
  • Supports start / stop lifecycle
  • Can be replicated by CloudManager to scale horizontally

Virtual servers communicate exclusively through the VirtualNetwork — they
have no OS-level sockets and do not depend on the host network configuration.

Usage
-----
    from aura.cloud.virtual_network import VirtualNetwork
    from aura.cloud.virtual_server import VirtualServer

    net = VirtualNetwork()
    srv = VirtualServer("api-server", net)
    srv.register_route("GET /hello", lambda req: {"message": "Hello from vServer!"})
    srv.start()

    # send a request from another server:
    net.send("another-server", "api-server", {"method": "GET", "path": "/hello"})

    # or call directly:
    response = srv.handle({"method": "GET", "path": "/hello"})
    print(response)   # {"message": "Hello from vServer!"}

    srv.stop()
"""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from .virtual_network import VirtualNetwork
from .router import CloudRouter


class VirtualServer:
    """A self-contained virtual compute unit with its own route table.

    Parameters
    ----------
    name:
        Human-readable server name (also used as server_id in the network).
    network:
        The VirtualNetwork this server is attached to.
    auto_start:
        If True, start the mailbox-processing thread immediately.
    """

    def __init__(
        self,
        name: str,
        network: VirtualNetwork,
        auto_start: bool = False,
    ) -> None:
        self.server_id: str = name
        self.name: str = name
        self.network: VirtualNetwork = network
        self.router: CloudRouter = CloudRouter()
        self._created_at: float = time.time()
        self._requests_handled: int = 0
        self._errors: int = 0
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Register on the virtual network
        self._address: str = network.register_address(self.server_id)

        if auto_start:
            self.start()

    # ── route registration ─────────────────────────────────────────────────────

    def register_route(
        self,
        route_key: str,
        handler: Callable[[Dict[str, Any]], Any],
    ) -> None:
        """Register *handler* for *route_key* (e.g. ``"GET /ping"``).

        The handler receives a request dict and returns a response (any JSON-
        serialisable value).
        """
        self.router.add_route(route_key, handler)

    def unregister_route(self, route_key: str) -> bool:
        """Remove a route.  Returns True if it existed."""
        return self.router.remove_route(route_key)

    # ── request handling ───────────────────────────────────────────────────────

    def handle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a request dict synchronously.

        Parameters
        ----------
        request:
            Must contain ``method`` (str) and ``path`` (str).
            May also contain ``body`` (any) and ``headers`` (dict).

        Returns
        -------
        dict
            Response with ``status``, ``body``, and ``server`` keys.
        """
        method = request.get("method", "GET").upper()
        path = request.get("path", "/")
        route_key = f"{method} {path}"

        with self._lock:
            self._requests_handled += 1

        handler = self.router.match(route_key)
        if handler is None:
            # Try fallback without method prefix
            handler = self.router.match(path)

        if handler is None:
            with self._lock:
                self._errors += 1
            return {
                "status": 404,
                "body": {"error": f"No route for '{route_key}' on {self.name}"},
                "server": self.name,
            }

        try:
            result = handler(request)
            return {"status": 200, "body": result, "server": self.name}
        except Exception as exc:  # noqa: BLE001
            with self._lock:
                self._errors += 1
            return {
                "status": 500,
                "body": {"error": str(exc)},
                "server": self.name,
            }

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background mailbox-processing thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._mailbox_loop,
            name=f"vserver-{self.name}",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the mailbox-processing thread and unregister from the network."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.network.unregister_address(self.server_id)

    # ── background loop ────────────────────────────────────────────────────────

    def _mailbox_loop(self) -> None:
        """Drain the virtual-network mailbox and dispatch each request."""
        while self._running:
            packet = self.network.recv(self.server_id, timeout=0.05)
            if packet is None:
                continue
            payload = packet.get("payload", {})
            if not isinstance(payload, dict):
                continue
            response = self.handle(payload)
            # Route the response back to the sender if they're still registered
            src = packet.get("src")
            if src and src != self.server_id:
                self.network.send(self.server_id, src, response)

    # ── introspection ──────────────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Return a snapshot of this server's state."""
        with self._lock:
            return {
                "name": self.name,
                "server_id": self.server_id,
                "address": self._address,
                "running": self._running,
                "routes": self.router.list_routes(),
                "requests_handled": self._requests_handled,
                "errors": self._errors,
                "uptime_seconds": round(time.time() - self._created_at, 2),
            }

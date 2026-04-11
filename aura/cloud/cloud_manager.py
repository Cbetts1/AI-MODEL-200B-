"""aura/cloud/cloud_manager.py — AURA Cloud Manager (Orchestrator).

CloudManager is the top-level controller for AURA's virtual cloud
infrastructure.  It owns:

  • A VirtualCPU for task scheduling
  • A VirtualNetwork for internal server-to-server messaging
  • A pool of VirtualServers (dynamically spawnable/destroyable)
  • A CloudRouter for the global route registry
  • A VirtualStorage for persistent cloud-layer data

The CloudManager is integrated into AuraEngine and exposed via the
``/v1/cloud/*`` API endpoints so operators can inspect and control the
virtual infrastructure through AURA's HTTP interface.

The stack is completely self-contained — it does not require any external
services, cloud providers, or host-network configuration.

Usage
-----
    from aura.cloud.cloud_manager import CloudManager

    cloud = CloudManager()
    cloud.start()

    # Spawn a new virtual server
    server = cloud.spawn_server("analytics")
    server.register_route("GET /ping", lambda req: {"pong": True})

    # Submit an async task to the vCPU
    future = cloud.submit_task(lambda: "done")
    print(future.result())

    # Persist data
    cloud.storage.put("analytics", "last_run", {"ts": 1234567890})

    print(cloud.status())
    cloud.stop()
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import Future
from typing import Any, Callable, Dict, List, Optional

from .virtual_cpu import VirtualCPU
from .virtual_network import VirtualNetwork
from .virtual_server import VirtualServer
from .router import CloudRouter
from .virtual_storage import VirtualStorage


class CloudManager:
    """Orchestrates the full AURA virtual cloud stack.

    Parameters
    ----------
    cpu_workers:
        Initial number of vCPU worker threads.
    storage_db_path:
        Optional path for the cloud storage SQLite file.
    """

    VERSION = "0.7.0"

    def __init__(
        self,
        cpu_workers: int = 4,
        storage_db_path: Optional[Any] = None,
    ) -> None:
        self.cpu = VirtualCPU(workers=cpu_workers, name="vcpu-main")
        self.network = VirtualNetwork(name="vnet-main")
        self.router = CloudRouter()
        self.storage = VirtualStorage(db_path=storage_db_path)

        self._lock = threading.Lock()
        self._servers: Dict[str, VirtualServer] = {}
        self._started_at: Optional[float] = None
        self._running: bool = False

        # Register built-in routes on the global router
        self._register_builtin_routes()

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the virtual cloud (all subsystems)."""
        if self._running:
            return
        self._started_at = time.time()
        self._running = True
        # Spawn the default core server
        self.spawn_server("core", auto_start=True)

    def stop(self) -> None:
        """Gracefully shut down the virtual cloud."""
        self._running = False
        with self._lock:
            for srv in list(self._servers.values()):
                srv.stop()
            self._servers.clear()
        self.cpu.shutdown(wait=True)
        self.storage.close()

    # ── server management ──────────────────────────────────────────────────────

    def spawn_server(self, name: str, auto_start: bool = True) -> VirtualServer:
        """Create and register a new VirtualServer named *name*.

        If a server with that name already exists it is returned as-is.
        """
        with self._lock:
            if name in self._servers:
                return self._servers[name]
            srv = VirtualServer(name=name, network=self.network, auto_start=auto_start)
            self._servers[name] = srv
            # Register the server in cloud storage
            self.storage.put(
                "cloud:servers",
                name,
                {"name": name, "spawned_at": time.time(), "running": auto_start},
            )
            return srv

    def destroy_server(self, name: str) -> bool:
        """Stop and remove a VirtualServer.  Returns True if it existed."""
        with self._lock:
            srv = self._servers.pop(name, None)
            if srv is None:
                return False
            srv.stop()
            self.storage.delete("cloud:servers", name)
            return True

    def get_server(self, name: str) -> Optional[VirtualServer]:
        """Return the VirtualServer with *name*, or None."""
        return self._servers.get(name)

    def list_servers(self) -> List[Dict[str, Any]]:
        """Return status snapshots for all virtual servers."""
        with self._lock:
            return [srv.status() for srv in self._servers.values()]

    # ── task scheduling ────────────────────────────────────────────────────────

    def submit_task(self, fn: Callable, *args: Any, **kwargs: Any) -> Future:
        """Schedule *fn* on the vCPU.  Returns a Future."""
        return self.cpu.submit(fn, *args, **kwargs)

    # ── route management ───────────────────────────────────────────────────────

    def add_route(
        self,
        route_key: str,
        handler: Callable,
        description: str = "",
    ) -> bool:
        """Register a global cloud route.  Returns True if added."""
        added = self.router.add_route(route_key, handler, description=description)
        if added:
            self.storage.put(
                "cloud:routes",
                route_key,
                {"route": route_key, "description": description, "added_at": time.time()},
            )
        return added

    def remove_route(self, route_key: str) -> bool:
        """Remove a global cloud route.  Returns True if it existed."""
        removed = self.router.remove_route(route_key)
        if removed:
            self.storage.delete("cloud:routes", route_key)
        return removed

    # ── infrastructure scaling ─────────────────────────────────────────────────

    def build(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        """Expand or modify the virtual infrastructure at runtime.

        Actions
        -------
        ``expand_cpu``  — add worker threads (``n`` kwarg, default 1)
        ``shrink_cpu``  — remove worker threads (``n`` kwarg, default 1)
        ``add_storage_namespace``  — create a storage namespace (``name`` kwarg)
        ``add_server``  — spawn a new virtual server (``name`` kwarg)
        ``remove_server`` — destroy a virtual server (``name`` kwarg)

        Returns a dict with the result of the action.
        """
        if action == "expand_cpu":
            n = int(kwargs.get("n", 1))
            new_count = self.cpu.expand(n)
            return {"action": action, "new_worker_count": new_count}

        if action == "shrink_cpu":
            n = int(kwargs.get("n", 1))
            new_count = self.cpu.shrink(n)
            return {"action": action, "new_worker_count": new_count}

        if action == "add_storage_namespace":
            name = kwargs.get("name", "")
            if not name:
                return {"action": action, "error": "name is required"}
            # Writing a sentinel key creates the namespace
            self.storage.put(name, "__meta__", {"created_at": time.time()})
            return {"action": action, "namespace": name, "created": True}

        if action == "add_server":
            name = kwargs.get("name", "")
            if not name:
                return {"action": action, "error": "name is required"}
            srv = self.spawn_server(name, auto_start=True)
            return {"action": action, "server": srv.status()}

        if action == "remove_server":
            name = kwargs.get("name", "")
            removed = self.destroy_server(name)
            return {"action": action, "server": name, "removed": removed}

        return {"action": action, "error": f"Unknown build action: '{action}'"}

    # ── status / introspection ─────────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        """Return a comprehensive snapshot of the virtual cloud state."""
        return {
            "version": self.VERSION,
            "running": self._running,
            "uptime_seconds": round(time.time() - self._started_at, 2)
            if self._started_at
            else 0,
            "cpu": self.cpu.stats(),
            "network": self.network.status(),
            "router": self.router.stats(),
            "storage": self.storage.stats(),
            "servers": self.list_servers(),
        }

    # ── private helpers ────────────────────────────────────────────────────────

    def _register_builtin_routes(self) -> None:
        """Register the built-in global cloud routes."""
        self.router.add_route(
            "GET /cloud/ping",
            lambda req: {"pong": True, "ts": time.time()},
            description="Virtual cloud health check",
        )
        self.router.add_route(
            "GET /cloud/status",
            lambda req: self.status(),
            description="Full virtual cloud status",
        )

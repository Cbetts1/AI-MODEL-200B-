"""aura/cloud/virtual_network.py — AURA Virtual Network Layer.

The VirtualNetwork is a 100 % in-process message bus that lets virtual
servers communicate without touching the host OS network stack.  It provides:

  • register_address(server_id)   — allocate a virtual address for a server
  • unregister_address(server_id) — release the address
  • send(src, dst, message)       — route a message between virtual servers
  • recv(server_id, timeout)      — receive the next message for a server
  • broadcast(src, message)       — deliver to all registered servers
  • allocate_port()               — reserve a logical port number
  • release_port(port)            — free a reserved port
  • status()                      — snapshot of the virtual network state

All "packets" are Python dicts.  No OS sockets are created; traffic stays
entirely inside the running Python process.

Usage
-----
    from aura.cloud.virtual_network import VirtualNetwork
    net = VirtualNetwork()
    net.register_address("server-a")
    net.register_address("server-b")
    net.send("server-a", "server-b", {"type": "ping"})
    msg = net.recv("server-b", timeout=1.0)
    print(msg)   # {'src': 'server-a', 'dst': 'server-b', 'payload': {'type': 'ping'}, ...}
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Dict, List, Optional


# Loopback prefix used for virtual addresses (human-readable, not a real IP)
_VNET_PREFIX = "vnet://"

# Port range reserved for the virtual network
_PORT_MIN = 40000
_PORT_MAX = 49999


class VirtualNetwork:
    """In-process virtual network — zero host-OS socket usage for internal routing.

    Parameters
    ----------
    name:
        Human-readable identifier for this network segment.
    max_queue_depth:
        Maximum number of unread messages per server mailbox.
    """

    def __init__(self, name: str = "vnet-0", max_queue_depth: int = 256) -> None:
        self.name = name
        self._max_depth = max_queue_depth
        self._lock = threading.Lock()
        # server_id → queue.Queue (mailbox)
        self._mailboxes: Dict[str, queue.Queue] = {}
        # server_id → virtual address string
        self._addresses: Dict[str, str] = {}
        # set of allocated logical port numbers
        self._ports: set = set()
        self._next_port: int = _PORT_MIN
        self._created_at: float = time.time()
        self._total_messages: int = 0

    # ── address management ─────────────────────────────────────────────────────

    def register_address(self, server_id: str) -> str:
        """Allocate a virtual address for *server_id*.  Returns the address."""
        with self._lock:
            if server_id in self._addresses:
                return self._addresses[server_id]
            addr = f"{_VNET_PREFIX}{self.name}/{server_id}"
            self._addresses[server_id] = addr
            self._mailboxes[server_id] = queue.Queue(maxsize=self._max_depth)
            return addr

    def unregister_address(self, server_id: str) -> bool:
        """Release the virtual address for *server_id*.  Returns True if existed."""
        with self._lock:
            if server_id not in self._addresses:
                return False
            del self._addresses[server_id]
            del self._mailboxes[server_id]
            return True

    def get_address(self, server_id: str) -> Optional[str]:
        """Return the virtual address for *server_id*, or None."""
        return self._addresses.get(server_id)

    # ── messaging ──────────────────────────────────────────────────────────────

    def send(self, src: str, dst: str, payload: Any) -> bool:
        """Route *payload* from *src* to *dst*.

        Returns True on success, False if *dst* is not registered or mailbox full.
        """
        with self._lock:
            mailbox = self._mailboxes.get(dst)
            if mailbox is None:
                return False
            packet = {
                "src": src,
                "dst": dst,
                "payload": payload,
                "timestamp": time.time(),
            }
            try:
                mailbox.put_nowait(packet)
                self._total_messages += 1
                return True
            except queue.Full:
                return False

    def recv(self, server_id: str, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """Receive the next message for *server_id*.

        Returns None if no message arrives within *timeout* seconds.
        """
        mailbox = self._mailboxes.get(server_id)
        if mailbox is None:
            return None
        try:
            return mailbox.get(timeout=timeout)
        except queue.Empty:
            return None

    def broadcast(self, src: str, payload: Any) -> int:
        """Deliver *payload* to all registered servers except *src*.

        Returns the number of servers successfully reached.
        """
        delivered = 0
        with self._lock:
            targets = [sid for sid in self._addresses if sid != src]
        for dst in targets:
            if self.send(src, dst, payload):
                delivered += 1
        return delivered

    # ── port registry ──────────────────────────────────────────────────────────

    def allocate_port(self) -> int:
        """Reserve and return a logical port number from the virtual range."""
        with self._lock:
            for _ in range(_PORT_MAX - _PORT_MIN + 1):
                port = self._next_port
                self._next_port = _PORT_MIN if self._next_port >= _PORT_MAX else self._next_port + 1
                if port not in self._ports:
                    self._ports.add(port)
                    return port
        raise RuntimeError("VirtualNetwork: all logical ports exhausted")

    def release_port(self, port: int) -> bool:
        """Free a previously allocated logical port.  Returns True if it existed."""
        with self._lock:
            if port in self._ports:
                self._ports.discard(port)
                return True
            return False

    # ── introspection ──────────────────────────────────────────────────────────

    def list_servers(self) -> List[str]:
        """Return list of registered server IDs."""
        return list(self._addresses.keys())

    def status(self) -> Dict[str, Any]:
        """Return a snapshot of virtual network state."""
        with self._lock:
            return {
                "name": self.name,
                "servers": list(self._addresses.keys()),
                "addresses": dict(self._addresses),
                "allocated_ports": sorted(self._ports),
                "total_messages_routed": self._total_messages,
                "uptime_seconds": round(time.time() - self._created_at, 2),
            }

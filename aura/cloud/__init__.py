"""aura/cloud — AURA Virtual Cloud Infrastructure.

AURA v0.7.0 ships with a fully self-contained virtual cloud layer that gives
every AURA deployment its own:

  VirtualCPU       — thread-pool task scheduler; can expand/shrink worker count
  VirtualNetwork   — in-process message bus (no host-OS sockets for internal
                     routing); manages virtual addresses and port registry
  VirtualServer    — spawnable compute units with their own route tables
  CloudRouter      — dynamic HTTP-route registry; routes build/expand at runtime
  VirtualStorage   — namespaced persistent storage with auto-expand capability
  CloudManager     — single orchestrator wiring all the above together

The entire stack operates independently of the host network.  Internal traffic
between virtual servers never leaves the Python process — it flows through
in-memory queues and shared dictionaries.  Only the external-facing HTTP
listener (``aura serve``) uses an OS socket.

Quick start
-----------
    from aura.cloud import CloudManager
    cloud = CloudManager()
    cloud.start()
    print(cloud.status())
    cloud.stop()
"""

from .cloud_manager import CloudManager
from .virtual_cpu import VirtualCPU
from .virtual_network import VirtualNetwork
from .virtual_server import VirtualServer
from .router import CloudRouter
from .virtual_storage import VirtualStorage

__all__ = [
    "CloudManager",
    "VirtualCPU",
    "VirtualNetwork",
    "VirtualServer",
    "CloudRouter",
    "VirtualStorage",
]
